from app.sources.base import JobSource, JobListing

class DemoSource(JobSource):
    async def fetch(self) -> list[JobListing]:
        return [JobListing(source="demo", external_id="demo-1", title="Lagermitarbeiter", company="Example GmbH", city="Wien", url="https://example.com/job/demo-1", employment="vollzeit", german_level="B1")]
