import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, Navigate } from "react-router-dom";
import { ErrorMsg } from "../components/ui";
import { useLoginMutation } from "../store/api";
import { loggedIn } from "../store/authSlice";

export default function Login() {
  const token = useSelector((s) => s.auth.token);
  const dispatch = useDispatch();
  const [login, { isLoading, error }] = useLoginMutation();
  const [form, setForm] = useState({ email: "", password: "" });

  if (token) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    const res = await login(form);
    if (res.data) dispatch(loggedIn(res.data));
  };

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand big">
          <span className="brand-mark">E</span>
          <div>
            <strong>EduTrack AI</strong>
            <small>Student dropout early-warning system</small>
          </div>
        </div>
        <label>
          Email
          <input type="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label>
          Password
          <input type="password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
        <ErrorMsg error={error} />
        <button className="btn primary" disabled={isLoading}>{isLoading ? "Signing in…" : "Sign in"}</button>
        <p className="muted small">New here? <Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}
