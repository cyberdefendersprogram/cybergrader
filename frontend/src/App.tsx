import { useCallback, useEffect, useMemo, useState } from "react";
import { api, API_BASE, HttpError } from "./api";
import { ExamsSection } from "./components/ExamsSection";
import { DashboardSection } from "./components/DashboardSection";
import { LabsSection } from "./components/LabsSection";
import { LoginForm } from "./components/LoginForm";
import { NotesSection } from "./components/NotesSection";
import { QuizzesSection } from "./components/QuizzesSection";
import type {
  DashboardSummary,
  ExamDefinition,
  LabStatus,
  LoginResponse,
  NoteDocument,
  QuizDefinition
} from "./types";

interface ToastState {
  kind: "success" | "error" | "info";
  message: string;
}

export default function App() {
  const [user, setUser] = useState<LoginResponse | null>(null);
  const [labs, setLabs] = useState<LabStatus[]>([]);
  const [quizzes, setQuizzes] = useState<QuizDefinition[]>([]);
  const [exams, setExams] = useState<ExamDefinition[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [note, setNote] = useState<NoteDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const welcomeMessage = useMemo(() => {
    if (!user) return "";
    return `Welcome back, ${user.user_id}`;
  }, [user]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const loadContent = useCallback(async (userId: string) => {
    setIsLoading(true);
    try {
      const [labData, quizData, examData, dashboardData, noteData] = await Promise.all([
        api.listLabs(userId),
        api.listQuizzes(),
        api.listExams(),
        api.dashboard(userId),
        api.getNote("lecture-01").catch(() => null)
      ]);
      setLabs(labData);
      setQuizzes(quizData);
      setExams(examData);
      setSummary(dashboardData);
      setNote(noteData);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleLogin = useCallback(async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      const payload = await api.login(credentials);
      setUser(payload);
      setToast({ kind: "success", message: `Signed in as ${payload.user_id} (${payload.role})` });
      await loadContent(payload.user_id);
    } finally {
      setIsLoading(false);
    }
  }, [loadContent]);

  const handleFlagSubmission = useCallback(
    async (labId: string, flagName: string, submission: string) => {
      if (!user) return;
      setIsLoading(true);
      try {
        const result = await api.submitFlag(labId, flagName, user.user_id, submission);
        setToast({
          kind: result.correct ? "success" : "error",
          message: result.correct ? "Flag accepted!" : "Flag was incorrect. Try again."
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to submit flag";
        setToast({ kind: "error", message });
      } finally {
        await loadContent(user.user_id);
      }
    },
    [user, loadContent]
  );

  const handleQuizSubmission = useCallback(
    async (quizId: string, answers: Record<string, string>) => {
      if (!user) return;
      setIsLoading(true);
      try {
        const result = await api.submitQuiz(quizId, user.user_id, answers);
        setToast({ kind: "success", message: `Quiz scored ${result.score}/${result.max_score}` });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to submit quiz";
        setToast({ kind: "error", message });
      } finally {
        await loadContent(user.user_id);
      }
    },
    [user, loadContent]
  );

  const handleExamSubmission = useCallback(
    async (examId: string, stageId: string, answer: string) => {
      if (!user) return;
      setIsLoading(true);
      try {
        const result = await api.submitExam(examId, user.user_id, stageId, answer);
        setToast({ kind: "success", message: `Exam stage stored (${result.score}/${result.max_score})` });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to submit exam stage";
        setToast({ kind: "error", message });
      } finally {
        await loadContent(user.user_id);
      }
    },
    [user, loadContent]
  );

  const handleSignOut = useCallback(() => {
    setUser(null);
    setLabs([]);
    setQuizzes([]);
    setExams([]);
    setSummary(null);
    setNote(null);
    setToast({ kind: "info", message: "Signed out" });
  }, []);

  const [isSyncing, setIsSyncing] = useState(false);
  const handleSync = useCallback(async () => {
    if (!user) return;
    setIsSyncing(true);
    try {
      const result = await api.syncContent(user.role);
      setToast({
        kind: "success",
        message: `Synced content: labs=${result.labs}, quizzes=${result.quizzes}, exams=${result.exams}`
      });
    } catch (err) {
      if (err instanceof HttpError && err.status === 403) {
        setToast({ kind: "error", message: "Forbidden: only staff/admin can sync content" });
      } else {
        const message = err instanceof Error ? err.message : "Sync failed";
        setToast({ kind: "error", message });
      }
    } finally {
      await loadContent(user.user_id);
      setIsSyncing(false);
    }
  }, [user, loadContent]);

  return (
    <div className="app-shell">
      <header className="hero">
        <span className="hero__badge">Cybersecurity learning cockpit</span>
        <h1>Cyber Grader</h1>
        <p>
          Track cybersecurity mastery across labs, quizzes, and capstone exams. 
        </p>
        <p style={{ marginTop: "1.25rem", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
          Connected to <strong>{API_BASE}</strong>
        </p>
      </header>

      <main className="content">
        {toast && (
          <div
            className={`toast ${
              toast.kind === "success" ? "toast--success" : toast.kind === "error" ? "toast--error" : ""
            }`}
          >
            {toast.message}
          </div>
        )}

        {!user && <LoginForm onSubmit={handleLogin} isSubmitting={isLoading} />}

        {user && (
          <>
            <nav className="subnav" aria-label="User navigation">
              <div className="subnav__info">
                <span className="badge">{user.role}</span>
                <h2 style={{ margin: "0.25rem 0 0" }}>{welcomeMessage}</h2>
                <p style={{ margin: 0, color: "var(--text-secondary)" }}>
                  Explore the content areas below and submit progress updates in real time.
                </p>
              </div>
              <div className="subnav__actions">
                {(user.role === "staff" || user.role === "admin") && (
                  <button type="button" className="primary-button" onClick={handleSync} disabled={isSyncing}>
                    {isSyncing ? "Syncing..." : "Sync content"}
                  </button>
                )}
                <button type="button" className="secondary-button" onClick={() => loadContent(user.user_id)}>
                  {isLoading ? "Refreshing..." : "Refresh data"}
                </button>
                <button type="button" className="secondary-button" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            </nav>

            <div className="content__grid">
              <QuizzesSection quizzes={quizzes} onSubmitQuiz={handleQuizSubmission} isSubmitting={isLoading} />
              <LabsSection labs={labs} onSubmitFlag={handleFlagSubmission} isSubmitting={isLoading} />
              <ExamsSection exams={exams} onSubmitExam={handleExamSubmission} isSubmitting={isLoading} />
              <DashboardSection summary={summary} />
              <NotesSection note={note} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
