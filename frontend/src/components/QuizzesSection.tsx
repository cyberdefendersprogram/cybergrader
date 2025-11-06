import { useState } from "react";
import type { QuizDefinition } from "../types";

interface QuizzesSectionProps {
  quizzes: QuizDefinition[];
  onSubmitQuiz: (quizId: string, answers: Record<string, string>) => Promise<void>;
  isSubmitting?: boolean;
}

export function QuizzesSection({ quizzes, onSubmitQuiz, isSubmitting }: QuizzesSectionProps) {
  const [answers, setAnswers] = useState<Record<string, Record<string, string>>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  if (!quizzes.length) {
    return null;
  }

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

  return (
    <section className="card">
      <h2>Knowledge checks</h2>
      <div className="section-grid">
        {quizzes.map((quiz) => {
          const quizAnswers = answers[quiz.id] || {};
          return (
            <article className="quiz-card" key={quiz.id}>
              <header>
                <h3 style={{ margin: 0 }}>{quiz.title}</h3>
                <span>Version {quiz.version}</span>
              </header>
              <div className="section-grid">
                {quiz.questions.map((question) => (
                  <div key={question.id}>
                    <p style={{ marginBottom: "0.5rem", fontWeight: 600 }}>{question.prompt}</p>
                    {question.type === "multiple_choice" ? (
                      <div style={{ display: "grid", gap: "0.5rem" }}>
                        {question.choices.map((choice) => (
                          <label
                            key={choice.key}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "0.65rem",
                              padding: "0.55rem 0.75rem",
                              borderRadius: "12px",
                              border: "1px solid rgba(148, 163, 184, 0.25)",
                              background:
                                quizAnswers[question.id] === choice.key
                                  ? "rgba(56, 189, 248, 0.18)"
                                  : "rgba(15, 23, 42, 0.55)",
                              cursor: "pointer"
                            }}
                          >
                            <input
                              type="radio"
                              name={`${quiz.id}-${question.id}`}
                              value={choice.key}
                              checked={quizAnswers[question.id] === choice.key}
                              onChange={(event) =>
                                setAnswers((prev) => ({
                                  ...prev,
                                  [quiz.id]: { ...prev[quiz.id], [question.id]: event.target.value }
                                }))
                              }
                            />
                            <span>{choice.label}</span>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <textarea
                        rows={3}
                        value={quizAnswers[question.id] || ""}
                        onChange={(event) =>
                          setAnswers((prev) => ({
                            ...prev,
                            [quiz.id]: { ...prev[quiz.id], [question.id]: event.target.value }
                          }))
                        }
                      />
                    )}
                  </div>
                ))}
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
          );
        })}
      </div>
    </section>
  );
}
