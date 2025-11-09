# Cyber Grader Platform — Feature Summary (Concise)

## 🔹 Core Overview
A containerized **FastAPI + React** application backed by **Supabase** for database, auth, and storage.  
All course content (labs, quizzes, exams) lives in **separate GitHub repositories** and syncs automatically.  
The platform enables students to log in, complete activities, and track progress — with data synced to **Google Sheets / Google Cloud** for reporting.

---

## 🚀 Key Features

### 1. **Architecture**
- **Frontend:** React SPA (students + staff UI).  
- **Backend:** FastAPI API (REST + background jobs).  
- **Database:** Supabase (Postgres, Auth, RLS, Storage).  
- **Containerized:** Docker-based deploys for portability.  
- **Integrations:** GitHub (content), Google Cloud (storage + Sheets).

---

### 2. **Authentication & Roles**
- Supabase email/password authentication.  
- Roles:  
  - `student`: take labs, quizzes, exams, view progress.  
  - `staff`: sync content, view grades.  
  - `admin`: manage system, exports, configs.  
- Role-based access enforced via RLS.

---

### 3. **Course Content Management**
- Content pulled from separate GitHub repos:  
  - `cis53-lab` — lab markdown + flag YAML.  
  - `cis53-quiz` — YAML quizzes.  
  - `cis53-exam` — staged final exam definitions.  
- Admin or cron-based **sync process**:
  - Fetch from repo → validate → upsert into Supabase.  
  - Tracks `version`, `source_ref` (commit SHA).  

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
- Student quiz history stored in Supabase.

---

### 6. **Final Exam (Staged Support)**
- Multi-stage exam (e.g., Part 1–3).  
- Each stage unlocks sequentially after previous completion.  
- Combination of objective (auto-graded) and subjective (manual review) items.  
- Time limits and attempt restrictions configurable.  
- Results aggregated for final grade computation.

---

### 7. **Google Cloud & Sheets Integration**
- **Google Cloud Storage:** optional backup of submissions and logs.  
- **Google Sheets Sync:**  
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
- **Local stack:** `scripts/deploy-local.sh` builds the Docker image, boots the API and Postgres via Docker Compose, and aggregates every container log into `logs/local-deploy.log` for easy troubleshooting.
- **DigitalOcean App Platform:** `scripts/deploy-digitalocean.sh` generates an App Platform spec that reuses the repo Dockerfile and injects a `DATABASE_URL` sourced from a DigitalOcean Managed Database connection string. The app auto-redeploys on each Git pull while keeping database state in the managed service.
- **Other targets:** Existing scripts ship images to Amazon ECR or Hetzner with minimal prerequisites.
