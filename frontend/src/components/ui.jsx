export const pct = (p) => (p == null ? "—" : `${Math.round(p * 100)}%`);

export function RiskBadge({ level, probability }) {
  if (!level) return <span className="badge none">No data</span>;
  return (
    <span className={`badge ${level.toLowerCase()}`}>
      {level}{probability != null && ` · ${pct(probability)}`}
    </span>
  );
}

export function Stat({ label, value, tone, hint }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

export function ErrorMsg({ error }) {
  if (!error) return null;
  const detail = error.data?.detail;
  const text = Array.isArray(detail)
    ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(", ")
    : detail || "Something went wrong. Is the backend running?";
  return <div className="alert error">{text}</div>;
}

// Diverging bar per feature: red = raises risk, green = lowers it
export function FactorChart({ factors, limit = 7 }) {
  const rows = factors.slice(0, limit);
  const max = Math.max(...rows.map((f) => Math.abs(f.impact)), 0.01);
  const fmt = (v) => (typeof v === "number" ? Math.round(v * 100) / 100 : v);
  return (
    <div className="factors">
      {rows.map((f) => (
        <div className="factor" key={f.feature}>
          <div className="factor-label">
            {f.label} <small>{fmt(f.value)}</small>
          </div>
          <div className="factor-bar">
            <div className="axis" />
            <div
              className={f.impact > 0 ? "bar up" : "bar down"}
              style={{ width: `${(Math.abs(f.impact) / max) * 50}%` }}
              title={`SHAP ${f.impact > 0 ? "+" : ""}${f.impact.toFixed(3)}`}
            />
          </div>
        </div>
      ))}
      <div className="factor-legend">
        <span><i className="dot down" /> lowers risk</span>
        <span><i className="dot up" /> raises risk</span>
      </div>
    </div>
  );
}
