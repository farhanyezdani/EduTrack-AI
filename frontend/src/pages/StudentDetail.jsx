import { useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AssessmentFields from "../components/AssessmentFields";
import { ErrorMsg, FactorChart, pct, RiskBadge } from "../components/ui";
import {
  useAddAssessmentMutation, useAddInterventionMutation, useDeleteStudentMutation,
  useGetPlanQuery, useGetStudentQuery, useUpdateInterventionMutation,
} from "../store/api";

export default function StudentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const role = useSelector((s) => s.auth.user?.role);
  const { data: s, error, isLoading } = useGetStudentQuery(id);
  const [del] = useDeleteStudentMutation();
  const [showTerm, setShowTerm] = useState(false);

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <ErrorMsg error={error} />;

  const latest = s.assessments[s.assessments.length - 1];
  const history = s.assessments.map((a) => ({ term: a.term, risk: Math.round(a.risk_probability * 100) }));

  const remove = async () => {
    if (!confirm(`Delete ${s.name}? This removes all their records.`)) return;
    const res = await del(s.id);
    if (!res.error) navigate("/students");
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{s.name}</h1>
          <p className="muted">
            Roll {s.roll_number} · Class {s.class_name} · {s.distance_km} km away · Income {s.family_income} · Parent edu {s.parent_education}
          </p>
        </div>
        <div className="row">
          <button className="btn ghost" onClick={() => setShowTerm((v) => !v)}>+ New term data</button>
          {role === "admin" && <button className="btn danger" onClick={remove}>Delete</button>}
        </div>
      </header>

      {showTerm && <NewTerm student={s} latest={latest} onDone={() => setShowTerm(false)} />}

      <section className="grid-2">
        <div className="card">
          <div className="row-between">
            <h2>Dropout risk — {latest.term}</h2>
            <RiskBadge level={latest.risk_level} />
          </div>
          <div className={`gauge ${latest.risk_level.toLowerCase()}`}>
            <div className="gauge-fill" style={{ width: pct(latest.risk_probability) }} />
          </div>
          <p className="big-num">{pct(latest.risk_probability)}</p>
          <h3>Why? (SHAP explanation)</h3>
          <FactorChart factors={latest.factors} />
          <p className="muted small">Model {latest.model_version}</p>
        </div>

        <div className="stack">
          <Plan id={s.id} assessmentId={latest.id} />
          <div className="card">
            <h2>Risk over time</h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="term" />
                <YAxis domain={[0, 100]} unit="%" />
                <Tooltip />
                <ReferenceLine y={60} stroke="#dc2626" strokeDasharray="4 4" label={{ value: "High", fontSize: 11, fill: "#dc2626" }} />
                <Line dataKey="risk" name="Risk %" stroke="#4f46e5" strokeWidth={3} dot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid-2">
        <Interventions student={s} />
        <div className="card">
          <h2>Term history</h2>
          <table>
            <thead><tr><th>Term</th><th>Attendance</th><th>Marks</th><th>Failed</th><th>Feedback</th><th>Risk</th></tr></thead>
            <tbody>
              {[...s.assessments].reverse().map((a) => (
                <tr key={a.id}>
                  <td>{a.term}</td>
                  <td>{a.attendance_pct}%</td>
                  <td>{a.avg_marks}</td>
                  <td>{a.failed_subjects}</td>
                  <td className="muted small">{a.teacher_feedback || "—"}</td>
                  <td><RiskBadge level={a.risk_level} probability={a.risk_probability} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function Plan({ id, assessmentId }) {
  const { data, isFetching, error } = useGetPlanQuery({ id, assessmentId });
  return (
    <div className="card plan">
      <div className="row-between">
        <h2>Suggested action plan</h2>
        {data && <span className="tag">{data.source === "llm" ? "Llama 3" : "Rule-based"}</span>}
      </div>
      {isFetching && <p className="muted">Generating…</p>}
      <ErrorMsg error={error} />
      {data && !isFetching && (
        <>
          <p>{data.summary}</p>
          <ol>{data.actions.map((a, i) => <li key={i}>{a}</li>)}</ol>
        </>
      )}
    </div>
  );
}

function NewTerm({ student, latest, onDone }) {
  const [value, setValue] = useState({
    ...Object.fromEntries(Object.keys(latest).filter((k) => !["id", "risk_probability", "risk_level", "factors", "model_version", "created_at"].includes(k)).map((k) => [k, latest[k]])),
    term: `Term ${student.assessments.length + 1}`,
    prev_marks: latest.avg_marks,
  });
  const [add, { isLoading, error }] = useAddAssessmentMutation();
  const submit = async (e) => {
    e.preventDefault();
    const res = await add({ id: student.id, ...value });
    if (res.data) onDone();
  };
  return (
    <form className="card" onSubmit={submit}>
      <h2>Record new term</h2>
      <p className="muted small">Pre-filled from last term — change what's different. Previous marks = last term's marks.</p>
      <AssessmentFields value={value} onChange={setValue} />
      <ErrorMsg error={error} />
      <div className="row">
        <button className="btn primary" disabled={isLoading}>{isLoading ? "Predicting…" : "Save & re-predict"}</button>
        <button type="button" className="btn ghost" onClick={onDone}>Cancel</button>
      </div>
    </form>
  );
}

const ACTIONS = ["Parent meeting", "Counselling session", "Remedial classes", "Fee / scholarship help", "Mentor assigned", "Home visit"];

function Interventions({ student }) {
  const [form, setForm] = useState({ action: ACTIONS[0], notes: "" });
  const [add, { isLoading, error }] = useAddInterventionMutation();
  const [update] = useUpdateInterventionMutation();

  const submit = async (e) => {
    e.preventDefault();
    const res = await add({ id: student.id, ...form, notes: form.notes || null });
    if (res.data) setForm({ action: ACTIONS[0], notes: "" });
  };

  return (
    <div className="card">
      <h2>Interventions</h2>
      <form className="row inline-form" onSubmit={submit}>
        <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })}>
          {ACTIONS.map((a) => <option key={a}>{a}</option>)}
        </select>
        <input placeholder="Notes (optional)" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        <button className="btn primary sm" disabled={isLoading}>Add</button>
      </form>
      <ErrorMsg error={error} />
      <ul className="timeline">
        {student.interventions.map((i) => (
          <li key={i.id} className={i.status === "Done" ? "done" : ""}>
            <div>
              <b>{i.action}</b> <small className="muted">{new Date(i.created_at).toLocaleDateString()}</small>
              {i.notes && <div className="small">{i.notes}</div>}
            </div>
            <button className="btn ghost sm"
              onClick={() => update({ id: student.id, iid: i.id, action: i.action, notes: i.notes, status: i.status === "Done" ? "Planned" : "Done" })}>
              {i.status === "Done" ? "✓ Done" : "Mark done"}
            </button>
          </li>
        ))}
        {student.interventions.length === 0 && <li className="muted">No interventions yet.</li>}
      </ul>
    </div>
  );
}
