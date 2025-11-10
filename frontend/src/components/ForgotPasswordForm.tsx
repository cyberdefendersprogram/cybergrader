import { useState } from "react";

interface ForgotPasswordFormProps {
  onRequest: (email: string) => Promise<void>;
  isSubmitting?: boolean;
  onBack?: () => void;
}

export function ForgotPasswordForm({ onRequest, isSubmitting, onBack }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState("");
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setInfo(null);
    setError(null);
    try {
      await onRequest(email);
      setInfo("If that email is registered, a reset link is on its way ✉️");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setError(message);
    }
  };

  return (
    <div className="card login-card">
      <div>
        <span className="badge">No worries</span>
        <h2>Reset your password</h2>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>Enter your email and check your inbox for a link.</p>
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Email address
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Sending..." : "Send reset link"}</button>
        {info && <p className="toast" style={{ position: "static" }}>{info}</p>}
        {error && <p className="toast toast--error" style={{ position: "static" }}>{error}</p>}
      </form>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
        <button type="button" className="secondary-button" onClick={onBack}>Back to sign in</button>
      </div>
    </div>
  );
}

