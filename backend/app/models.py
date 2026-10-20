"""
users -< students -< assessments   (one row per term, with the prediction)
                   -< interventions
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="teacher")  # "admin" | "teacher"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    roll_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    class_name: Mapped[str] = mapped_column(String(20), index=True)
    parent_contact: Mapped[str | None] = mapped_column(String(20))
    distance_km: Mapped[float] = mapped_column(Float)
    family_income: Mapped[str] = mapped_column(String(10))
    parent_education: Mapped[str] = mapped_column(String(10))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", order_by="Assessment.created_at")
    interventions: Mapped[list["Intervention"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", order_by="Intervention.created_at.desc()")

    @property
    def latest(self) -> "Assessment | None":
        return self.assessments[-1] if self.assessments else None


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String(30))

    attendance_pct: Mapped[float] = mapped_column(Float)
    avg_marks: Mapped[float] = mapped_column(Float)
    prev_marks: Mapped[float] = mapped_column(Float)
    assignment_completion: Mapped[float] = mapped_column(Float)
    behavior_score: Mapped[float] = mapped_column(Float)
    failed_subjects: Mapped[int] = mapped_column(Integer)
    fee_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    extracurricular: Mapped[bool] = mapped_column(Boolean, default=False)
    teacher_feedback: Mapped[str | None] = mapped_column(Text)

    # prediction at the time of entry
    risk_probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(10), index=True)
    top_factors: Mapped[str] = mapped_column(Text)  # JSON
    model_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    student: Mapped[Student] = relationship(back_populates="assessments")


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Planned")  # Planned | Done
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    student: Mapped[Student] = relationship(back_populates="interventions")
