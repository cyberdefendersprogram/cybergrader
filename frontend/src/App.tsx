import { useCallback, useEffect, useMemo, useState } from "react";
import { api, API_BASE, HttpError, setAuthToken } from "./api";
import { ExamsSection } from "./components/ExamsSection";
import { DashboardSection } from "./components/DashboardSection";
import { LabsSection } from "./components/LabsSection";
import { LoginForm } from "./components/LoginForm";
import { SignupForm } from "./components/SignupForm";
import { ForgotPasswordForm } from "./components/ForgotPasswordForm";
import { ResetPasswordForm } from "./components/ResetPasswordForm";
import { Onboarding } from "./components/Onboarding";
import { NotesSection } from "./components/NotesSection";
import { NotesList } from "./components/NotesList";
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
  const [view, setView] = useState<
    | "home" | "login" | "signup" | "forgot" | "reset"
    | "dashboard" | "labs" | "quizzes" | "exams" | "activity" | "notes" | "note"
  >("home");
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [noteName, setNoteName] = useState<string | null>(null);
  const [labs, setLabs] = useState<LabStatus[]>([]);
  const [quizzes, setQuizzes] = useState<QuizDefinition[]>([]);
  const [exams, setExams] = useState<ExamDefinition[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [note, setNote] = useState<NoteDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [meInfo, setMeInfo] = useState<{ email: string; role: string; student_id: string | null } | null>(null);

  const welcomeMessage = useMemo(() => {
    if (!user) return "";
    return meInfo?.email ? `Welcome back, ${meInfo.email}` : `Welcome back`;
  }, [user, meInfo]);

  useEffect(() => {
    // Simple path-based view selection
    const syncView = () => {
      const path = window.location.pathname;
      if (path.startsWith("/reset-password")) {
        const params = new URLSearchParams(window.location.search);
        setResetToken(params.get("token"));
        setView("reset");
      } else if (path === "/" && user) {
        setView("dashboard");
      } else if (path === "/dashboard") {
        setView("dashboard");
      } else if (path === "/labs") {
        setView("labs");
      } else if (path === "/quizzes") {
        setView("quizzes");
      } else if (path === "/exams") {
        setView("exams");
      } else if (path === "/activity") {
        setView("activity");
      } else if (path === "/notes") {
        setView("notes");
      } else if (path.startsWith("/notes/")) {
        const n = path.split("/")[2] || null;
        setNoteName(n);
        setView("note");
      } else if (path.startsWith("/signup")) {
        setView("signup");
      } else if (path.startsWith("/forgot-password")) {
        setView("forgot");
      } else if (path.startsWith("/login")) {
        setView("login");
      } else {
        setView(user ? "dashboard" : "home");
      }
    };
    syncView();
    const onPop = () => syncView();
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = (path: string) => {
    window.history.pushState({}, "", path);
    const event = new PopStateEvent("popstate");
    window.dispatchEvent(event);
  };

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  // Fetch individual note when viewing note detail
  useEffect(() => {
    if (view === "note" && noteName) {
      api
        .getNote(noteName)
        .then((doc) => setNote(doc))
        .catch(() => setNote(null));
    }
  }, [view, noteName]);

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
      setAuthToken(payload.token);
      localStorage.setItem("cg_token", payload.token);
      setToast({ kind: "success", message: `Signed in as ${credentials.email}` });
      const me = await api.me().catch(() => null);
      if (me) setMeInfo(me);
      await loadContent(payload.user_id);
      navigate("/");
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

  const handleSignup = useCallback(async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      const payload = await api.signup(credentials);
      setUser(payload);
      setAuthToken(payload.token);
      localStorage.setItem("cg_token", payload.token);
      setToast({ kind: "success", message: `Welcome, ${credentials.email}!` });
      const me = await api.me().catch(() => null);
      if (me) setMeInfo(me);
      await loadContent(payload.user_id);
      navigate("/");
    } finally {
      setIsLoading(false);
    }
  }, [loadContent]);

  useEffect(() => {
    const token = localStorage.getItem("cg_token");
    if (token) {
      setAuthToken(token);
      api.me().then(setMeInfo).catch(() => undefined);
    }
  }, []);

  const handleSignOut = useCallback(() => {
    setUser(null);
    setAuthToken(null);
    localStorage.removeItem("cg_token");
    setLabs([]);
    setQuizzes([]);
    setExams([]);
    setSummary(null);
    setNote(null);
    setToast({ kind: "info", message: "Signed out" });
    navigate("/login");
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

        {!user && (
          <>
            {view === "home" && (
              <Onboarding onSignup={() => navigate("/signup")} onLogin={() => navigate("/login")} />
            )}
            {view === "login" && (
              <LoginForm
                onSubmit={handleLogin}
                isSubmitting={isLoading}
                onForgotPassword={(email) => {
                  navigate(`/forgot-password${email ? `?email=${encodeURIComponent(email)}` : ""}`);
                }}
                onSignupNavigate={() => navigate("/signup")}
              />
            )}
            {view === "signup" && (
              <SignupForm onSubmit={handleSignup} isSubmitting={isLoading} onLoginNavigate={() => navigate("/login")} />
            )}
            {view === "forgot" && (
              <ForgotPasswordForm
                isSubmitting={isLoading}
                onBack={() => navigate("/login")}
                onRequest={async (email) => {
                  setIsLoading(true);
                  try {
                    await api.requestPasswordReset(email);
                    setToast({ kind: "success", message: "If registered, we emailed you a reset link" });
                  } finally {
                    setIsLoading(false);
                  }
                }}
              />
            )}
            {view === "reset" && resetToken && (
              <ResetPasswordForm
                token={resetToken}
                isSubmitting={isLoading}
                onReset={async (token, newPassword) => {
                  setIsLoading(true);
                  try {
                    await api.resetPassword(token, newPassword);
                    setToast({ kind: "success", message: "Password updated. Please sign in." });
                    navigate("/login");
                  } finally {
                    setIsLoading(false);
                  }
                }}
              />
            )}
          </>
        )}

        {user && (
          <>
            <nav className="subnav" aria-label="User navigation">
              <div className="subnav__info">
                <span className="badge">{meInfo?.role ?? user.role}</span>
                <h2 style={{ margin: "0.25rem 0 0" }}>{welcomeMessage}</h2>
                <p style={{ margin: 0, color: "var(--text-secondary)" }}>
                  Explore the content areas below and submit progress updates in real time.
                </p>
              </div>
              <div className="subnav__actions">
                <button type="button" className="secondary-button" onClick={() => navigate("/dashboard")}>
                  Dashboard
                </button>
                <button type="button" className="secondary-button" onClick={() => navigate("/labs")}>Labs</button>
                <button type="button" className="secondary-button" onClick={() => navigate("/quizzes")}>Quizzes</button>
                <button type="button" className="secondary-button" onClick={() => navigate("/exams")}>Exams</button>
                <button type="button" className="secondary-button" onClick={() => navigate("/activity")}>Activity</button>
                <button type="button" className="secondary-button" onClick={() => navigate("/notes")}>Notes</button>
                {(user.role === "staff" || user.role === "admin") && (
                  <>
                    <button type="button" className="primary-button" onClick={handleSync} disabled={isSyncing}>
                      {isSyncing ? "Syncing..." : "Sync content"}
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={async () => {
                        setIsLoading(true);
                        try {
                          const data = await api.exportScores();
                          const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `scores-export-${Date.now()}.json`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                          setToast({ kind: "success", message: "Export ready (JSON downloaded)" });
                        } catch (err) {
                          const message = err instanceof Error ? err.message : "Export failed";
                          setToast({ kind: "error", message });
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                    >
                      Export scores
                    </button>
                  </>
                )}
                <button type="button" className="secondary-button" onClick={() => loadContent(user.user_id)}>
                  {isLoading ? "Refreshing..." : "Refresh data"}
                </button>
                <button type="button" className="secondary-button" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            </nav>

            {/* Student ID prompt (one friendly nudge) */}
            {meInfo && meInfo.role === "student" && !meInfo.student_id && (
              <div className="card login-card" style={{ marginBottom: "1rem" }}>
                <h3 style={{ marginTop: 0 }}>Add your Student ID</h3>
                <p style={{ margin: 0, color: "var(--text-secondary)" }}>
                  Just once and you're golden. Promise.
                </p>
                <form
                  className="login-form"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const input = (e.currentTarget.elements.namedItem("student_id") as HTMLInputElement) || null;
                    if (!input) return;
                    const value = input.value.trim();
                    if (!value) return;
                    setIsLoading(true);
                    try {
                      await api.setStudentId(value);
                      const me = await api.me().catch(() => null);
                      if (me) setMeInfo(me);
                      setToast({ kind: "success", message: "Student ID saved" });
                    } catch (err) {
                      const message = err instanceof Error ? err.message : "Could not save Student ID";
                      setToast({ kind: "error", message });
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                >
                  <label>
                    Student ID
                    <input name="student_id" placeholder="e.g., A12345678" />
                  </label>
                  <button type="submit" disabled={isLoading}>{isLoading ? "Saving..." : "Save"}</button>
                </form>
              </div>
            )}

            {view === "dashboard" && <DashboardSection summary={summary} />}
            {view === "labs" && (
              <LabsSection labs={labs} onSubmitFlag={handleFlagSubmission} isSubmitting={isLoading} />
            )}
            {view === "quizzes" && (
              <QuizzesSection quizzes={quizzes} onSubmitQuiz={handleQuizSubmission} isSubmitting={isLoading} />
            )}
            {view === "exams" && (
              <ExamsSection exams={exams} onSubmitExam={handleExamSubmission} isSubmitting={isLoading} />
            )}
            {view === "activity" && <DashboardSection summary={summary} />}
            {view === "notes" && <NotesList navigate={navigate} />}
            {view === "note" && note && <NotesSection note={note} />}
          </>
        )}
      </main>
    </div>
  );
}
