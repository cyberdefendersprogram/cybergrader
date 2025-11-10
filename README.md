# Cyber Grader

This repository contains the reference implementation of the **Cyber Grader Platform** described in `spec.md`. It includes:

* A FastAPI backend (`backend/`) that loads course content from the bundled `content/` directory, persists to Postgres, and exposes REST endpoints for students, staff, and admins.
* A React + TypeScript single-page application (`frontend/`) built with Vite and served as static assets from the FastAPI backend.
* Sample course content in Markdown/YAML under `content/` to demonstrate labs, quizzes, exam stages, and lecture notes.

## Getting started

### Backend API (dev quick start)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API boots with content from the local `content/` directory and auto-creates the database schema. Authentication uses email + password with JWT. For password resets, configure the ForwardEmail API (see below).

### Frontend SPA (dev)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API requests to `http://localhost:8000` so the React application can interact with FastAPI during development. When you are ready to ship static assets, run `npm run build` and the compiled bundle in `frontend/dist/` will be automatically served by the backend (including a catch-all route for client-side navigation).

The UI follows a one-screen-per-action model with clear routes and a connection light in the header (green when `/health` is reachable):

- `/` — Onboarding for unauthenticated users
- `/signup`, `/login`, `/forgot-password`, `/reset-password?token=…`
- After login: `/dashboard`, `/labs(/:id)`, `/quizzes(/:id)`, `/exams(/:id)`, `/activity`, `/notes(/:name)`

The header shows the signed‑in email. Dashboard is summary‑only with CTAs; students are prompted to set a unique `student_id` once. Staff/admin see Sync Content and Export Scores actions.

### Content structure

Content lives alongside the code for the MVP:

```
content/
├── labs
│   ├── hello-lab.md
│   └── hello-lab.yml
├── quizzes
│   └── getting-started.yml
├── exams
│   └── final.yml
└── notes
    └── lecture-01.md
```

Adding new YAML/Markdown files and calling the `/admin/sync` endpoint will refresh the in-memory store and persist to Postgres.

The backend reads course material from the local `content/` directory in this repository. A staff/admin can trigger a reload by calling `/admin/sync` (the UI provides a "Sync content" button). The API logs how many items were loaded and persists them to Postgres.

Notes index and pages are served via `/notes` and `/notes/:name`.

### Integrations

#### Google Sheets sync

The `/admin/export-scores` endpoint exports all lab, quiz, and exam attempts and, when configured, pushes them to a Google Sheet.
The sync writes four tabs:

- `Scores` — One row per user with identity columns and per‑item scores:
  - Identity: `user_id`, `email` (when available), `student_id` (unique when set)
  - Labs: `lab:<id>` = count of correct flags in that lab
  - Quizzes: `quiz:<id> (max)` = best score observed for that quiz
  - Exams: `exam:<id> (max)` = best score observed for that exam
  
The UI offers two export paths:

- Sync to Google Sheets (when env is configured) — writes Scores + raw tabs.
- Direct CSV download of the Scores pivot at `/admin/export-scores.csv` (triggered by the Export button in the UI).
- `Labs` — Raw lab flag submissions.
- `Quizzes` — Raw quiz attempts.
- `Exams` — Raw exam submissions.

Provide the following environment variables before starting the API to enable synchronization:

| Variable | Description |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Either the JSON string for a Google service account or a path to the credential file. |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | The ID of the target spreadsheet that contains `Labs`, `Quizzes`, `Exams`, and `Meta` tabs. |

When the credentials or spreadsheet are not configured, the export still returns the data but reports that syncing was skipped.

#### Postgres persistence

Set `DATABASE_URL` to a Postgres connection string (Aurora, Amazon RDS, or a Hetzner-hosted container) and the API will persist
content and submissions via the bundled Postgres store. Use `DATABASE_SCHEMA` to scope writes to a dedicated schema (defaults to
`public`). The store automatically creates the required tables and hydrates the in-memory cache on startup so you can scale the
API horizontally. Declare `DATABASE_BACKUP_SCHEDULE`—`nightly` by default—to document the cadence of your logical or snapshot
backups.

| Table | Purpose |
| --- | --- |
| `labs` | Lab metadata and flag definitions (`jsonb`) |
| `quizzes` | Quiz metadata and question definitions (`jsonb`) |
| `exams` | Exam metadata and stage definitions (`jsonb`) |
| `lab_submissions` | Each submitted lab flag with timestamps |
| `quiz_submissions` | Quiz attempt scores |
| `exam_submissions` | Exam stage submissions |

Nightly backups are recommended (e.g., `pg_dump` or managed snapshots). The backup schedule variable does not execute the backup itself—it documents your cadence.

> Experimental: Alternative backends like Supabase are not part of the primary deployment path and may be removed or changed.

### Versioning

The app version is stored in the root `VERSION` file and is exposed by FastAPI (`app.version`) and `/health`.

- Format: `MAJOR.MINOR.PATCH`
- Current policy: start at `0.0.N`. Increment `N` on every check‑in. Backward‑incompatible changes are allowed until the version explicitly moves to `0.1.N`.
- Update the `VERSION` file with each change that alters behavior.

### Deployment (supported targets)

Use the provided scripts to run locally or deploy to DigitalOcean App Platform. Other targets are experimental.

- `scripts/deploy-local.sh` – spins up the local Docker Compose stack (API + Postgres) and streams every container log into `logs/local-deploy.log`. Press <kbd>Ctrl</kbd>+<kbd>C</kbd> to tear down the stack when you are done testing.
- `scripts/deploy-digitalocean.sh` – deploys to DigitalOcean App Platform using a generated spec (no repository YAMLs needed) and connects the app to a **DigitalOcean Managed Database** via `DO_DB_CONNECTION_STRING`. Optionally follows build/deploy/runtime logs similar to the local script.
- (Experimental) `scripts/build-and-push-ecr.sh` – AWS ECR helper.
- (Experimental) `scripts/deploy-hetzner.sh` – Hetzner VM helper.

### Environment files

- Local dev: copy `.env.example.local` to `.env.local` and edit as needed. The local deploy script auto-loads `.env.local` if present.
- DigitalOcean: copy `.env.example.do` to `.env.do` and fill in your app name, region, GitHub repo (`owner/name`), branch, and managed database connection string. The DO deploy script loads `.env.do` automatically or derives the repo from your local git remote.

### Docker image

The root `Dockerfile` performs a multi-stage build: a Node.js stage runs `npm ci && npm run build` to produce the Vite bundle, and the final Python image installs FastAPI and copies the generated `frontend/dist/` assets. To test locally:

```bash
docker build -t cybergrader:latest .
docker run --rm -p 8000:8000 cybergrader:latest
```

The container exposes port `8000` and launches `uvicorn app.main:app`, automatically serving the bundled static assets.

> Notes: AWS/Hetzner helpers are experimental and not part of the primary path.

### Local quality checks

Run lightweight checks before committing changes:

```bash
# Backend: verify modules compile
cd backend
python -m compileall app

# Frontend: ensure the production bundle builds
cd ../frontend
npm install
npm run build

# (Optional) Playwright E2E suite – requires the backend running on :8000
npm run e2e
```
