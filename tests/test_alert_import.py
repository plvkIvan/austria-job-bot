
from app.services.alert_import import (
    parse_alert,
    valid_source_url,
)


def test_matching_domains():
    assert (
        valid_source_url(
            "https://www.karriere.at/jobs/1234"
        )[0]
        == "karriere"
    )

    assert (
        valid_source_url(
            "https://www.willhaben.at/iad/jobs/jobangebot-123"
        )[0]
        == "willhaben"
    )

    assert valid_source_url(
        "https://evil.example/redirect?"
        "next=https://karriere.at/jobs/1234"
    ) is None

    assert valid_source_url(
        "http://www.karriere.at/jobs/1234"
    ) is None

    assert valid_source_url(
        "https://www.karriere.at/jobs"
    ) is None


def test_parse_and_dedupe():
    raw = (
        b"From: alerts@example.org\n"
        b"Subject: New job\n"
        b"MIME-Version: 1.0\n"
        b"Content-Type: text/html; charset=utf-8\n\n"
        b'<a href="https://www.karriere.at/jobs/1234'
        b'?utm_source=mail">'
        b"Java Backend Developer</a>"
        b'<a href="https://www.karriere.at/jobs/1234">'
        b"Java Backend Developer</a>"
    )

    jobs = parse_alert(raw)

    assert len(jobs) == 1

    assert (
        jobs[0]["title"]
        == "Java Backend Developer"
    )

    assert (
        jobs[0]["url"]
        == "https://www.karriere.at/jobs/1234"
    )
