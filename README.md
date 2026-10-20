# EduTrack AI: Student Dropout Early-Warning System

A full-stack AI/ML application that predicts which students are at risk of dropping out, explains **why** for each student, and helps teachers plan and track interventions.

**Stack:** React 18 · Redux Toolkit (RTK Query) · React Router · Recharts · FastAPI · SQLAlchemy 2 · PostgreSQL / SQLite · Redis · XGBoost · scikit-learn · imbalanced-learn (SMOTE) · Llama 3 (optional) · Docker Compose · pytest · GitHub Actions

## Results (held-out test set, 1,000 students)

| Metric | Value |
|---|---|
| ROC-AUC | **0.859** |
| Recall (at-risk students caught) | **86%** |
| Precision | 40% |
| F2 score | 0.701 |
| Decision threshold | 0.36 (tuned for F2) |

Model comparison (5-fold CV ROC-AUC): Logistic Regression 0.866 · Random Forest 0.868 · XGBoost default 0.846 · **XGBoost tuned 0.871**

> **Note on data:** real student records aren't publicly available, so the model is trained on a synthetic dataset of 5,000 students (`backend/app/ml/generate_data.py`) that simulates risk factors reported in dropout research. The pipeline retrains on real data with the same columns.

## Features

- **Risk prediction:** XGBoost model with SMOTE, hyper-parameter tuning, and an F2-tuned threshold
- **Explainability:** SHAP values for every prediction ("attendance raised risk by X, extracurriculars lowered it by Y")
- **AI action plan:** Llama 3 turns the top SHAP factors into a short plan for the teacher (rule-based fallback if no LLM is configured)
- **Progress tracking:** each term is stored as a new assessment, so the app shows how risk changes over time
- **Interventions:** log parent meetings and counselling sessions, then mark them done
- **What-If simulator:** move sliders and the prediction updates live
- **Model Insights page:** model comparison, confusion matrix, ROC curve, feature importance
- **Dashboard:** risk distribution, risk by class, most common risk drivers (cached in Redis)
- **CSV bulk import** with per-row validation errors
- **Sign up / login with JWT** and roles: anyone can sign up as a teacher; admins can also delete students and create other admins
- Search, filters, and pagination, with filters kept in the URL

## Architecture

```
React + Redux Toolkit  ──/api──►  FastAPI  ──►  PostgreSQL (users, students, assessments, interventions)
   (Vite / nginx)                   │  ├──►  Redis (dashboard + plan cache)
                                    │  ├──►  XGBoost model (loaded once at startup) + SHAP
                                    │  └──►  Llama 3 via Groq / Ollama (optional)
```

```
backend/
  app/
    main.py            FastAPI app, startup, logging middleware
    config.py          settings from env vars
    database.py        SQLAlchemy engine/session
    models.py          tables: User, Student, Assessment, Intervention
    schemas.py         Pydantic request/response validation
    security.py        PBKDF2 password hashing, JWT, role checks
    cache.py           Redis cache-aside helpers
    seed.py            demo users + 120 demo students
    routers/           auth, students, dashboard, model
    services/
      predictor.py     loads model, predicts, computes SHAP
      advisor.py       Llama 3 action plan + rule-based fallback
    ml/
      features.py      feature engineering shared by training and API
      generate_data.py synthetic dataset
      train.py         training pipeline
  artifacts/           model.joblib, metrics.json
  tests/               pytest (API + ML)
frontend/src/
  store/               Redux store, auth slice, RTK Query API
  pages/               Dashboard, Students, StudentDetail, AddStudent, WhatIf, ModelInsights, Login
  components/          Layout, AssessmentFields, ui (badges, SHAP chart)
```

## Run locally (no Docker)

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.ml.train          # generates data + trains the model (~30 s)
python -m app.seed              # demo users + 120 students
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

**Frontend** (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

**Logging in:** click **Create an account** on the login page to sign up (you become a teacher), or use a demo login.

**Demo logins** (local development only)

| Role | Email | Password |
|---|---|---|
| Admin | admin@edutrack.dev | admin123 |
| Teacher | teacher@edutrack.dev | teacher123 |

## Run with Docker (PostgreSQL + Redis)

```bash
docker compose up --build
```

App: http://localhost:3000 · API: http://localhost:8000/docs

## Turn on Llama 3 (optional)

1. Get a free API key from https://console.groq.com.
2. Copy `backend/.env.example` to `backend/.env`.
3. Set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.

To run without an API key, use Ollama instead: `ollama pull llama3`. The action-plan card then shows **Llama 3** instead of **Rule-based**.

## Tests

```bash
cd backend
pytest -q
```

17 tests cover sign-up, auth, role checks, validation, prediction, history, CSV import, the dashboard, and model sanity checks.

## API overview

| Method | Path | What it does |
|---|---|---|
| POST | /api/auth/register | Sign up as a teacher (returns a JWT) |
| POST | /api/auth/login | Log in and get a JWT |
| GET | /api/auth/me | Current user |
| POST / GET | /api/auth/users | Create or list users (admin) |
| GET | /api/students | List students (search, risk/class filters, pagination) |
| POST | /api/students | Create a student, predict risk |
| POST | /api/students/upload | Bulk CSV import |
| GET / PUT / DELETE | /api/students/{id} | Get, update, or delete a student (delete is admin-only) |
| POST | /api/students/{id}/assessments | Add new term data and re-predict |
| GET | /api/students/{id}/plan | AI action plan |
| POST / PATCH | /api/students/{id}/interventions | Log or update interventions |
| GET | /api/dashboard/summary | Dashboard numbers (cached) |
| GET | /api/model/metrics | Training metrics |
| POST | /api/model/predict | What-If prediction (nothing is saved) |
