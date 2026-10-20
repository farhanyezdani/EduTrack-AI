"""
Turns the top SHAP factors into an action plan for the teacher.
Uses Llama 3 through any OpenAI-compatible API if configured, otherwise fixed rules.
Only feature values are sent to the LLM, never names or contact details.
"""
import json
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)

RULES = {
    "attendance_pct": "Call parents about attendance and set a weekly attendance target.",
    "failed_subjects": "Arrange remedial classes for the failed subjects.",
    "avg_marks": "Assign a subject mentor and track marks in the next unit test.",
    "prev_marks": "Review what changed since last term with the student.",
    "marks_trend": "Marks are falling - schedule a one-to-one academic review.",
    "assignment_completion": "Give a simple assignment tracker and check it every Friday.",
    "behavior_score": "Refer to the school counsellor for a behaviour check-in.",
    "fee_pending": "Inform the office about scholarship / fee waiver options.",
    "family_income": "Check eligibility for government scholarships and free books.",
    "parent_education": "Hold a parent meeting to explain the student's progress simply.",
    "distance_km": "Check if school transport or a bicycle scheme is available.",
    "extracurricular": "Encourage joining a club or sport to improve engagement.",
    "feedback_sentiment": "Teacher remarks are negative - have a friendly talk to find the cause.",
}


def rule_based_plan(level: str, probability: float, factors: list[dict]) -> dict:
    risky = [f for f in factors if f["impact"] > 0][:3]
    actions = [RULES[f["feature"]] for f in risky] or ["Keep monitoring; no urgent action needed."]
    reasons = ", ".join(f["label"].lower() for f in risky) or "no major risk factor"
    return {
        "summary": f"{level} risk ({probability:.0%}). Main drivers: {reasons}.",
        "actions": actions,
        "source": "rules",
    }


def build_prompt(level: str, probability: float, factors: list[dict]) -> str:
    lines = "\n".join(
        f"- {f['label']}: value={f['value']}, effect={'increases' if f['impact'] > 0 else 'reduces'} risk"
        for f in factors[:5]
    )
    return (
        f"A school dropout model rates a student as {level} risk ({probability:.0%}).\n"
        f"Top factors from the model (SHAP):\n{lines}\n\n"
        "Write a plan for the class teacher. Reply ONLY with JSON: "
        '{"summary": "<one sentence>", "actions": ["<action 1>", "<action 2>", "<action 3>"]}. '
        "Actions must be practical for an Indian school and refer to the factors above."
    )


def generate_plan(level: str, probability: float, factors: list[dict]) -> dict:
    if not (settings.llm_base_url and settings.llm_api_key):
        return rule_based_plan(level, probability, factors)
    try:
        resp = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": "You are an experienced school counsellor."},
                    {"role": "user", "content": build_prompt(level, probability, factors)},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        return {"summary": str(data["summary"]), "actions": [str(a) for a in data["actions"]][:5], "source": "llm"}
    except Exception as e:  # network error, bad JSON, missing keys...
        log.warning("LLM call failed, using rule-based plan: %s", e)
        return rule_based_plan(level, probability, factors)
