import { useDispatch, useSelector } from "react-redux";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../store/api";
import { loggedOut } from "../store/authSlice";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/students", label: "Students", end: true },
  { to: "/students/new", label: "Add Student" },
  { to: "/what-if", label: "What-If Simulator" },
  { to: "/model", label: "Model Insights" },
];

export default function Layout() {
  const user = useSelector((s) => s.auth.user);
  const dispatch = useDispatch();

  const logout = () => {
    dispatch(loggedOut());
    dispatch(api.util.resetApiState());
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">E</span>
          <div>
            <strong>EduTrack AI</strong>
            <small>Dropout early-warning</small>
          </div>
        </div>
        <nav>
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>{l.label}</NavLink>
          ))}
        </nav>
        <div className="user-box">
          <div>
            <strong>{user?.name}</strong>
            <small>{user?.role}</small>
          </div>
          <button className="btn ghost sm" onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
