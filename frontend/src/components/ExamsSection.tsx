import { useState } from "react";
import type { ExamDefinition } from "../types";

interface ExamsSectionProps {
  exams: ExamDefinition[];
  onSubmitExam: (examId: string, stageId: string, answer: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function ExamsSection({ exams, onSubmitExam, isSubmitting }: ExamsSectionProps) {
  const [responses, setResponses] = useState<Record<string, Record<string, string>>>({});
  const [activeStage, setActiveStage] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  if (!exams.length) {
    return null;
  }

  const handleSubmit = async (examId: string) => {
    const stageId = activeStage[examId] || exams.find((exam) => exam.id === examId)?.stages[0]?.id;
    if (!stageId) {
      return;
    }
    const answer = responses[examId]?.[stageId] || "";
    if (!answer.trim()) {
      setErrors((prev) => ({ ...prev, [examId]: "Add a response before submitting." }));
      return;
    }
    try {
      await onSubmitExam(examId, stageId, answer);
      setResponses((prev) => ({ ...prev, [examId]: { ...prev[examId], [stageId]: "" } }));
      setErrors((prev) => ({ ...prev, [examId]: null }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Exam submission failed";
      setErrors((prev) => ({ ...prev, [examId]: message }));
    }
  };

  return (
    <section className="card">
      <h2>Capstone exam</h2>
      <div className="section-grid">
        {exams.map((exam) => {
          const stageId = activeStage[exam.id] || exam.stages[0]?.id;
          const stage = exam.stages.find((item) => item.id === stageId) ?? exam.stages[0];
          return (
            <article className="exam-card" key={exam.id}>
              <header>
                <h3 style={{ margin: 0 }}>{exam.title}</h3>
                <span>Version {exam.version}</span>
              </header>
              {stage && (
                <div className="section-grid">
                  <label>
                    Stage
                    <select
                      value={stage.id}
                      onChange={(event) =>
                        setActiveStage((prev) => ({ ...prev, [exam.id]: event.target.value }))
                      }
                    >
                      {exam.stages.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p style={{ margin: 0, color: "var(--text-secondary)" }}>{stage.description}</p>
                  <label>
                    Response
                    <textarea
                      rows={4}
                      value={responses[exam.id]?.[stage.id] || ""}
                      onChange={(event) =>
                        setResponses((prev) => ({
                          ...prev,
                          [exam.id]: { ...prev[exam.id], [stage.id]: event.target.value }
                        }))
                      }
                    />
                  </label>
                </div>
              )}
              <div className="exam-actions">
                <button type="button" onClick={() => handleSubmit(exam.id)} disabled={isSubmitting}>
                  {isSubmitting ? "Submitting..." : "Submit stage"}
                </button>
                {errors[exam.id] && (
                  <span style={{ color: "var(--error)", fontSize: "0.85rem" }}>{errors[exam.id]}</span>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
