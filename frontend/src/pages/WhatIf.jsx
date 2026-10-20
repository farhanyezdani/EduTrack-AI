import { useEffect, useState } from "react";
import { ErrorMsg, FactorChart, pct, RiskBadge } from "../components/ui";
import { usePredictMutation } from "../store/api";

const SLIDERS = [
  ["attendance_pct", "Attendance %", 0, 100],
  ["avg_marks", "Average marks", 0, 100],
  ["prev_marks", "Previous term marks", 0, 100],
  ["assignment_completion", "Assignment completion %", 0, 100],
  ["behavior_score", "Behaviour score", 0, 100],
  ["failed_subjects", "Failed subjects", 0, 6],
  ["distance_km", "Distance (km)", 0, 30],
];

const START = {
  attendance_pct: 58, avg_marks: 42, prev_marks: 50, assignment_completion: 45, behavior_score: 55,
  failed_subjects: 2, distance_km: 12, fee_pending: true, extracurricular: false,
  family_income: "Low", parent_education: "School", teacher_feedback: "Often absent and distracted",
};

export default function WhatIf() {
  const [x, setX] = useState(START);
  const [predict, { data, error }] = usePredictMutation();

  useEffect(() => {
    const t = setTimeout(() => predict(x), 200);
    return () => clearTimeout(t);
  }, [x, predict]);

  const set = (k, v) => setX({ ...x, [k]: v });

  return (
    <>
      <header className="page-head">
        <div>
          <h1>What-If simulator</h1>
          <p className="muted">Change a student's numbers and watch the model's risk prediction update live.</p>
        </div>
        <button className="btn ghost" onClick={() => setX(START)}>Reset</button>
      </header>
      <section className="grid-2">
        <div className="card">
          {SLIDERS.map(([k, label, min, max]) => (
            <label key={k} className="slider">
              <span>{label} <b>{x[k]}</b></span>
              <input type="range" min={min} max={max} step={1} value={x[k]} onChange={(e) => set(k, Number(e.target.value))} />
            </label>
          ))}
          <div className="grid-form">
            <label>Family income
              <select value={x.family_income} onChange={(e) => set("family_income", e.target.value)}>
                <option>Low</option><option>Medium</option><option>High</option>
              </select>
            </label>
            <label>Parent education
              <select value={x.parent_education} onChange={(e) => set("parent_education", e.target.value)}>
                <option>None</option><option>School</option><option>Graduate</option>
              </select>
            </label>
            <label className="check"><input type="checkbox" checked={x.fee_pending} onChange={(e) => set("fee_pending", e.target.checked)} /> Fee pending</label>
            <label className="check"><input type="checkbox" checked={x.extracurricular} onChange={(e) => set("extracurricular", e.target.checked)} /> Extracurriculars</label>
            <label className="wide">Teacher feedback
              <input value={x.teacher_feedback} onChange={(e) => set("teacher_feedback", e.target.value)} />
            </label>
          </div>
        </div>
        <div className="card sticky">
          <ErrorMsg error={error} />
          {data && (
            <>
              <div className="row-between">
                <h2>Predicted risk</h2>
                <RiskBadge level={data.risk_level} />
              </div>
              <div className={`gauge ${data.risk_level.toLowerCase()}`}>
                <div className="gauge-fill" style={{ width: pct(data.risk_probability) }} />
              </div>
              <p className="big-num">{pct(data.risk_probability)}</p>
              <h3>What's driving it</h3>
              <FactorChart factors={data.factors} limit={8} />
            </>
          )}
        </div>
      </section>
    </>
  );
}
