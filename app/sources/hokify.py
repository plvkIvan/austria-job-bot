from app.sources.base import JobSource, JobListing

class HokifySource(JobSource):
    async def fetch(self) -> list[JobListing]:
        # No scraping or undocumented API access. Await authorized integration.
        return []
