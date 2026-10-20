import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AssessmentFields, { emptyAssessment } from "../components/AssessmentFields";
import { ErrorMsg } from "../components/ui";
import { useCreateStudentMutation } from "../store/api";

export const emptyProfile = {
  name: "", roll_number: "", class_name: "10A", parent_contact: "",
  distance_km: 5, family_income: "Medium", parent_education: "School",
};

export function ProfileFields({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <div className="grid-form">
      <label>Full name<input required value={value.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label>Roll number<input required value={value.roll_number} onChange={(e) => set("roll_number", e.target.value)} /></label>
      <label>Class<input required value={value.class_name} onChange={(e) => set("class_name", e.target.value)} /></label>
      <label>Parent contact<input value={value.parent_contact || ""} onChange={(e) => set("parent_contact", e.target.value)} /></label>
      <label>Distance from school (km)
        <input type="number" min={0} max={100} step="any" required value={value.distance_km}
          onChange={(e) => set("distance_km", e.target.value === "" ? "" : Number(e.target.value))} />
      </label>
      <label>Family income
        <select value={value.family_income} onChange={(e) => set("family_income", e.target.value)}>
          <option>Low</option><option>Medium</option><option>High</option>
        </select>
      </label>
      <label>Parent education
        <select value={value.parent_education} onChange={(e) => set("parent_education", e.target.value)}>
          <option>None</option><option>School</option><option>Graduate</option>
        </select>
      </label>
    </div>
  );
}

export default function AddStudent() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(emptyProfile);
  const [assessment, setAssessment] = useState(emptyAssessment);
  const [create, { isLoading, error }] = useCreateStudentMutation();

  const submit = async (e) => {
    e.preventDefault();
    const res = await create({ ...profile, parent_contact: profile.parent_contact || null, assessment });
    if (res.data) navigate(`/students/${res.data.id}`);
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Add student</h1>
          <p className="muted">The ML model predicts dropout risk as soon as you save.</p>
        </div>
      </header>
      <form onSubmit={submit}>
        <div className="card">
          <h2>Profile</h2>
          <ProfileFields value={profile} onChange={setProfile} />
        </div>
        <div className="card">
          <h2>Current term</h2>
          <AssessmentFields value={assessment} onChange={setAssessment} />
        </div>
        <ErrorMsg error={error} />
        <button className="btn primary" disabled={isLoading}>{isLoading ? "Predicting…" : "Save & predict risk"}</button>
      </form>
    </>
  );
}
