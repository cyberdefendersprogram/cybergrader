import type {
  DashboardSummary,
  ExamDefinition,
  ExamSubmissionResult,
  FlagSubmissionResult,
  LabStatus,
  LoginRequest,
  LoginResponse,
  NoteDocument,
  QuizDefinition,
  QuizSubmissionResult
} from "./types";

const deriveApiBase = (): string => {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined;

  // 1) Explicit global override wins (e.g., for tests)
  if (typeof window !== "undefined") {
    const globalOverride = (window as typeof window & { __API_BASE__?: string }).__API_BASE__;
    if (globalOverride) return globalOverride;
  }

  // 2) Vite env var next
  if (envBase) return envBase;

  // 3) Default: backend runs at localhost:8000
  return "http://localhost:8000";
};

export const API_BASE = deriveApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    },
    ...init
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request to ${path} failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  login: (payload: LoginRequest) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listLabs: (userId: string) => request<LabStatus[]>(`/labs?user_id=${encodeURIComponent(userId)}`),
  submitFlag: (labId: string, flagName: string, userId: string, submission: string) =>
    request<FlagSubmissionResult>(
      "/labs/" + encodeURIComponent(labId) + "/flags/" + encodeURIComponent(flagName),
      {
        method: "POST",
        body: JSON.stringify({ user_id: userId, submission })
      }
    ),
  listQuizzes: () => request<QuizDefinition[]>("/quizzes"),
  submitQuiz: (quizId: string, userId: string, answers: Record<string, string>) =>
    request<QuizSubmissionResult>(`/quizzes/${encodeURIComponent(quizId)}/submit`, {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        answers: Object.entries(answers).map(([question_id, answer]) => ({
          question_id,
          answer
        }))
      })
    }),
  listExams: () => request<ExamDefinition[]>("/exams"),
  submitExam: (examId: string, userId: string, stageId: string, answer: string) =>
    request<ExamSubmissionResult>(`/exams/${encodeURIComponent(examId)}/submit`, {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        stage_id: stageId,
        answers: { response: answer }
      })
    }),
  dashboard: (userId: string) => request<DashboardSummary>(`/dashboard/${encodeURIComponent(userId)}`),
  getNote: (note: string) => request<NoteDocument>(`/notes/${encodeURIComponent(note)}`)
};
