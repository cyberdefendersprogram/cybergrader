# Cyber Grader MVP

This repository hosts a minimal implementation of the **Cyber Grader Platform** described in `spec.md`. The MVP is composed of:

* A FastAPI backend (`backend/`) that loads course content from the bundled `content/` directory or a configured Git repository, manages lab/quiz/exam submissions in memory, and exposes REST endpoints for students, staff, and admins.
* A lightweight React single-page application (`frontend/index.html`) served as a static asset that interacts with the backend API.
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

Open `frontend/index.html` in your browser while the API is running on `http://localhost:8000`. Update `window.API_BASE` in the console if the API is hosted on a different origin.

The SPA supports logging in, viewing labs/quizzes/exams, submitting attempts, and checking the aggregated dashboard.

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

Set `CONTENT_REPO_URL` to clone course material from a Git repository (defaults to `https://github.com/cyberdefenders/cis53.git`; leave empty to rely on the bundled `content/` folder).
You can change the branch with `CONTENT_REPO_BRANCH` and the checkout location with `CONTENT_REPO_PATH`. The API refreshes the
clone during startup and whenever an admin triggers `/admin/sync`. Declare `CONTENT_REFRESH_SCHEDULE=nightly` (or another cron
hint) to document how often an external scheduler should run the sync job when you automate it outside the UI.

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

### Container images & deployment

Two bash scripts are included so you can ship containers without Terraform:

* `scripts/build-and-push-ecr.sh` – builds the repository image and pushes it to Amazon ECR. The script creates the repository if it does not exist, logs you in with the AWS CLI, and tags the image with `IMAGE_TAG` (defaults to `latest`).
* `scripts/deploy-hetzner.sh` – targets an existing Hetzner host over SSH, writes a minimal Docker Compose file, and starts the container. Set `BUILD_LOCALLY=1` to build and stream the image over SSH when you do not have a registry.

**Amazon ECR vs. Hetzner Cloud**

| Concern | Amazon ECR + ECS/Fargate | Hetzner (self-managed Docker host) |
| --- | --- | --- |
| Setup time | Higher—requires IAM, repository, task/service definitions | Faster—provision a VM and run the script |
| Scaling | Automatic with ECS/Fargate or EKS | Manual (use additional VMs or install Kubernetes yourself) |
| Networking | Deep AWS integration (VPC, ALB, PrivateLink) | Public IPs by default, private networking via VXLAN |
| Cost | Pay per image storage + compute minutes | Flat VM price, inexpensive bandwidth |
| Compliance | Easier to align with existing AWS guardrails | Need to manage hardening, patching, backups yourself |

For teams already on AWS, using ECR plus Fargate gives you managed scaling and IAM integration. Hetzner is compelling when you want predictable pricing and a simple VM that you control directly. The provided scripts let you evaluate both quickly.
