from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from app.core.config import settings

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(2), default="uk")
    city: Mapped[str] = mapped_column(String(120), default="")
    query: Mapped[str] = mapped_column(String(240), default="")
    german_level: Mapped[str] = mapped_column(String(3), default="")
    employment: Mapped[str] = mapped_column(String(30), default="")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default="language")

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(240))
    title: Mapped[str] = mapped_column(String(250))
    company: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    employment: Mapped[str] = mapped_column(String(30), default="")
    german_level: Mapped[str] = mapped_column(String(3), default="")
    salary_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(engine)
