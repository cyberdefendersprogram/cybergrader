# Cyber Grader — Product & Technical Spec

## 🔹 Core Overview
A containerized **FastAPI + React** application backed by **Postgres** for persistence.  
All course content (labs, quizzes, exams) lives in the repository's local **content/** directory and can be reloaded by staff/admin.  
The platform enables students to log in, complete activities, and track progress — with data synced to **Google Sheets / Google Cloud** for reporting.

---

## 1. Architecture
- Frontend: React SPA (students + staff UI)
- Backend: FastAPI API (REST)
- Database: Postgres (Dockerized locally or DigitalOcean Managed Database)
- Containerized: Docker images; Compose for local, DO App Platform for cloud
- Integrations: Google Sheets (optional), ForwardEmail (password reset)

---

## 2. Authentication & Roles (Concepts)
- Primary: email (username) + password authentication (bcrypt).  
  - POST `/auth/signup` creates a user (default role `student`) and stores a bcrypt `password_hash`.
  - POST `/auth/login` verifies credentials and issues a 24h JWT session (HS256, `SECRET_KEY`).
  - No email verification for signup in this version.
- Password reset via email (ForwardEmail API).  
  - POST `/auth/request-password-reset` generates a short‑lived token and emails a reset link.  
  - POST `/auth/reset-password` accepts `{ token, new_password }`, validates, and updates the password.
  - Env: `FORWARDEMAIL_API_TOKEN`, `EMAIL_FROM`, `RESET_LINK_BASE`, `SECRET_KEY`.
- Roles:  
  - `student`: take labs, quizzes, exams, view progress.  
  - `staff`: sync content, view grades.  
  - `admin`: manage system, exports, configs.  
- New signups default to `student`. After first login, students without a `student_id` are prompted to set one.
- Minimal data model:  
  - `users(id, email, role, student_id, password_hash, created_at, updated_at)`  
  - `password_reset_tokens(id, user_id, token, expires_at, used_at, created_at)`

---

## 3. Course Content Management (Concepts)
- Content loaded from the local repository `content/` folder (YAML + Markdown).  
- Staff/admin can trigger `/admin/sync` from the UI to reload and persist content into Postgres.  
- Tracks a daily version string for quick auditing.

---

## 4. Labs (Concepts)
- Markdown-based instructions parsed and rendered.  
- Flags defined via YAML with validator rules (`exact`, `regex`, `file_exists`).  
- Students submit flags → backend validates → score computed.  
- Multiple attempts allowed, highest score stored.  
- Staff dashboard for reviewing progress.  
- Audit trail for submissions and scoring.

---

## 5. Quizzes & Tests (Concepts)
- YAML-based question sets (multiple choice, short answer, etc.).  
- Auto-grading with per-question scoring.  
- Versioned quiz content linked to GitHub commit.  
- Student quiz history stored in Postgres.

---

## 6. Final Exam (Concepts)
- Multi-stage exam (e.g., Part 1–3).  
- Each stage unlocks sequentially after previous completion.  
- Combination of objective (auto-graded) and subjective (manual review) items.  
- Time limits and attempt restrictions configurable.  
- Results aggregated for final grade computation.

---

## 7. Integrations (Summary)
- **Google Sheets Sync (optional):**  
  - Exports `lab_submissions`, `quiz_submissions`, and `exam_results`.  
  - Uses service-account credentials via Sheets API.  
  - Triggered by admin endpoint `/admin/export-scores`.  
  - Optionally run as scheduled background task or manual export.  

---

<!-- Student/Instructor dashboard UI is organized under Section 9 (Frontend) -->

## 8. Deployment & Operations
- **Local stack:** `scripts/deploy-local.sh` builds the Docker image, boots the API and Postgres via Docker Compose, and aggregates logs into `logs/local-deploy.log`. If `.env.local` exists it is auto-loaded (see env pattern below).
- **DigitalOcean App Platform:** `scripts/deploy-digitalocean.sh` generates an App Platform spec and injects `DATABASE_URL` from a DigitalOcean Managed Database connection string. If `.env.do` exists it is auto-loaded. Follows build/deploy/runtime logs by default.
- **Other targets:** Existing scripts ship images to Amazon ECR or Hetzner with minimal prerequisites.

### Env file pattern
- Real env files (`.env.local`, `.env.do`) are not checked in. Examples exist: `.env.example.local`, `.env.example.do`.
- Copy an example to the real filename and edit. Scripts auto-source them:
  - Local: `scripts/deploy-local.sh` loads `.env.local` if present and passes it to Compose.
  - DigitalOcean: `scripts/deploy-digitalocean.sh` loads `.env.do` if present (override with `ENV_FILE_CANDIDATE=/path/file`).
## 9. Frontend

#### Summary
- Onboarding at `/` for unauthenticated users with friendly intro and clear CTAs to sign up or log in.
- Signed‑in header shows the user’s email (never internal IDs). Minimal, consistent top navigation.
- Dashboard is summary‑only with quick CTAs; prompt students to set `student_id` once.
- Labs, Quizzes, and Exams each have list pages and focused detail pages. Notes have an index and dedicated pages (last in nav). Activity shows a learner’s own history.
- One screen per action, simple forms, helpful toasts; small touches of charm without being distracting.

#### UI Principles
- One screen per logical action.
- Clear, student‑friendly language; small, encouraging microcopy.
- Accessible and legible: good contrast, visible focus, large click targets; responsive layout.
- Predictable, deep‑linkable routes for every entity (labs/quizzes/exams/notes).

#### Routes & Pages
- Unauthenticated
  - `/` — Onboarding card (intro + CTAs to “/signup” or “/login”).
  - `/signup` — Email + password signup.
  - `/login` — Email + password login.
  - `/forgot-password` — Request reset link via email.
  - `/reset-password?token=…` — Set new password.
- Authenticated
  - `/` — Redirect to `/dashboard`.
  - `/dashboard` — Summary cards (Labs/Quizzes/Exams) + CTAs; `student_id` prompt if missing.
  - `/labs` — List with status; link to `/labs/:labId`.
  - `/labs/:labId` — Instructions + flag submission form.
  - `/quizzes` — List with progress; link to `/quizzes/:quizId`.
  - `/quizzes/:quizId` — Quiz details and attempt submission.
  - `/exams` — List with progress; link to `/exams/:examId`.
  - `/exams/:examId` — Exam page (single‑page staged submission is fine).
  - `/activity` — Personal history: lab submissions, quiz attempts, exam submissions.
  - `/notes` — Notes index (derived from content/notes).
  - `/notes/:noteName` — Dedicated note page.

#### Navigation
- Top nav: Dashboard, Labs, Quizzes, Exams, Activity, Notes (Notes last).
- Staff/admin also see actions: “Sync content” and “Export scores”.
- “Export scores” triggers a download/export via `/admin/export-scores` (CSV/Sheets per env).
- Detail pages include a simple “Back to …” link.
- Header shows the signed‑in email and compact user actions (Refresh, Sync/Export for staff/admin, Sign out).

#### Student Dashboard
- Progress cards for Labs/Quizzes/Exams: available/in‑progress/completed counts; compact progress bars.
- Primary CTAs route to list pages (no submissions on the dashboard).
- Student ID prompt appears as a friendly inline card until saved.
- Student ID must be unique across all users; enforce at the database and surface a clear error if already in use.

#### Instructor Dashboard (staff/admin)
- Actions: Sync content (calls `/admin/sync`) and Export scores (calls `/admin/export-scores`).
- Gradebook view (filter by lab/quiz/exam) to review student progress.
- Submission detail and regrade tools (future iterations).
- Audit log viewer for actions, syncs, and scores (future iterations).
#### Lists & Details
- Lists: simple cards with title, short metadata (version), progress/status, and Start/Continue CTA.
- Details: focused forms and instructions; success/error toasts with encouraging copy.

#### Activity (Logs)
- Timeline or table view of a student’s own lab submissions, quiz attempts, and exam submissions.
- Emphasize progress; no admin‑only data appears here.

#### Notes
- Notes index appears last in nav; each note has its own page.
- Backend provides `GET /notes` to enumerate available notes (derived from `content/notes`).

#### Auth Flows
- Email+password signup/login with JWT sessions (24h). Password reset emails via ForwardEmail.
- After signup/login, if role=student and `student_id` is missing, show a one‑time prompt to set it.
- Student ID is globally unique; conflicts are handled with a clear, student‑friendly error message.

#### Copy & Empty States
- Success: “Nice work — flag accepted!”, “Password updated. You’re set.”
- Errors are short and actionable: “Hmm, that didn’t work — try again.”
- Empty states explain what’s next and how to begin.

#### Accessibility & Performance
- Meet WCAG AA contrast; visible focus states; labeled inputs.
- Route-based data loading; non-blocking UI with concise toasts/status.

---

## 10. Backend API (Routes)

### Auth
- `POST /auth/signup` — Create user (role=student), store password hash, return JWT.
- `POST /auth/login` — Verify credentials, return JWT.
- `GET /auth/me` — Return { email, role, student_id } for the current token.
- `POST /auth/request-password-reset` — Generate reset token and send email (always 200).
- `POST /auth/reset-password` — Consume token and set new password.
- `POST /profile/student-id` — Set/update student_id (JWT required; unique constraint enforced).

### Content & Progress
- `GET /labs?user_id=…` — Lab status (flags prompts + completion per user).
- `POST /labs/{lab_id}/flags/{flag_name}` — Submit a flag.
- `GET /quizzes` — List quizzes.
- `POST /quizzes/{quiz_id}/submit` — Submit quiz answers.
- `GET /exams` — List exams.
- `POST /exams/{exam_id}/submit` — Submit exam stage.
- `GET /dashboard/{user_id}` — Aggregated history for Activity.

### Notes
- `GET /notes` — List available notes (derived from `content/notes`).
- `GET /notes/{note_name}` — Get note markdown content.

### Admin
- `POST /admin/sync` — Staff/admin only (header `X-User-Role: staff|admin`). Reload content from `content/` and persist.
- `GET /admin/export-scores` — Export lab/quiz/exam results and (optionally) sync to Google Sheets.

### Misc
- `GET /health` — Healthcheck.

Auth headers: new endpoints require `Authorization: Bearer <jwt>`. Admin sync also expects `X-User-Role` for demo auth.

---

## 11. Data Model (Database)

Schema: configurable via `DATABASE_SCHEMA` (default `public`). Tables are auto‑created by the service on startup.

### Tables
- `users` — id, email (unique), password_hash (bcrypt_sha256), role, student_id (unique when not null), created_at, updated_at
- `password_reset_tokens` — id, user_id (FK), token (unique), expires_at, used_at, created_at
- `labs` — id, title, version, instructions_path, flags (jsonb)
- `quizzes` — id, title, version, questions (jsonb)
- `exams` — id, title, version, stages (jsonb)
- `lab_submissions` — id, user_id, lab_id, flag_name, correct, submitted_at
- `quiz_submissions` — id, user_id, quiz_id, score, max_score, submitted_at
- `exam_submissions` — id, user_id, exam_id, stage_id, score, max_score, submitted_at

Indexes:
- Unique on `users.email`
- Partial unique on `users.student_id` where `student_id is not null`
- Primary keys on all tables as listed

---

## 12. Integrations (Details)

### Google Sheets
- Exports lab/quiz/exam submissions, optionally updates a Google Sheet.
- Env: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEETS_SPREADSHEET_ID`.
- Endpoint: `GET /admin/export-scores` (returns data even if sync is skipped).

### ForwardEmail (Email API)
- Sends password reset emails via ForwardEmail HTTP API.
- Env: `FORWARDEMAIL_API_TOKEN`, `EMAIL_FROM`, `RESET_LINK_BASE`.

### Content Source
- Local `content/` directory in the repository (default for local and DO deployments).
- Staff/admin reload with `POST /admin/sync`.

---

## 13. Observability & Logging

### Logging Philosophy
- Be explicit, not noisy. Log what’s important for operability and debugging:
  - Database backend selection (memory, postgres).
  - Content sync source/status and counts (labs/quizzes/exams).
  - Postgres store hydration counts and per‑table upsert counts.
  - Auth events at info level (signup/login/reset requested/reset completed) without sensitive data.
- Never log secrets (passwords, tokens, API keys). Scrub sensitive values if needed.
- Emit via Uvicorn’s logger (`uvicorn.error`) so messages appear in container/platform logs.

### Where to find logs
- Local: aggregated in `logs/local-deploy.log` by `scripts/deploy-local.sh` (color stripped; Ctrl+C to stop).
- DigitalOcean: `doctl apps logs <APP_ID> --type build --type deploy --type run --follow`.

---

## 14. Deployment & Env Files (Reference)

### Local
- `scripts/deploy-local.sh` — builds image, starts API + Postgres with Docker Compose, streams logs.
- Auto‑loads `.env.local` if present and passes it to Compose.

### DigitalOcean App Platform
- `scripts/deploy-digitalocean.sh` — generates a spec and deploys using DO Managed DB.
- Auto‑loads `.env.do` if present; updates existing app by name; can follow logs.

### Env file pattern
- Real env files (`.env.local`, `.env.do`) are ignored by git. Examples: `.env.example.local`, `.env.example.do`.
- Copy an example to the real filename and edit; scripts auto‑source them.
