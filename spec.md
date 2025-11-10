# Cyber Grader Platform — Feature Summary (Concise)

## 🔹 Core Overview
A containerized **FastAPI + React** application backed by **Postgres** for persistence.  
All course content (labs, quizzes, exams) lives in the repository's local **content/** directory and can be reloaded by staff/admin.  
The platform enables students to log in, complete activities, and track progress — with data synced to **Google Sheets / Google Cloud** for reporting.

---

## 🚀 Key Features

### 1. **Architecture**
- **Frontend:** React SPA (students + staff UI).  
- **Backend:** FastAPI API (REST).  
- **Database:** Postgres (Dockerized locally or DigitalOcean Managed Database).  
- **Containerized:** Docker-based deploys for portability.  
- **Integrations:** Google Sheets export (optional).

---

### 2. **Authentication & Roles**
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

### 3. **Course Content Management**
- Content loaded from the local repository `content/` folder (YAML + Markdown).  
- Staff/admin can trigger `/admin/sync` from the UI to reload and persist content into Postgres.  
- Tracks a daily version string for quick auditing.

---

### 4. **Labs**
- Markdown-based instructions parsed and rendered.  
- Flags defined via YAML with validator rules (`exact`, `regex`, `file_exists`).  
- Students submit flags → backend validates → score computed.  
- Multiple attempts allowed, highest score stored.  
- Staff dashboard for reviewing progress.  
- Audit trail for submissions and scoring.

---

### 5. **Quizzes & Tests**
- YAML-based question sets (multiple choice, short answer, etc.).  
- Auto-grading with per-question scoring.  
- Versioned quiz content linked to GitHub commit.  
- Student quiz history stored in Postgres.

---

### 6. **Final Exam (Staged Support)**
- Multi-stage exam (e.g., Part 1–3).  
- Each stage unlocks sequentially after previous completion.  
- Combination of objective (auto-graded) and subjective (manual review) items.  
- Time limits and attempt restrictions configurable.  
- Results aggregated for final grade computation.

---

### 7. **Google Sheets Integration**
- **Google Sheets Sync (optional):**  
  - Exports `lab_submissions`, `quiz_submissions`, and `exam_results`.  
  - Uses service-account credentials via Sheets API.  
  - Triggered by admin endpoint `/admin/export-scores`.  
  - Optionally run as scheduled background task or manual export.  

---

### 8. **Student Dashboard**
- Shows all course components:
  - Labs (progress, scores)  
  - Quizzes (attempt history)  
  - Exams (stages and results)  
- Markdown viewer for lecture notes (from repo).  
- Embedded YouTube lecture links.  
- Personalized feedback (future AI-generated).

---

### 9. **Instructor Dashboard**
- Content sync controls and validation logs.
- Gradebook view (filter by lab/quiz/exam).
- Export to CSV / Google Sheets.
- Submission detail and regrade tools.
- Audit log viewer (actions, syncs, scores).

---

### 10. **Deployment & Operations**
- **Local stack:** `scripts/deploy-local.sh` builds the Docker image, boots the API and Postgres via Docker Compose, and aggregates logs into `logs/local-deploy.log`. If `.env.local` exists it is auto-loaded (see env pattern below).
- **DigitalOcean App Platform:** `scripts/deploy-digitalocean.sh` generates an App Platform spec and injects `DATABASE_URL` from a DigitalOcean Managed Database connection string. If `.env.do` exists it is auto-loaded. Follows build/deploy/runtime logs by default.
- **Other targets:** Existing scripts ship images to Amazon ECR or Hetzner with minimal prerequisites.

#### Env file pattern
- Real env files (`.env.local`, `.env.do`) are not checked in. Examples exist: `.env.example.local`, `.env.example.do`.
- Copy an example to the real filename and edit. Scripts auto-source them:
  - Local: `scripts/deploy-local.sh` loads `.env.local` if present and passes it to Compose.
  - DigitalOcean: `scripts/deploy-digitalocean.sh` loads `.env.do` if present (override with `ENV_FILE_CANDIDATE=/path/file`).
