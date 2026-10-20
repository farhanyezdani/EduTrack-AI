import csv
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app import cache
from app.database import get_db
from app.models import Assessment, Intervention, Student, User
from app.schemas import (AssessmentIn, AssessmentOut, InterventionIn, InterventionOut, PlanOut,
                         ProfileIn, StudentCreate, StudentDetail, StudentListItem, StudentPage)
from app.security import get_current_user, require_admin
from app.services.advisor import generate_plan
from app.services.predictor import get_predictor

router = APIRouter(prefix="/api/students", tags=["students"])


# ---------- helpers ----------
def model_row(profile: Student | ProfileIn, a: AssessmentIn) -> dict:
    return {
        **a.model_dump(exclude={"term"}),
        "distance_km": profile.distance_km,
        "family_income": profile.family_income,
        "parent_education": profile.parent_education,
    }


def make_assessment(student_id: int, a: AssessmentIn, pred: dict) -> Assessment:
    return Assessment(
        student_id=student_id, **a.model_dump(),
        risk_probability=pred["risk_probability"], risk_level=pred["risk_level"],
        top_factors=json.dumps(pred["factors"][:6]), model_version=pred["model_version"],
    )


def assessment_out(a: Assessment) -> AssessmentOut:
    out = AssessmentOut.model_validate(a)
    out.factors = json.loads(a.top_factors)
    return out


def get_student_or_404(db: Session, student_id: int) -> Student:
    student = db.scalar(
        select(Student).where(Student.id == student_id)
        .options(selectinload(Student.assessments), selectinload(Student.interventions)))
    if not student:
        raise HTTPException(404, "Student not found")
    return student


def detail(student: Student) -> StudentDetail:
    return StudentDetail(
        **ProfileIn.model_validate(student, from_attributes=True).model_dump(),
        id=student.id, created_at=student.created_at,
        assessments=[assessment_out(a) for a in student.assessments],
        interventions=[InterventionOut.model_validate(i) for i in student.interventions],
    )


# ---------- routes ----------
@router.get("", response_model=StudentPage)
def list_students(
    search: str | None = None,
    risk_level: str | None = Query(None, pattern="^(Low|Medium|High)$"),
    class_name: str | None = None,
    sort: str = Query("risk", pattern="^(risk|recent|name)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # latest assessment per student
    latest = (select(Assessment.student_id, func.max(Assessment.id).label("aid"))
              .group_by(Assessment.student_id).subquery())
    q = (select(Student, Assessment)
         .outerjoin(latest, latest.c.student_id == Student.id)
         .outerjoin(Assessment, Assessment.id == latest.c.aid))
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(Student.name.ilike(like), Student.roll_number.ilike(like)))
    if risk_level:
        q = q.where(Assessment.risk_level == risk_level)
    if class_name:
        q = q.where(Student.class_name == class_name)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    order = {
        "risk": (Assessment.risk_probability.desc().nulls_last(), Student.id),
        "recent": (Student.id.desc(),),
        "name": (Student.name, Student.id),
    }[sort]
    rows = db.execute(q.order_by(*order).offset((page - 1) * size).limit(size)).all()

    items = []
    for s, a in rows:
        factors = json.loads(a.top_factors) if a else []
        top = next((f["label"] for f in factors if f["impact"] > 0), None)
        items.append(StudentListItem(
            id=s.id, name=s.name, roll_number=s.roll_number, class_name=s.class_name,
            attendance_pct=a.attendance_pct if a else None, avg_marks=a.avg_marks if a else None,
            risk_probability=a.risk_probability if a else None, risk_level=a.risk_level if a else None,
            top_reason=top))
    return StudentPage(items=items, total=total, page=page, size=size)


@router.post("", response_model=StudentDetail, status_code=201)
def create_student(body: StudentCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if db.scalar(select(Student).where(Student.roll_number == body.roll_number)):
        raise HTTPException(409, "Roll number already exists")
    student = Student(**body.model_dump(exclude={"assessment"}), created_by=user.id)
    db.add(student)
    db.flush()
    pred = get_predictor().predict_one(model_row(body, body.assessment))
    db.add(make_assessment(student.id, body.assessment, pred))
    db.commit()
    cache.invalidate()
    return detail(get_student_or_404(db, student.id))


@router.post("/upload", summary="Bulk import students from CSV")
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """CSV columns: name, roll_number, class_name, parent_contact, distance_km, family_income,
    parent_education, term, attendance_pct, avg_marks, prev_marks, assignment_completion,
    behavior_score, failed_subjects, fee_pending, extracurricular, teacher_feedback"""
    text = file.file.read().decode("utf-8-sig")
    valid, errors = [], []
    existing = set(db.scalars(select(Student.roll_number)))
    for line_no, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        row = {k.strip(): (v.strip() if v else None) for k, v in row.items() if k}
        for flag in ("fee_pending", "extracurricular"):
            row[flag] = str(row.get(flag) or "").lower() in ("1", "true", "yes", "y")
        try:
            profile = ProfileIn.model_validate(row)
            assessment = AssessmentIn.model_validate({**row, "term": row.get("term") or "Term 1"})
        except ValidationError as e:
            errors.append({"line": line_no, "error": e.errors()[0]["msg"] + f" ({e.errors()[0]['loc'][0]})"})
            continue
        if profile.roll_number in existing:
            errors.append({"line": line_no, "error": f"Roll number {profile.roll_number} already exists"})
            continue
        existing.add(profile.roll_number)
        valid.append((profile, assessment))

    if valid:
        preds = get_predictor().predict([model_row(p, a) for p, a in valid])
        for (profile, assessment), pred in zip(valid, preds):
            student = Student(**profile.model_dump(), created_by=user.id)
            db.add(student)
            db.flush()
            db.add(make_assessment(student.id, assessment, pred))
        db.commit()
        cache.invalidate()
    return {"imported": len(valid), "failed": len(errors), "errors": errors[:50]}


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return detail(get_student_or_404(db, student_id))


@router.put("/{student_id}", response_model=StudentDetail)
def update_profile(student_id: int, body: ProfileIn, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    student = get_student_or_404(db, student_id)
    clash = db.scalar(select(Student).where(Student.roll_number == body.roll_number, Student.id != student_id))
    if clash:
        raise HTTPException(409, "Roll number already exists")
    for k, v in body.model_dump().items():
        setattr(student, k, v)
    db.commit()
    return detail(get_student_or_404(db, student_id))


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    db.delete(get_student_or_404(db, student_id))
    db.commit()
    cache.invalidate()


@router.post("/{student_id}/assessments", response_model=StudentDetail, status_code=201)
def add_assessment(student_id: int, body: AssessmentIn, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    student = get_student_or_404(db, student_id)
    pred = get_predictor().predict_one(model_row(student, body))
    db.add(make_assessment(student.id, body, pred))
    db.commit()
    cache.invalidate()
    db.expire(student)
    return detail(get_student_or_404(db, student_id))


@router.get("/{student_id}/plan", response_model=PlanOut)
def intervention_plan(student_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    student = get_student_or_404(db, student_id)
    a = student.latest
    if not a:
        raise HTTPException(400, "Student has no assessment yet")
    key = f"plan:{a.id}"
    if cached := cache.get_json(key):
        return cached
    plan = generate_plan(a.risk_level, a.risk_probability, json.loads(a.top_factors))
    cache.set_json(key, plan, ttl=3600)
    return plan


@router.post("/{student_id}/interventions", response_model=InterventionOut, status_code=201)
def add_intervention(student_id: int, body: InterventionIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    get_student_or_404(db, student_id)
    item = Intervention(student_id=student_id, created_by=user.id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    cache.invalidate()
    return item


@router.patch("/{student_id}/interventions/{intervention_id}", response_model=InterventionOut)
def update_intervention(student_id: int, intervention_id: int, body: InterventionIn,
                        db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(Intervention, intervention_id)
    if not item or item.student_id != student_id:
        raise HTTPException(404, "Intervention not found")
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    cache.invalidate()
    return item
