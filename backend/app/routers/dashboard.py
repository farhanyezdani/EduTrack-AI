import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import cache
from app.database import get_db
from app.models import Assessment, Intervention, Student, User
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def compute_summary(db: Session) -> dict:
    latest_ids = select(func.max(Assessment.id)).group_by(Assessment.student_id)
    latest = db.scalars(select(Assessment).where(Assessment.id.in_(latest_ids))).all()
    students = {s.id: s for s in db.scalars(select(Student))}
    total = len(latest)

    levels = Counter(a.risk_level for a in latest)

    by_class: dict[str, dict] = {}
    for a in latest:
        cls = students[a.student_id].class_name
        row = by_class.setdefault(cls, {"class_name": cls, "total": 0, "high": 0, "medium": 0, "risk_sum": 0.0})
        row["total"] += 1
        row["risk_sum"] += a.risk_probability
        if a.risk_level == "High":
            row["high"] += 1
        elif a.risk_level == "Medium":
            row["medium"] += 1
    classes = [{**r, "avg_risk": round(r.pop("risk_sum") / r["total"], 3)}
               for r in sorted(by_class.values(), key=lambda r: (len(r["class_name"]), r["class_name"]))]

    # top positive factor for each medium/high student
    drivers = Counter()
    for a in latest:
        if a.risk_level != "Low":
            for f in json.loads(a.top_factors):
                if f["impact"] > 0:
                    drivers[f["label"]] += 1
                    break

    buckets = [0] * 10
    for a in latest:
        buckets[min(int(a.risk_probability * 10), 9)] += 1

    open_interventions = db.scalar(select(func.count()).where(Intervention.status == "Planned"))

    def avg(attr):
        return round(sum(getattr(a, attr) for a in latest) / total, 1) if total else 0

    return {
        "total_students": total,
        "high_risk": levels.get("High", 0),
        "medium_risk": levels.get("Medium", 0),
        "low_risk": levels.get("Low", 0),
        "avg_attendance": avg("attendance_pct"),
        "avg_marks": avg("avg_marks"),
        "open_interventions": open_interventions,
        "by_class": classes,
        "top_drivers": [{"label": k, "count": v} for k, v in drivers.most_common(6)],
        "risk_histogram": [{"range": f"{i * 10}-{i * 10 + 10}%", "count": c} for i, c in enumerate(buckets)],
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if cached := cache.get_json("summary"):
        return {**cached, "cached": True}
    data = compute_summary(db)
    cache.set_json("summary", data, ttl=300)
    return {**data, "cached": False}
