"""
Database Models for YourMove VR Therapy System
SQLAlchemy models for doctors and patients
(Updated for SQLAlchemy 2.0 + Pylance type checking)
"""

from sqlalchemy import String, Integer, Text, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime
from typing import Optional
import os


# ---------- Base ----------

class Base(DeclarativeBase):
    pass


# ---------- Doctor Model ----------

class Doctor(Base):
    """Doctor/Therapist account model"""
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Doctor(username='{self.username}', name='{self.full_name}')>"


# ---------- Patient Model ----------

class Patient(Base):
    """Patient model for children undergoing VR therapy"""
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(20))
    diagnosis_level: Mapped[str] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name='{self.name}', age={self.age})>"


# ---------- Database Setup ----------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./yourmove.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------- Initialize Database ----------

def init_database() -> None:
    """Initialize database and create default doctor account"""
    Base.metadata.create_all(bind=engine)

    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    db = SessionLocal()
    try:
        existing_doctor = db.query(Doctor).filter(Doctor.username == "admin").first()
        if not existing_doctor:
            default_doctor = Doctor(
                username="admin",
                hashed_password=pwd_context.hash("admin123"),
                full_name="Dr. Admin",
                email="admin@yourmove.com"
            )
            db.add(default_doctor)
            db.commit()
            print("✓ Default doctor account created: admin / admin123")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
