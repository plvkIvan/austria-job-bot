from __future__ import annotations

import argparse
import hashlib
import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, unquote

from app.db.models import Job, SessionLocal, init_db

# Domains must match exactly, or as a subdomain. Never execute or follow links.
SOURCE_DOMAINS = {
    "karriere": ("karriere.at",),
    "ams": ("ams.at",),
    "stepstone": ("stepstone.at",),
    "hokify": ("hokify.at",),
    "willhaben": ("willhaben.at",),
}

# Only links that *look* like job listings; search pages are not job announcements.
PATH_HINTS = {
    "karriere": ("/jobs/", "/job/"),
    "ams": ("/job", "/stellenangebot", "/jobs/"),
    "stepstone": ("/stellenangebote--", "/stellenangebote/", "/job/"),
    "hokify": ("/job/", "/jobs/"),
    "willhaben": ("/iad/jobs/", "/jobs/"),
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append(
                (self._href, " ".join(" ".join(self._text).split()))
            )
            self._href = None
            self._text = []


def valid_source_url(url: str):
    try:
        parts = urlsplit(url.strip())

        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            return None

        host = parts.hostname.lower().rstrip(".")
        path = unquote(parts.path).lower()

        for source, domains in SOURCE_DOMAINS.items():
            if any(
                host == domain or host.endswith("." + domain)
                for domain in domains
            ):
                if any(hint in path for hint in PATH_HINTS[source]):
                    cleaned = urlunsplit(
                        ("https", parts.netloc.lower(), parts.path, "", "")
                    )
                    return source, cleaned

        return None

    except ValueError:
        return None


def parse_alert(data: bytes) -> list[dict[str, str]]:
    message = BytesParser(policy=policy.default).parsebytes(data)
    candidates: list[tuple[str, str]] = []

    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue

        if part.get_content_type() == "text/html":
            parser = Links()
            parser.feed(part.get_content())
            candidates += parser.links

        elif part.get_content_type() == "text/plain":
            plain = part.get_content()
            candidates += [
                (url.rstrip(".,);>"), "")
                for url in re.findall(
                    r"https://[^\s<>\"']+", plain
                )
            ]

    results = {}
    subject = str(message.get("subject", "Job alert"))[:250]

    for url, text in candidates:
        match = valid_source_url(url)

        if not match:
            continue

        source, clean_url = match
        stable_id = hashlib.sha256(
            clean_url.encode()
        ).hexdigest()

        results[(source, stable_id)] = {
            "source": source,
            "external_id": stable_id,
            "title": (
                text if len(text) >= 8 else subject
            )[:250],
            "company": "",
            "city": "",
            "url": clean_url,
            "description": "",
            "employment": "",
            "german_level": "",
            "salary_eur": None,
        }

    return list(results.values())


def import_eml(path: Path) -> tuple[int, int]:
    records = parse_alert(path.read_bytes())

    init_db()
    added = 0

    with SessionLocal() as db:
        for record in records:
            existing = (
                db.query(Job.id)
                .filter_by(
                    source=record["source"],
                    external_id=record["external_id"]
                )
                .first()
            )

            if existing:
                continue

            db.add(Job(**record))
            added += 1

        db.commit()

    return added, len(records)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Import links from personally received "
            "job-alert emails (.eml)"
        )
    )

    parser.add_argument(
        "files",
        nargs="+",
        type=Path
    )

    args = parser.parse_args()

    for path in args.files:
        added, found = import_eml(path)

        print(
            f"{path.name}: detected={found}, new={added}"
        )


if __name__ == "__main__":
    main()
