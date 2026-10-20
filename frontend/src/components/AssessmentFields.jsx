export const emptyAssessment = {
  term: "Term 1",
  attendance_pct: 75,
  avg_marks: 60,
  prev_marks: 60,
  assignment_completion: 70,
  behavior_score: 70,
  failed_subjects: 0,
  fee_pending: false,
  extracurricular: false,
  teacher_feedback: "",
};

const NUMBERS = [
  ["attendance_pct", "Attendance %", 0, 100],
  ["avg_marks", "Average marks (this term)", 0, 100],
  ["prev_marks", "Marks (previous term)", 0, 100],
  ["assignment_completion", "Assignment completion %", 0, 100],
  ["behavior_score", "Behaviour score", 0, 100],
  ["failed_subjects", "Failed subjects", 0, 10],
];

export default function AssessmentFields({ value, onChange, showTerm = true }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <div className="grid-form">
      {showTerm && (
        <label>
          Term
          <input value={value.term} onChange={(e) => set("term", e.target.value)} required />
        </label>
      )}
      {NUMBERS.map(([k, label, min, max]) => (
        <label key={k}>
          {label}
          <input
            type="number" min={min} max={max} step="any" required
            value={value[k]}
            onChange={(e) => set(k, e.target.value === "" ? "" : Number(e.target.value))}
          />
        </label>
      ))}
      <label className="check">
        <input type="checkbox" checked={value.fee_pending} onChange={(e) => set("fee_pending", e.target.checked)} />
        Fee pending
      </label>
      <label className="check">
        <input type="checkbox" checked={value.extracurricular} onChange={(e) => set("extracurricular", e.target.checked)} />
        Takes part in extracurriculars
      </label>
      <label className="wide">
        Teacher feedback
        <textarea
          rows={2} placeholder="e.g. Irregular lately, seems distracted in class"
          value={value.teacher_feedback || ""}
          onChange={(e) => set("teacher_feedback", e.target.value)}
        />
      </label>
    </div>
  );
}
