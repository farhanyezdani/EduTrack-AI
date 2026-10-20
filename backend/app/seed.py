"""
Demo data: two users and 120 students with two terms each.

    python -m app.seed

Logins: admin@edutrack.dev / admin123, teacher@edutrack.dev / teacher123
"""
import random

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.ml.generate_data import generate
from app.models import Assessment, Student, User
from app.routers.students import make_assessment
from app.schemas import AssessmentIn
from app.security import hash_password
from app.services.predictor import get_predictor

DEMO_USERS = [
    ("Admin", "admin@edutrack.dev", "admin123", "admin"),
    ("Priya Verma", "teacher@edutrack.dev", "teacher123", "teacher"),
]
FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Rohan",
         "Ananya", "Diya", "Aadhya", "Saanvi", "Pari", "Myra", "Sara", "Ira", "Kavya", "Zoya",
         "Rahul", "Neha", "Imran", "Fatima", "Harpreet", "Simran", "Karan", "Pooja", "Aman", "Riya"]
LAST = ["Sharma", "Verma", "Khan", "Singh", "Gupta", "Yadav", "Ansari", "Kumar", "Mishra", "Jain",
        "Chauhan", "Ali", "Kaur", "Reddy", "Das"]
CLASSES = ["9A", "9B", "10A", "10B", "11A", "12A"]


def ensure_users(db):
    for name, email, pw, role in DEMO_USERS:
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(name=name, email=email, password_hash=hash_password(pw), role=role))
    db.commit()


def seed(n_students: int = 120):
    Base.metadata.create_all(engine)
    rng = random.Random(7)
    db = SessionLocal()
    try:
        ensure_users(db)
        if db.scalar(select(Student).limit(1)):
            print("Students already exist - skipping student seed")
            return
        term1 = generate(n_students, seed=99).drop(columns="dropout").to_dict("records")
        predictor = get_predictor()
        for i, r in enumerate(term1):
            student = Student(
                name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", roll_number=f"2026{i + 1:03d}",
                class_name=rng.choice(CLASSES), parent_contact=f"9{rng.randint(100000000, 999999999)}",
                distance_km=r["distance_km"], family_income=r["family_income"],
                parent_education=r["parent_education"],
            )
            db.add(student)
            db.flush()

            a1 = AssessmentIn(term="Term 1", **{k: r[k] for k in AssessmentIn.model_fields if k in r})
            drift = rng.uniform(-12, 8)
            a2 = a1.model_copy(update={
                "term": "Term 2",
                "prev_marks": a1.avg_marks,
                "avg_marks": round(min(100, max(5, a1.avg_marks + drift)), 1),
                "attendance_pct": round(min(100, max(20, a1.attendance_pct + drift * 0.8)), 1),
                "assignment_completion": round(min(100, max(0, a1.assignment_completion + drift)), 1),
            })
            rows = [{**a.model_dump(exclude={"term"}), "distance_km": student.distance_km,
                     "family_income": student.family_income, "parent_education": student.parent_education}
                    for a in (a1, a2)]
            for a, pred in zip((a1, a2), predictor.predict(rows)):
                db.add(make_assessment(student.id, a, pred))
        db.commit()
        print(f"Seeded {n_students} students, {db.query(Assessment).count()} assessments")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
