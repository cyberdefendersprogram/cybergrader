interface OnboardingProps {
  onSignup: () => void;
  onLogin: () => void;
}

export function Onboarding({ onSignup, onLogin }: OnboardingProps) {
  return (
    <div className="card login-card" style={{ textAlign: "left", maxWidth: 640 }}>
      <span className="badge">Welcome</span>
      <h2 style={{ marginTop: 8 }}>Cyber Grader</h2>
      <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>
        Learn by doing. Tackle hands‑on labs, quick quizzes, and capstone exams —
        then watch your skills graph climb. We keep it simple, fast, and a little fun.
      </p>
      <ul style={{ color: "var(--text-secondary)", lineHeight: 1.7 }}>
        <li>Sign up with your email — no hoops.</li>
        <li>Add your Student ID once and you're set.</li>
        <li>Practice, submit, improve. Rinse and repeat.</li>
      </ul>
      <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
        <button type="button" onClick={onSignup}>Get started</button>
        <button type="button" className="secondary-button" onClick={onLogin}>I have an account</button>
      </div>
    </div>
  );
}

