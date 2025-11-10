# Cyber Grader MVP

This repository hosts a minimal implementation of the **Cyber Grader Platform** described in `spec.md`. The MVP is composed of:

* A FastAPI backend (`backend/`) that loads course content from the bundled `content/` directory or a configured Git repository, manages lab/quiz/exam submissions in memory, and exposes REST endpoints for students, staff, and admins.
* A polished React + TypeScript single-page application (`frontend/`) built with Vite and served as static assets from the FastAPI backend.
* Sample course content in Markdown/YAML under `content/` to demonstrate labs, quizzes, exam stages, and lecture notes.

## Getting started

### Backend API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API boots with demo content synced from the local `content/` directory. Authentication is mocked with three predefined emails:

| Email              | Role    |
| ------------------ | ------- |
| `alice@student.edu` | student |
| `sam@staff.edu`     | staff   |
| `ada@admin.edu`     | admin   |

### Frontend SPA

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API requests to `http://localhost:8000` so the React application can interact with FastAPI during development. When you are ready to ship static assets, run `npm run build` and the compiled bundle in `frontend/dist/` will be automatically served by the backend (including a catch-all route for client-side navigation).

The UI supports logging in, viewing labs/quizzes/exams, submitting attempts, and checking the aggregated dashboard—now with an updated layout, markdown rendering, and toast notifications.

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

Adding new YAML/Markdown files and calling the `/admin/sync` endpoint will refresh the in-memory store.

The backend reads course material from the local `content/` directory in this repository. A staff/admin can trigger a reload by calling `/admin/sync` (the UI provides a "Sync content" button). The API logs how many items were loaded and persists them to the configured Postgres backend.

### Google Sheets sync

The `/admin/export-scores` endpoint exports all lab, quiz, and exam attempts and, when configured, pushes them to a Google Sheet.

Provide the following environment variables before starting the API to enable synchronization:

| Variable | Description |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Either the JSON string for a Google service account or a path to the credential file. |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | The ID of the target spreadsheet that contains `Labs`, `Quizzes`, `Exams`, and `Meta` tabs. |

When the credentials or spreadsheet are not configured, the export still returns the data but reports that syncing was skipped.

### Postgres persistence (Aurora or Hetzner)

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

Nightly backups are recommended whether you run Aurora snapshots or `pg_dump` against a Hetzner-managed container. The backup
schedule variable does not execute the backup itself—it advertises the cadence for your automation or runbooks.

### Supabase persistence

Set `SUPABASE_URL` and either `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_ANON_KEY` to have the API hydrate from and persist to Supabase. When the variables are not set the service falls back to the in-memory store.

The store expects the following tables to exist (all columns are snake_case and timestamps should use `timestamptz`):

| Table | Columns |
| --- | --- |
| `labs` | `id text primary key`, `title text`, `version text`, `instructions_path text`, `flags jsonb` |
| `quizzes` | `id text primary key`, `title text`, `version text`, `questions jsonb` |
| `exams` | `id text primary key`, `title text`, `version text`, `stages jsonb` |
| `lab_submissions` | `user_id text`, `lab_id text`, `flag_name text`, `correct boolean`, `submitted_at timestamptz` |
| `quiz_submissions` | `user_id text`, `quiz_id text`, `score integer`, `max_score integer`, `submitted_at timestamptz` |
| `exam_submissions` | `user_id text`, `exam_id text`, `stage_id text`, `score integer`, `max_score integer`, `submitted_at timestamptz` |

Supabase gives you managed Postgres, authentication, storage, and a built-in REST interface. Compared with Amazon RDS you avoid managing separate IAM, connection pooling, or realtime features, but RDS gives you tighter VPC integration and more control over parameter groups. For this MVP, Supabase is the quickest way to match the platform spec because it bundles auth and APIs. You can still point the service at RDS by omitting the Supabase variables and adding a custom store implementation if you need full AWS alignment.

### Deployment

Use the provided scripts to run locally or deploy to managed infrastructure:

- `scripts/deploy-local.sh` – spins up the local Docker Compose stack (API + Postgres) and streams every container log into `logs/local-deploy.log`. Press <kbd>Ctrl</kbd>+<kbd>C</kbd> to tear down the stack when you are done testing.
- `scripts/deploy-digitalocean.sh` – deploys to DigitalOcean App Platform using a generated spec (no repository YAMLs needed) and connects the app to a **DigitalOcean Managed Database** via `DO_DB_CONNECTION_STRING`. Optionally follows build/deploy/runtime logs similar to the local script.
- `scripts/build-and-push-ecr.sh` – builds the repository image (including the compiled frontend assets) and pushes it to Amazon ECR. The script creates the repository if it does not exist, logs you in with the AWS CLI, and tags the image with `IMAGE_TAG` (defaults to `latest`).
- `scripts/deploy-hetzner.sh` – targets an existing Hetzner host over SSH, writes a minimal Docker Compose file, and starts the container. Set `BUILD_LOCALLY=1` to build the Dockerfile locally—which now bundles the frontend—before streaming the image over SSH when you do not have a registry.

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

**Amazon ECR vs. Hetzner Cloud**

| Concern | Amazon ECR + ECS/Fargate | Hetzner (self-managed Docker host) |
| --- | --- | --- |
| Setup time | Higher—requires IAM, repository, task/service definitions | Faster—provision a VM and run the script |
| Scaling | Automatic with ECS/Fargate or EKS | Manual (use additional VMs or install Kubernetes yourself) |
| Networking | Deep AWS integration (VPC, ALB, PrivateLink) | Public IPs by default, private networking via VXLAN |
| Cost | Pay per image storage + compute minutes | Flat VM price, inexpensive bandwidth |
| Compliance | Easier to align with existing AWS guardrails | Need to manage hardening, patching, backups yourself |

For teams already on AWS, using ECR plus Fargate gives you managed scaling and IAM integration. Hetzner is compelling when you want predictable pricing and a simple VM that you control directly. The provided scripts let you evaluate both quickly.

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
