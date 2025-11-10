import { useState } from "react";

interface SignupFormProps {
  onSubmit: (payload: { email: string; password: string }) => Promise<void>;
  isSubmitting?: boolean;
  onLoginNavigate?: () => void;
}

export function SignupForm({ onSubmit, isSubmitting, onLoginNavigate }: SignupFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    try {
      await onSubmit({ email, password });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to create account";
      setError(message);
    }
  };

  return (
    <div className="card login-card">
      <div>
        <span className="badge">New here?</span>
        <h2>Create your account</h2>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>Takes 10 seconds. No email verification required.</p>
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Email address
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating..." : "Create account"}</button>
        {error && <p className="toast toast--error" style={{ position: "static" }}>{error}</p>}
      </form>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
        <button type="button" className="secondary-button" onClick={onLoginNavigate}>
          Back to sign in
        </button>
      </div>
    </div>
  );
}
