import type { DashboardSummary } from "../types";

interface DashboardSectionProps {
  summary: DashboardSummary | null;
}

export function DashboardSection({ summary }: DashboardSectionProps) {
  if (!summary) {
    return null;
  }

  return (
    <section className="card">
      <h2>Progress dashboard</h2>
      <div className="dashboard-grid">
        <div className="stat-card">
          <h4>Lab progress</h4>
          {summary.labs.length ? (
            summary.labs.map((lab) => (
              <span key={lab.id}>
                {lab.title}: {lab.score}/{lab.total_flags}
              </span>
            ))
          ) : (
            <span>No lab attempts yet.</span>
          )}
        </div>
        <div className="stat-card">
          <h4>Quiz history</h4>
          {summary.quizzes.length ? (
            summary.quizzes.map((quiz) => (
              <span key={`${quiz.quiz_id}-${quiz.submitted_at}`}>
                {quiz.quiz_id}: {quiz.score}/{quiz.max_score}
              </span>
            ))
          ) : (
            <span>No quiz submissions yet.</span>
          )}
        </div>
        <div className="stat-card">
          <h4>Exam history</h4>
          {summary.exams.length ? (
            summary.exams.map((exam) => (
              <span key={`${exam.exam_id}-${exam.stage_id}-${exam.submitted_at}`}>
                {exam.exam_id} · {exam.stage_id}: {exam.score}/{exam.max_score}
              </span>
            ))
          ) : (
            <span>No exam submissions yet.</span>
          )}
        </div>
      </div>
    </section>
  );
}
