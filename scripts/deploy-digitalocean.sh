#!/usr/bin/env bash
set -euo pipefail

# Deploy the backend container to DigitalOcean App Platform backed by a
# DigitalOcean Managed Postgres database. This script emits the App Platform
# spec on the fly (no repo YAMLs), sets DATABASE_URL to the managed database,
# and can stream logs similar to the local deploy script.
#
# Requirements:
#   - doctl (https://docs.digitalocean.com/reference/doctl/) configured with an
#     access token that can manage App Platform apps.
#   - An existing DigitalOcean managed database with a connection string.
#
# You can provide configuration via environment variables or a dotenv file.
# If a file named .env.do exists at the repo root, this script will source it.
# Override with ENV_FILE_CANDIDATE=/path/to/file.env
#
# Required env:
#   DO_APP_NAME               App name (e.g., cybergrader)
#   DO_REGION                 Region slug (e.g., nyc)
#   DO_DB_CONNECTION_STRING   Full Postgres connection string from DO managed DB
#   DO_GITHUB_REPO            GitHub repo in owner/name form (e.g., org/cybergrader)
#
# Optional env:
#   DO_APP_ID                 If set, updates existing app; otherwise creates new
#   DO_INSTANCE_SIZE          App instance size slug (default: basic-xxs)
#   DO_INSTANCE_COUNT         Number of instances (default: 1)
#   DO_PROJECT_ID             If set, associates app with a project
#   DATABASE_SCHEMA           Schema name (default: public)
#   FOLLOW_LOGS               If 1, follow logs after submission (default: 1)

# Resolve repo root and load env file if present
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE_CANDIDATE="${ENV_FILE_CANDIDATE:-${ROOT_DIR}/.env.do}"
if [[ -f "${ENV_FILE_CANDIDATE}" ]]; then
  echo "Using env file: ${ENV_FILE_CANDIDATE}"
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE_CANDIDATE}"
  set +a
fi

: "${DO_APP_NAME:?Set DO_APP_NAME}"
: "${DO_REGION:?Set DO_REGION}"

if [[ -z "${DO_DB_CONNECTION_STRING:-}" ]]; then
  echo "Set DO_DB_CONNECTION_STRING for the managed database" >&2
  exit 1
fi

DO_INSTANCE_SIZE=${DO_INSTANCE_SIZE:-basic-xxs}
DO_INSTANCE_COUNT=${DO_INSTANCE_COUNT:-1}
DATABASE_SCHEMA=${DATABASE_SCHEMA:-public}
FOLLOW_LOGS=${FOLLOW_LOGS:-1}

# Try to derive DO_GITHUB_REPO from git remote if not provided
if [[ -z "${DO_GITHUB_REPO:-}" ]]; then
  if command -v git >/dev/null 2>&1; then
    if GIT_URL=$(git -C "${ROOT_DIR}" config --get remote.origin.url 2>/dev/null); then
      # Support git@github.com:owner/repo.git and https URLs
      if [[ "${GIT_URL}" =~ github.com[:/](.+)/([^/\.]*) ]]; then
        DO_GITHUB_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
      fi
    fi
  fi
fi

DO_GITHUB_BRANCH=${DO_GITHUB_BRANCH:-main}

SPEC_FILE=${SPEC_FILE:-digitalocean.app.yaml}

cat > "${SPEC_FILE}" <<YAML
name: ${DO_APP_NAME}
region: ${DO_REGION}
services:
  - name: api
    github:
      repo: ${DO_GITHUB_REPO}
      branch: ${DO_GITHUB_BRANCH}
      deploy_on_push: true
    dockerfile_path: Dockerfile
    source_dir: .
    http_port: 8000
    instance_size_slug: ${DO_INSTANCE_SIZE}
    instance_count: ${DO_INSTANCE_COUNT}
    routes:
      - path: /
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        value: "${DO_DB_CONNECTION_STRING}"
      - key: DATABASE_SCHEMA
        scope: RUN_TIME
        value: ${DATABASE_SCHEMA}
YAML

if [[ -n "${DO_PROJECT_ID:-}" ]]; then
  echo "Associating app with project ${DO_PROJECT_ID}"
fi

# If DO_APP_ID not provided, try to resolve by name to avoid 409 conflicts
if [[ -z "${DO_APP_ID:-}" ]]; then
  if command -v doctl >/dev/null 2>&1; then
    EXISTING_ID=$(doctl apps list --format ID,Spec.Name --no-header | awk -v name="${DO_APP_NAME}" '$2==name {print $1}' | head -n1 || true)
    if [[ -n "${EXISTING_ID}" ]]; then
      DO_APP_ID="${EXISTING_ID}"
      echo "Found existing app '${DO_APP_NAME}' (ID=${DO_APP_ID}); updating instead of creating"
    fi
  fi
fi

if [[ -n "${DO_APP_ID:-}" ]]; then
  echo "Updating existing app: ${DO_APP_ID}"
  doctl apps update "${DO_APP_ID}" --spec "${SPEC_FILE}"
else
  echo "Creating new app from spec: ${SPEC_FILE}"
  doctl apps create --spec "${SPEC_FILE}"
fi

echo "Deployment submitted. Use 'doctl apps list' and 'doctl apps logs' to monitor."

if [[ "${FOLLOW_LOGS}" == "1" ]]; then
  APP_ID=${DO_APP_ID:-}
  if [[ -z "${APP_ID}" ]]; then
    APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | awk -v name="${DO_APP_NAME}" '$2==name {print $1}' | head -n1)
  fi
  if [[ -n "${APP_ID}" ]]; then
    echo "Following logs for app ${APP_ID} (Ctrl+C to stop)"
    # Valid types: build, deploy, run (repeat flag for multiple types)
    doctl apps logs "${APP_ID}" --type build --type deploy --type run --follow
  else
    echo "Could not resolve app ID; skipping log follow" >&2
  fi
fi
