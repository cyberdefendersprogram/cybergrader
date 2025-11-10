import type { DashboardSummary, ExamSubmissionResult, FlagSubmissionResult, QuizSubmissionResult } from "../types";

interface ActivitySectionProps {
  summary: DashboardSummary | null;
}

function toLocal(ts: string): string {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function ActivitySection({ summary }: ActivitySectionProps) {
  if (!summary) {
    return (
      <div className="card login-card">
        <h3 style={{ marginTop: 0 }}>Activity</h3>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>Loading your recent activity…</p>
      </div>
    );
  }

  const labs: FlagSubmissionResult[] = summary.labs || [];
  const quizzes: QuizSubmissionResult[] = summary.quizzes || [];
  const exams: ExamSubmissionResult[] = summary.exams || [];

  return (
    <div className="card login-card">
      <h3 style={{ marginTop: 0 }}>Activity</h3>
      <p style={{ marginTop: 0, color: "var(--text-secondary)" }}>Your latest submissions and scores.</p>

      <div style={{ display: "grid", gap: "1rem" }}>
        <section>
          <h4 style={{ margin: 0 }}>Lab submissions</h4>
          {labs.length === 0 ? (
            <p style={{ color: "var(--text-secondary)" }}>No lab flags submitted yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th align="left">Lab</th>
                  <th align="left">Flag</th>
                  <th align="left">Result</th>
                  <th align="left">When</th>
                </tr>
              </thead>
              <tbody>
                {labs.map((r, i) => (
                  <tr key={`lab-${i}`}>
                    <td>{r.lab_id}</td>
                    <td>{r.flag_name}</td>
                    <td>{r.correct ? "✅ Correct" : "❌ Incorrect"}</td>
                    <td>{toLocal(r.submitted_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h4 style={{ margin: 0 }}>Quiz attempts</h4>
          {quizzes.length === 0 ? (
            <p style={{ color: "var(--text-secondary)" }}>No quizzes attempted yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th align="left">Quiz</th>
                  <th align="left">Score</th>
                  <th align="left">When</th>
                </tr>
              </thead>
              <tbody>
                {quizzes.map((q, i) => (
                  <tr key={`quiz-${i}`}>
                    <td>{q.quiz_id}</td>
                    <td>
                      {q.score}/{q.max_score}
                    </td>
                    <td>{toLocal(q.submitted_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h4 style={{ margin: 0 }}>Exam submissions</h4>
          {exams.length === 0 ? (
            <p style={{ color: "var(--text-secondary)" }}>No exams attempted yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th align="left">Exam</th>
                  <th align="left">Stage</th>
                  <th align="left">Score</th>
                  <th align="left">When</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((e, i) => (
                  <tr key={`exam-${i}`}>
                    <td>{e.exam_id}</td>
                    <td>{e.stage_id}</td>
                    <td>
                      {e.score}/{e.max_score}
                    </td>
                    <td>{toLocal(e.submitted_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}

