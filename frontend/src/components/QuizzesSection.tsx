import { useMemo, useState } from "react";
import type { QuizDefinition } from "../types";

interface QuizzesSectionProps {
  quizzes: QuizDefinition[];
  onSubmitQuiz: (quizId: string, answers: Record<string, string>) => Promise<void>;
  isSubmitting?: boolean;
}

export function QuizzesSection({ quizzes, onSubmitQuiz, isSubmitting }: QuizzesSectionProps) {
  const [answers, setAnswers] = useState<Record<string, Record<string, string>>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [activeIndex, setActiveIndex] = useState(0);

  const activeQuiz: QuizDefinition | null = useMemo(() => {
    if (!quizzes.length) return null;
    if (activeIndex < 0) return quizzes[0];
    if (activeIndex >= quizzes.length) return quizzes[quizzes.length - 1];
    return quizzes[activeIndex];
  }, [quizzes, activeIndex]);

  if (!quizzes.length || !activeQuiz) {
    return null;
  }

  const isAnswerCorrect = (question: QuizDefinition["questions"][number], value: string | undefined): boolean | null => {
    if (!value) return null;
    if (question.type === "multiple_choice") {
      return value === question.answer;
    }
    return value.trim().toLowerCase() === question.answer.trim().toLowerCase();
  };

  const handleSubmit = async (quizId: string) => {
    const quizAnswers = answers[quizId] || {};
    if (!Object.keys(quizAnswers).length) {
      setErrors((prev) => ({ ...prev, [quizId]: "Answer at least one question before submitting." }));
      return;
    }
    try {
      await onSubmitQuiz(quizId, quizAnswers);
      setAnswers((prev) => ({ ...prev, [quizId]: {} }));
      setErrors((prev) => ({ ...prev, [quizId]: null }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Quiz submission failed";
      setErrors((prev) => ({ ...prev, [quizId]: message }));
    }
  };

  const quiz = activeQuiz;
  const quizAnswers = answers[quiz.id] || {};

  return (
    <section className="card card--full">
      <h2>Knowledge checks</h2>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
            disabled={activeIndex === 0}
          >
            ← Prev
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setActiveIndex((i) => Math.min(quizzes.length - 1, i + 1))}
            disabled={activeIndex >= quizzes.length - 1}
          >
            Next →
          </button>
        </div>
        <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
          Quiz {activeIndex + 1} of {quizzes.length}
        </div>
      </div>

      <article className="quiz-card" key={quiz.id}>
        <header>
          <h3 style={{ margin: 0 }}>{quiz.title}</h3>
          <span>Version {quiz.version}</span>
        </header>
        <div className="section-grid">
          {quiz.questions.map((question) => {
            const value = quizAnswers[question.id];
            const correct = isAnswerCorrect(question, value);
            return (
              <div key={question.id}>
                <p style={{ marginBottom: "0.5rem", fontWeight: 600 }}>{question.prompt}</p>
                {question.type === "multiple_choice" ? (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                      alignItems: "flex-start"
                    }}
                  >
                    {question.choices.map((choice) => {
                      const selected = value === choice.key;
                      const selectedAndChecked = selected && correct !== null;
                      const bg = selectedAndChecked
                        ? correct
                          ? "rgba(34, 197, 94, 0.18)" // green
                          : "rgba(239, 68, 68, 0.18)" // red
                        : selected
                        ? "rgba(56, 189, 248, 0.18)"
                        : "rgba(15, 23, 42, 0.55)";
                      const borderColor = selectedAndChecked
                        ? correct
                          ? "rgba(34, 197, 94, 0.6)"
                          : "rgba(239, 68, 68, 0.6)"
                        : "rgba(148, 163, 184, 0.25)";
                      return (
                        <label
                          key={choice.key}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.65rem",
                            padding: "0.55rem 0.75rem",
                            borderRadius: "12px",
                            border: `1px solid ${borderColor}`,
                            background: bg,
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                            width: "auto",
                            maxWidth: "100%",
                            justifyContent: "flex-start"
                          }}
                        >
                          <input
                            type="radio"
                            name={`${quiz.id}-${question.id}`}
                            value={choice.key}
                            checked={selected}
                            onChange={(event) =>
                              setAnswers((prev) => ({
                                ...prev,
                                [quiz.id]: { ...prev[quiz.id], [question.id]: event.target.value }
                              }))
                            }
                          />
                          <span>{choice.label}</span>
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ display: "grid", gap: "0.5rem" }}>
                    <textarea
                      rows={3}
                      value={value || ""}
                      onChange={(event) =>
                        setAnswers((prev) => ({
                          ...prev,
                          [quiz.id]: { ...prev[quiz.id], [question.id]: event.target.value }
                        }))
                      }
                    />
                    {value && (
                      <span style={{ fontSize: "0.9rem", color: correct ? "#22c55e" : "#ef4444" }}>
                        {correct ? "Looks correct" : "Not correct"}
                      </span>
                    )}
                  </div>
                )}
                {question.type === "multiple_choice" && value && (
                  <div style={{ marginTop: "0.25rem", fontSize: "0.9rem", color: correct ? "#22c55e" : "#ef4444" }}>
                    {correct ? "Correct" : "Incorrect"}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div className="quiz-actions">
          <button type="button" onClick={() => handleSubmit(quiz.id)} disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit quiz"}
          </button>
          {errors[quiz.id] && (
            <span style={{ color: "var(--error)", fontSize: "0.85rem" }}>{errors[quiz.id]}</span>
          )}
        </div>
      </article>
    </section>
  );
}
