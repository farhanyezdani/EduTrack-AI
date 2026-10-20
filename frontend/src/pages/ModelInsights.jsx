import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorMsg, Stat } from "../components/ui";
import { useGetMetricsQuery } from "../store/api";

const LABELS = {
  attendance_pct: "Attendance", avg_marks: "Avg marks", prev_marks: "Prev marks",
  assignment_completion: "Assignments", behavior_score: "Behaviour", failed_subjects: "Failed subjects",
  distance_km: "Distance", fee_pending: "Fee pending", extracurricular: "Extracurricular",
  marks_trend: "Marks trend", feedback_sentiment: "Feedback tone", family_income: "Family income",
  parent_education: "Parent education",
};

export default function ModelInsights() {
  const { data: m, error, isLoading } = useGetMetricsQuery();
  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <ErrorMsg error={error} />;

  const importance = Object.entries(m.feature_importance).map(([k, v]) => ({ name: LABELS[k] || k, value: v }));
  const cm = m.confusion_matrix;
  const roc = m.roc_curve.map((p) => ({ ...p, random: p.fpr }));

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Model insights</h1>
          <p className="muted">
            XGBoost · version {m.version} · trained on {m.dataset.train_rows} students, tested on {m.dataset.test_rows} unseen students
            · dropout rate {Math.round(m.dataset.dropout_rate * 100)}%
          </p>
        </div>
      </header>

      <section className="stats">
        <Stat label="ROC-AUC" value={m.test.roc_auc.toFixed(3)} hint="ranking quality (0.5 = random)" />
        <Stat label="Recall" value={`${Math.round(m.test.recall * 100)}%`} tone="good" hint="at-risk students caught" />
        <Stat label="Precision" value={`${Math.round(m.test.precision * 100)}%`} hint="flags that were correct" />
        <Stat label="F2 score" value={m.test.f2.toFixed(3)} hint="recall-weighted F-score" />
        <Stat label="Threshold" value={m.threshold} hint="tuned for F2, not 0.5" />
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Model comparison (5-fold CV)</h2>
          <table>
            <thead><tr><th>Model</th><th>ROC-AUC</th><th>F1</th><th>Recall</th><th>Precision</th></tr></thead>
            <tbody>
              {m.comparison.map((r) => (
                <tr key={r.model}><td>{r.model}</td><td>{r.roc_auc}</td><td>{r.f1}</td><td>{r.recall}</td><td>{r.precision}</td></tr>
              ))}
              <tr className="highlight"><td><b>XGBoost (tuned)</b></td><td><b>{m.cv_auc}</b></td><td colSpan={3} className="muted small">RandomizedSearchCV, 25 trials</td></tr>
            </tbody>
          </table>
          <h3>Best hyper-parameters</h3>
          <div className="chips">
            {Object.entries(m.best_params).map(([k, v]) => <span key={k} className="tag">{k} = {v}</span>)}
          </div>
        </div>

        <div className="card">
          <h2>Confusion matrix (test set)</h2>
          <div className="cm">
            <div />
            <div className="cm-h">Predicted: stays</div>
            <div className="cm-h">Predicted: drops out</div>
            <div className="cm-h side">Actual: stays</div>
            <div className="cm-cell ok">{cm.tn}<small>true negative</small></div>
            <div className="cm-cell warn">{cm.fp}<small>false alarm</small></div>
            <div className="cm-h side">Actual: drops out</div>
            <div className="cm-cell bad">{cm.fn}<small>missed</small></div>
            <div className="cm-cell ok">{cm.tp}<small>caught</small></div>
          </div>
          <p className="muted small">
            We accept more false alarms to miss fewer real dropouts — a counselling call costs little, a dropout costs a lot.
          </p>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>ROC curve</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={roc}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fpr" type="number" domain={[0, 1]} label={{ value: "False positive rate", position: "insideBottom", offset: -4, fontSize: 12 }} />
              <YAxis domain={[0, 1]} />
              <Tooltip />
              <Line dataKey="tpr" name="XGBoost" stroke="#4f46e5" strokeWidth={3} dot={false} />
              <Line dataKey="random" name="Random guess" stroke="#94a3b8" strokeDasharray="5 5" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h2>Global feature importance</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={importance} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" name="Gain" fill="#4f46e5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  );
}
