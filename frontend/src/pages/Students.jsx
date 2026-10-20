import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorMsg, RiskBadge } from "../components/ui";
import { useGetStudentsQuery, useUploadCsvMutation } from "../store/api";

const CLASSES = ["9A", "9B", "10A", "10B", "11A", "12A"];

export default function Students() {
  // filters are kept in the query string
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("search") || "");
  const filters = Object.fromEntries(params.entries());
  const page = Number(filters.page || 1);
  const { data, error, isFetching } = useGetStudentsQuery({ size: 15, ...filters });

  const setFilter = (key, value) => {
    const next = { ...filters, page: 1, [key]: value };
    if (!value) delete next[key];
    setParams(next);
  };

  useEffect(() => {
    const t = setTimeout(() => {
      if (search !== (params.get("search") || "")) setFilter("search", search);
    }, 300);
    return () => clearTimeout(t);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Students</h1>
          <p className="muted">Latest dropout-risk prediction for each student</p>
        </div>
        <div className="row">
          <CsvUpload />
          <Link className="btn primary" to="/students/new">+ Add student</Link>
        </div>
      </header>

      <div className="card filters">
        <input placeholder="Search name or roll no…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={filters.risk_level || ""} onChange={(e) => setFilter("risk_level", e.target.value)}>
          <option value="">All risk levels</option>
          <option>High</option><option>Medium</option><option>Low</option>
        </select>
        <select value={filters.class_name || ""} onChange={(e) => setFilter("class_name", e.target.value)}>
          <option value="">All classes</option>
          {CLASSES.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={filters.sort || "risk"} onChange={(e) => setFilter("sort", e.target.value === "risk" ? "" : e.target.value)}>
          <option value="risk">Sort: Highest risk</option>
          <option value="recent">Sort: Recently added</option>
          <option value="name">Sort: Name (A–Z)</option>
        </select>
        <span className="muted small">{data?.total ?? 0} students {isFetching && "· updating…"}</span>
      </div>

      <ErrorMsg error={error} />

      <div className="card table-card">
        <table>
          <thead>
            <tr><th>Name</th><th>Roll no</th><th>Class</th><th>Attendance</th><th>Marks</th><th>Main reason</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {data?.items.map((s) => (
              <tr key={s.id}>
                <td><Link to={`/students/${s.id}`}>{s.name}</Link></td>
                <td>{s.roll_number}</td>
                <td>{s.class_name}</td>
                <td>{s.attendance_pct ?? "—"}%</td>
                <td>{s.avg_marks ?? "—"}</td>
                <td className="muted">{s.top_reason || "—"}</td>
                <td><RiskBadge level={s.risk_level} probability={s.risk_probability} /></td>
              </tr>
            ))}
            {data?.items.length === 0 && <tr><td colSpan={7} className="muted">No students match these filters.</td></tr>}
          </tbody>
        </table>
        <div className="pager">
          <button className="btn ghost sm" disabled={page <= 1} onClick={() => setFilter("page", page - 1)}>← Prev</button>
          <span>Page {page} of {pages}</span>
          <button className="btn ghost sm" disabled={page >= pages} onClick={() => setFilter("page", page + 1)}>Next →</button>
        </div>
      </div>
    </>
  );
}

function CsvUpload() {
  const input = useRef();
  const [upload, { data, error, isLoading, reset }] = useUploadCsvMutation();
  return (
    <>
      <input ref={input} type="file" accept=".csv" hidden
        onChange={(e) => { if (e.target.files[0]) upload(e.target.files[0]); e.target.value = ""; }} />
      <button className="btn ghost" disabled={isLoading} onClick={() => input.current.click()}>
        {isLoading ? "Uploading…" : "Import CSV"}
      </button>
      {(data || error) && (
        <div className="toast" onClick={reset}>
          {error ? <ErrorMsg error={error} /> : (
            <>
              <b>{data.imported} imported</b>, {data.failed} failed
              {data.errors.slice(0, 3).map((e) => <div key={e.line} className="small">Line {e.line}: {e.error}</div>)}
              <div className="small muted">click to dismiss</div>
            </>
          )}
        </div>
      )}
    </>
  );
}
