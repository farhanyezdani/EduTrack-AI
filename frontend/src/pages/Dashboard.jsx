import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorMsg, RiskBadge, Stat } from "../components/ui";
import { useGetStudentsQuery, useGetSummaryQuery } from "../store/api";

export const RISK_COLORS = { High: "#dc2626", Medium: "#d97706", Low: "#16a34a" };

export default function Dashboard() {
  const { data: s, error, isLoading } = useGetSummaryQuery();
  const { data: top } = useGetStudentsQuery({ risk_level: "High", size: 6 });

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <ErrorMsg error={error} />;

  const pie = [
    { name: "High", value: s.high_risk },
    { name: "Medium", value: s.medium_risk },
    { name: "Low", value: s.low_risk },
  ];

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Latest risk prediction for every student{s.cached && " · served from Redis cache"}</p>
        </div>
        <Link className="btn primary" to="/students/new">+ Add student</Link>
      </header>

      <section className="stats">
        <Stat label="Students" value={s.total_students} />
        <Stat label="High risk" value={s.high_risk} tone="high" hint="needs action now" />
        <Stat label="Medium risk" value={s.medium_risk} tone="medium" hint="monitor closely" />
        <Stat label="Avg attendance" value={`${s.avg_attendance}%`} />
        <Stat label="Open interventions" value={s.open_interventions} />
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Risk distribution</h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                {pie.map((p) => <Cell key={p.name} fill={RISK_COLORS[p.name]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h2>Risk by class</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={s.by_class}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="class_name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="high" name="High" stackId="r" fill={RISK_COLORS.High} />
              <Bar dataKey="medium" name="Medium" stackId="r" fill={RISK_COLORS.Medium} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Risk score spread</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={s.risk_histogram}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="range" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" name="Students" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h2>Most common risk drivers</h2>
          <p className="muted small">Top SHAP factor for each medium/high risk student</p>
          <ul className="drivers">
            {s.top_drivers.map((d) => (
              <li key={d.label}>
                <span>{d.label}</span>
                <div className="meter"><div style={{ width: `${(d.count / s.top_drivers[0].count) * 100}%` }} /></div>
                <b>{d.count}</b>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card">
        <div className="row-between">
          <h2>Highest risk students</h2>
          <Link to="/students?risk_level=High">View all →</Link>
        </div>
        <table>
          <thead><tr><th>Name</th><th>Class</th><th>Attendance</th><th>Main reason</th><th>Risk</th></tr></thead>
          <tbody>
            {top?.items.map((st) => (
              <tr key={st.id}>
                <td><Link to={`/students/${st.id}`}>{st.name}</Link></td>
                <td>{st.class_name}</td>
                <td>{st.attendance_pct}%</td>
                <td>{st.top_reason}</td>
                <td><RiskBadge level={st.risk_level} probability={st.risk_probability} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
