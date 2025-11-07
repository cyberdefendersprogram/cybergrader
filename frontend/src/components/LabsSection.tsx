import { useMemo, useState } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import type { LabFlagPrompt, LabStatus } from "../types";

interface LabsSectionProps {
  labs: LabStatus[];
  onSubmitFlag: (labId: string, flagName: string, submission: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function LabsSection({ labs, onSubmitFlag, isSubmitting }: LabsSectionProps) {
  const [flagValues, setFlagValues] = useState<Record<string, string>>({});
  const [activeLab, setActiveLab] = useState<string | null>(null);

  const renderInstructions = (markdown: string) => {
    const html = marked.parse(markdown, { async: false }) as string;
    return { __html: DOMPurify.sanitize(html) };
  };

  if (!labs.length) {
    return (
      <section className="card">
        <h2>Labs</h2>
        <p style={{ color: "var(--text-secondary)" }}>
          Labs will appear here after content is synchronized. Try logging in as a staff member
          and running a sync from the admin tools.
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Hands-on labs</h2>
      <div className="section-grid">
        {labs.map((lab) => {
          const labKey = lab.id;
          const active = activeLab === null || activeLab === labKey;
          const toggleActive = () => setActiveLab((prev) => (prev === labKey ? null : labKey));
          return (
            <article className="lab-card" key={lab.id}>
              <header>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap" }}>
                  <div>
                    <h3 style={{ margin: 0 }}>{lab.title}</h3>
                    <span>
                      Score {lab.score}/{lab.total_flags}
                    </span>
                  </div>
                  <button type="button" className="secondary-button" onClick={toggleActive}>
                    {active ? "Hide details" : "Show details"}
                  </button>
                </div>
                <span>Version {lab.version}</span>
              </header>
              {active && (
                <div className="section-grid">
                  <div className="markdown" dangerouslySetInnerHTML={renderInstructions(lab.instructions)} />
                  {lab.flags.map((flag) => (
                    <FlagForm
                      key={flag.name}
                      lab={lab}
                      flag={flag}
                      value={flagValues[`${lab.id}:${flag.name}`] || ""}
                      onChange={(value) =>
                        setFlagValues((prev) => ({ ...prev, [`${lab.id}:${flag.name}`]: value }))
                      }
                      onSubmit={async (value) => {
                        await onSubmitFlag(lab.id, flag.name, value);
                        setFlagValues((prev) => ({ ...prev, [`${lab.id}:${flag.name}`]: "" }));
                      }}
                      isSubmitting={isSubmitting}
                    />
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

interface FlagFormProps {
  lab: LabStatus;
  flag: LabFlagPrompt;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => Promise<void>;
  isSubmitting?: boolean;
}

function FlagForm({ lab, flag, value, onChange, onSubmit, isSubmitting }: FlagFormProps) {
  const flagKey = useMemo(() => `${lab.id}:${flag.name}`, [lab.id, flag.name]);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!value) {
      setError("Enter a flag before submitting.");
      return;
    }
    try {
      await onSubmit(value);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed";
      setError(message);
    }
  };

  return (
    <form className="flag-form" onSubmit={handleSubmit} data-flag-key={flagKey}>
      <label>
        {flag.prompt}
        <input value={value} onChange={(event) => onChange(event.target.value)} placeholder="CHALLENGE{...}" />
      </label>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Submitting..." : "Submit flag"}
      </button>
      {error && <span style={{ color: "var(--error)", fontSize: "0.85rem" }}>{error}</span>}
    </form>
  );
}
