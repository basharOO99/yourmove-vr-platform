"""
Database Models for YourMove VR Therapy System
SQLAlchemy 2.0 fully typed models — production safe
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime
import os

from sqlalchemy import String, Integer, Text, DateTime, Float, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

# ──────────────────────────────────────────────────────────────────────────────
# Base (SQLAlchemy 2.0 style)
# ──────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Database Engine
# ──────────────────────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./yourmove.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────

class Doctor(Base):
    """Therapist / doctor account"""
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Doctor username={self.username!r}>"


class Patient(Base):
    """Patient receiving VR therapy"""
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(20))
    diagnosis_level: Mapped[str] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name={self.name!r}>"


class SessionDataLog(Base):
    """Persistent time-series log"""
    __tablename__ = "session_data_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    patient_id: Mapped[str] = mapped_column(String(100), index=True)
    focus_level: Mapped[int] = mapped_column(Integer)
    stress_level: Mapped[int] = mapped_column(Integer)
    max_tremor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_stress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_command: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ai_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SessionDataLog session={self.session_id!r} "
            f"focus={self.focus_level} stress={self.stress_level}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────

def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    db = SessionLocal()
    try:
        if not db.query(Doctor).filter(Doctor.username == "admin").first():
            db.add(Doctor(
                username="admin",
                hashed_password=pwd_context.hash("admin123"),
                full_name="Dr. Admin",
                email="admin@yourmove.com",
            ))
            db.commit()
            print("✓ Default doctor created  username=admin  password=admin123")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
