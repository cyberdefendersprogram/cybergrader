import { useState } from "react";
import type { LoginRequest } from "../types";

interface LoginFormProps {
  onSubmit: (payload: LoginRequest) => Promise<void>;
  isSubmitting?: boolean;
}

export function LoginForm({ onSubmit, isSubmitting }: LoginFormProps) {
  const [email, setEmail] = useState("alice@student.edu");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      await onSubmit({ email, password });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to sign in";
      setError(message);
    }
  };

  return (
    <div className="card login-card">
      <div>
        <span className="badge">Demo environment</span>
        <h2>Sign in to Cyber Grader</h2>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>
          Use one of the sample accounts below to explore the full experience.
        </p>
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Email address
          <input
            type="email"
            value={email}
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
        {error && <p className="toast toast--error" style={{ position: "static" }}>{error}</p>}
      </form>
      <div style={{ display: "grid", gap: "0.4rem", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
        <strong style={{ color: "var(--text-primary)" }}>Sample roles</strong>
        <span>alice@student.edu — Student</span>
        <span>sam@staff.edu — Staff</span>
        <span>ada@admin.edu — Admin</span>
      </div>
    </div>
  );
}
