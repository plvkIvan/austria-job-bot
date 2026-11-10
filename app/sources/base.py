from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class JobListing:
    source: str
    external_id: str
    title: str
    company: str
    city: str
    url: str
    description: str = ""
    employment: str = ""
    german_level: str = ""
    salary_eur: float | None = None

class JobSource(ABC):
    @abstractmethod
    async def fetch(self) -> list[JobListing]:
        """Only implement with an authorized source/API."""
