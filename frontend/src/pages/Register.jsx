import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, Navigate } from "react-router-dom";
import { ErrorMsg } from "../components/ui";
import { useRegisterMutation } from "../store/api";
import { loggedIn } from "../store/authSlice";

export default function Register() {
  const token = useSelector((s) => s.auth.token);
  const dispatch = useDispatch();
  const [register, { isLoading, error }] = useRegisterMutation();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [mismatch, setMismatch] = useState(false);

  if (token) return <Navigate to="/" replace />;

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) return setMismatch(true);
    setMismatch(false);
    const { confirm, ...body } = form;
    const res = await register(body);
    if (res.data) dispatch(loggedIn(res.data));
  };

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand big">
          <span className="brand-mark">E</span>
          <div>
            <strong>Create account</strong>
            <small>Sign up as a teacher on EduTrack AI</small>
          </div>
        </div>
        <label>
          Full name
          <input required minLength={2} value={form.name} onChange={set("name")} />
        </label>
        <label>
          Email
          <input type="email" required value={form.email} onChange={set("email")} />
        </label>
        <label>
          Password
          <input type="password" required minLength={6} value={form.password} onChange={set("password")} />
        </label>
        <label>
          Confirm password
          <input type="password" required minLength={6} value={form.confirm} onChange={set("confirm")} />
        </label>
        {mismatch && <div className="alert error">Passwords do not match</div>}
        <ErrorMsg error={error} />
        <button className="btn primary" disabled={isLoading}>{isLoading ? "Creating…" : "Create account"}</button>
        <p className="muted small">Already have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  );
}
