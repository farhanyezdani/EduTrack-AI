import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ.pop("REDIS_URL", None)
os.environ.pop("LLM_BASE_URL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

STUDENT = {
    "name": "Test Student", "roll_number": "T001", "class_name": "10A", "parent_contact": "9000000000",
    "distance_km": 18, "family_income": "Low", "parent_education": "None",
    "assessment": {
        "term": "Term 1", "attendance_pct": 48, "avg_marks": 32, "prev_marks": 45,
        "assignment_completion": 30, "behavior_score": 45, "failed_subjects": 3,
        "fee_pending": True, "extracurricular": False,
        "teacher_feedback": "Irregular and often absent, struggling with subjects",
    },
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    return login(client, "admin@edutrack.dev", "admin123")


@pytest.fixture(scope="module")
def teacher(client):
    return login(client, "teacher@edutrack.dev", "teacher123")


def test_requires_auth(client):
    assert client.get("/api/students").status_code == 401


def test_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "admin@edutrack.dev", "password": "nope"})
    assert r.status_code == 401


def test_register_logs_in_as_teacher(client):
    body = {"name": "New Teacher", "email": "New.Teacher@School.com", "password": "secret1"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "teacher"
    token = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=token).json()["email"] == "new.teacher@school.com"
    assert client.post("/api/auth/register", json={**body, "email": "new.teacher@school.com"}).status_code == 409
    r = client.post("/api/auth/register", json={**body, "email": "x@school.com", "role": "admin"})
    assert r.json()["user"]["role"] == "teacher"


def test_register_short_password(client):
    r = client.post("/api/auth/register", json={"name": "Ab", "email": "a@b.com", "password": "123"})
    assert r.status_code == 422


def test_create_high_risk_student(client, teacher):
    r = client.post("/api/students", json=STUDENT, headers=teacher)
    assert r.status_code == 201, r.text
    a = r.json()["assessments"][0]
    assert a["risk_level"] == "High"
    assert a["factors"][0]["impact"] != 0
    assert any(f["feature"] == "attendance_pct" for f in a["factors"])


def test_duplicate_roll_number(client, teacher):
    assert client.post("/api/students", json=STUDENT, headers=teacher).status_code == 409


def test_validation(client, teacher):
    bad = {**STUDENT, "roll_number": "T002", "assessment": {**STUDENT["assessment"], "attendance_pct": 150}}
    assert client.post("/api/students", json=bad, headers=teacher).status_code == 422


def test_new_assessment_lowers_risk(client, teacher):
    sid = client.get("/api/students", headers=teacher).json()["items"][0]["id"]
    better = {**STUDENT["assessment"], "term": "Term 2", "attendance_pct": 95, "avg_marks": 85,
              "prev_marks": 32, "assignment_completion": 95, "behavior_score": 90, "failed_subjects": 0,
              "fee_pending": False, "extracurricular": True, "teacher_feedback": "Excellent, regular and attentive"}
    r = client.post(f"/api/students/{sid}/assessments", json=better, headers=teacher)
    history = r.json()["assessments"]
    assert len(history) == 2
    assert history[1]["risk_probability"] < history[0]["risk_probability"]


def test_list_filter_and_search(client, teacher):
    r = client.get("/api/students", params={"search": "T001"}, headers=teacher).json()
    assert r["total"] == 1
    r = client.get("/api/students", params={"risk_level": "High"}, headers=teacher).json()
    assert all(i["risk_level"] == "High" for i in r["items"])


def test_sort_recent_shows_newest_first(client, teacher):
    newest = client.get("/api/students", params={"sort": "recent", "size": 1}, headers=teacher).json()["items"][0]
    assert newest["roll_number"] == "T001"
    assert client.get("/api/students", params={"sort": "bad"}, headers=teacher).status_code == 422


def test_plan_fallback(client, teacher):
    sid = client.get("/api/students", headers=teacher).json()["items"][0]["id"]
    plan = client.get(f"/api/students/{sid}/plan", headers=teacher).json()
    assert plan["source"] == "rules" and plan["actions"]


def test_csv_upload(client, teacher):
    csv = ("name,roll_number,class_name,distance_km,family_income,parent_education,attendance_pct,"
           "avg_marks,prev_marks,assignment_completion,behavior_score,failed_subjects,fee_pending\n"
           "A One,C1,9A,3,High,Graduate,95,88,85,90,92,0,no\n"
           "B Two,C2,9A,5,Medium,School,150,60,60,60,60,0,no\n")
    r = client.post("/api/students/upload", files={"file": ("s.csv", csv, "text/csv")}, headers=teacher).json()
    assert r["imported"] == 1 and r["failed"] == 1


def test_dashboard(client, teacher):
    d = client.get("/api/dashboard/summary", headers=teacher).json()
    assert d["total_students"] == d["high_risk"] + d["medium_risk"] + d["low_risk"]


def test_what_if(client, teacher):
    body = {**STUDENT["assessment"], "distance_km": 2, "family_income": "High", "parent_education": "Graduate"}
    r = client.post("/api/model/predict", json=body, headers=teacher)
    assert 0 <= r.json()["risk_probability"] <= 1


def test_only_admin_can_delete(client, teacher, admin):
    sid = client.get("/api/students", headers=teacher).json()["items"][0]["id"]
    assert client.delete(f"/api/students/{sid}", headers=teacher).status_code == 403
    assert client.delete(f"/api/students/{sid}", headers=admin).status_code == 204
