import type {
  DashboardSummary,
  ExamDefinition,
  ExamSubmissionResult,
  FlagSubmissionResult,
  LabStatus,
  LoginRequest,
  LoginResponse,
  NoteDocument,
  NoteIndex,
  QuizDefinition,
  QuizSubmissionResult,
  SyncResponse
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

let AUTH_TOKEN: string | null = null;
export function setAuthToken(token: string | null) {
  AUTH_TOKEN = token;
}

export class HttpError extends Error {
  status: number;
  body?: string;
  constructor(status: number, message: string, body?: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {}),
      ...(init?.headers || {})
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text();
    const message = text || `Request to ${path} failed with ${response.status}`;
    throw new HttpError(response.status, message, text);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  signup: (payload: { email: string; password: string }) =>
    request<LoginResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  login: (payload: LoginRequest) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  me: () => request<{ email: string; role: string; student_id: string | null }>("/auth/me"),
  setStudentId: (student_id: string) =>
    request<{ ok: true }>("/profile/student-id", {
      method: "POST",
      body: JSON.stringify({ student_id })
    }),
  requestPasswordReset: (email: string) =>
    request<{ ok: true }>("/auth/request-password-reset", {
      method: "POST",
      body: JSON.stringify({ email })
    }),
  resetPassword: (token: string, new_password: string) =>
    request<{ ok: true }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password })
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
  getNote: (note: string) => request<NoteDocument>(`/notes/${encodeURIComponent(note)}`),
  listNotes: () => request<NoteIndex>("/notes"),
  exportScores: () => request<any>("/admin/export-scores"),
  syncContent: (role: string) =>
    request<SyncResponse>(`/admin/sync`, {
      method: "POST",
      headers: { "X-User-Role": role }
    })
};
