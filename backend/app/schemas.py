from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Income = Literal["Low", "Medium", "High"]
ParentEdu = Literal["None", "School", "Graduate"]
RiskLevel = Literal["Low", "Medium", "High"]


# ---------- Auth ----------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["admin", "teacher"] = "teacher"


class RegisterIn(BaseModel):
    # no role field: self sign-up is always a teacher
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Prediction ----------
class AssessmentIn(BaseModel):
    term: str = Field(default="Term 1", max_length=30)
    attendance_pct: float = Field(ge=0, le=100)
    avg_marks: float = Field(ge=0, le=100)
    prev_marks: float = Field(ge=0, le=100)
    assignment_completion: float = Field(ge=0, le=100)
    behavior_score: float = Field(ge=0, le=100)
    failed_subjects: int = Field(ge=0, le=10)
    fee_pending: bool = False
    extracurricular: bool = False
    teacher_feedback: str | None = Field(default=None, max_length=1000)


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    class_name: str = Field(min_length=1, max_length=20)
    parent_contact: str | None = Field(default=None, max_length=20)
    distance_km: float = Field(ge=0, le=100)
    family_income: Income
    parent_education: ParentEdu


class StudentCreate(ProfileIn):
    assessment: AssessmentIn


class PredictIn(AssessmentIn):
    distance_km: float = Field(ge=0, le=100)
    family_income: Income
    parent_education: ParentEdu


class Factor(BaseModel):
    feature: str
    label: str
    value: float | str
    impact: float  # SHAP value, positive = raises risk


class PredictionOut(BaseModel):
    risk_probability: float
    risk_level: RiskLevel
    factors: list[Factor]
    model_version: str


# ---------- Students ----------
class AssessmentOut(AssessmentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    risk_probability: float
    risk_level: RiskLevel
    factors: list[Factor] = []
    model_version: str
    created_at: datetime


class InterventionIn(BaseModel):
    action: str = Field(min_length=2, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
    status: Literal["Planned", "Done"] = "Planned"


class InterventionOut(InterventionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class StudentListItem(BaseModel):
    id: int
    name: str
    roll_number: str
    class_name: str
    attendance_pct: float | None
    avg_marks: float | None
    risk_probability: float | None
    risk_level: RiskLevel | None
    top_reason: str | None


class StudentPage(BaseModel):
    items: list[StudentListItem]
    total: int
    page: int
    size: int


class StudentDetail(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    assessments: list[AssessmentOut]
    interventions: list[InterventionOut]


class PlanOut(BaseModel):
    summary: str
    actions: list[str]
    source: Literal["llm", "rules"]
