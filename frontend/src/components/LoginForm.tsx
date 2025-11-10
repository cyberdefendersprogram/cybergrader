import { useState } from "react";
import type { LoginRequest } from "../types";

interface LoginFormProps {
  onSubmit: (payload: LoginRequest) => Promise<void>;
  isSubmitting?: boolean;
  onForgotPassword?: (email: string) => void;
  onSignupNavigate?: () => void;
}

export function LoginForm({ onSubmit, isSubmitting, onForgotPassword, onSignupNavigate }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
        <span className="badge">Welcome back</span>
        <h2>Sign in to Cyber Grader</h2>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>
          We saved you a seat. Enter your email and password to continue.
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
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
        <button
          type="button"
          className="secondary-button"
          onClick={() => (onForgotPassword ? onForgotPassword(email) : undefined)}
        >
          Forgot password?
        </button>
        <button type="button" className="secondary-button" onClick={onSignupNavigate}>
          Create account
        </button>
      </div>
    </div>
  );
}
