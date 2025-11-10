import { useState } from "react";

interface ResetPasswordFormProps {
  token: string;
  onReset: (token: string, newPassword: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function ResetPasswordForm({ token, onReset, isSubmitting }: ResetPasswordFormProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    try {
      await onReset(token, password);
      setInfo("Password updated. You can sign in now 🚀");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reset password";
      setError(message);
    }
  };

  return (
    <div className="card login-card">
      <div>
        <span className="badge">Almost there</span>
        <h2>Create a new password</h2>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>Be kind to your future self — pick one you’ll remember.</p>
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          New password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Updating..." : "Update password"}</button>
        {info && <p className="toast" style={{ position: "static" }}>{info}</p>}
        {error && <p className="toast toast--error" style={{ position: "static" }}>{error}</p>}
      </form>
    </div>
  );
}

