import { useSelector } from "react-redux";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AddStudent from "./pages/AddStudent";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import ModelInsights from "./pages/ModelInsights";
import Register from "./pages/Register";
import StudentDetail from "./pages/StudentDetail";
import Students from "./pages/Students";
import WhatIf from "./pages/WhatIf";

function Protected({ children }) {
  const token = useSelector((s) => s.auth.token);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/students" element={<Students />} />
        <Route path="/students/new" element={<AddStudent />} />
        <Route path="/students/:id" element={<StudentDetail />} />
        <Route path="/what-if" element={<WhatIf />} />
        <Route path="/model" element={<ModelInsights />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
