export type Role = "student" | "staff" | "admin";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user_id: string;
  role: Role;
  token: string;
}

export interface LabFlagPrompt {
  name: string;
  prompt: string;
  validator: "exact" | "regex" | "file_exists";
  pattern?: string | null;
}

export interface LabStatus {
  id: string;
  title: string;
  version: string;
  instructions: string;
  score: number;
  total_flags: number;
  flags: LabFlagPrompt[];
}

export interface QuizChoice {
  key: string;
  label: string;
}

export interface QuizQuestion {
  id: string;
  prompt: string;
  type: "multiple_choice" | "short_answer";
  choices: QuizChoice[];
  answer: string;
  points: number;
}

export interface QuizDefinition {
  id: string;
  title: string;
  version: string;
  questions: QuizQuestion[];
}

export interface QuizSubmissionResult {
  user_id: string;
  quiz_id: string;
  score: number;
  max_score: number;
  submitted_at: string;
}

export interface ExamStageDefinition {
  id: string;
  title: string;
  description: string;
  max_score: number;
}

export interface ExamDefinition {
  id: string;
  title: string;
  version: string;
  stages: ExamStageDefinition[];
}

export interface ExamSubmissionResult {
  user_id: string;
  exam_id: string;
  stage_id: string;
  score: number;
  max_score: number;
  submitted_at: string;
}

export interface DashboardSummary {
  labs: LabStatus[];
  quizzes: QuizSubmissionResult[];
  exams: ExamSubmissionResult[];
}

export interface NoteDocument {
  name: string;
  body: string;
}

export interface FlagSubmissionResult {
  correct: boolean;
  user_id: string;
  lab_id: string;
  flag_name: string;
  submitted_at: string;
}
