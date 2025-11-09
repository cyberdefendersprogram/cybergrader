#!/usr/bin/env bash
set -euo pipefail

# Deploy the backend container to DigitalOcean App Platform backed by a managed
# Postgres database. The script emits an App Platform spec that reuses the
# repository Dockerfile and wires the DATABASE_URL to an existing DO managed DB
# connection string or secret.
#
# Requirements:
#   - doctl (https://docs.digitalocean.com/reference/doctl/) configured with an
#     access token that can manage App Platform apps.
#   - An existing DigitalOcean managed database with a connection string.
#
# Required env:
#   DO_APP_NAME               App name (e.g., cybergrader)
#   DO_REGION                 Region slug (e.g., nyc)
#   DO_DB_CONNECTION_STRING   Full Postgres URL OR set DO_DB_SECRET_NAME instead
#       or
#   DO_DB_SECRET_NAME         Name of an App Platform secret containing the URL
#
# Optional env:
#   DO_APP_ID                 If set, updates existing app; otherwise creates new
#   DO_INSTANCE_SIZE          App instance size slug (default: basic-xxs)
#   DO_INSTANCE_COUNT         Number of instances (default: 1)
#   DO_PROJECT_ID             If set, associates app with a project
#   CONTENT_REPO_URL          Repo for course content (default: empty / bundled)
#   CONTENT_REPO_BRANCH       Branch to sync (default: main)
#   DATABASE_SCHEMA           Schema name (default: public)

: "${DO_APP_NAME:?Set DO_APP_NAME}"
: "${DO_REGION:?Set DO_REGION}"

if [[ -z "${DO_DB_CONNECTION_STRING:-}" && -z "${DO_DB_SECRET_NAME:-}" ]]; then
  echo "Set DO_DB_CONNECTION_STRING or DO_DB_SECRET_NAME for the managed database" >&2
  exit 1
fi

DO_INSTANCE_SIZE=${DO_INSTANCE_SIZE:-basic-xxs}
DO_INSTANCE_COUNT=${DO_INSTANCE_COUNT:-1}
DATABASE_SCHEMA=${DATABASE_SCHEMA:-public}
CONTENT_REPO_URL=${CONTENT_REPO_URL:-}
CONTENT_REPO_BRANCH=${CONTENT_REPO_BRANCH:-main}

SPEC_FILE=${SPEC_FILE:-digitalocean.app.yaml}

if [[ -n "${DO_DB_SECRET_NAME:-}" ]]; then
  read -r -d '' DATABASE_URL_ENV <<YAML || true
      - key: DATABASE_URL
        scope: RUN_TIME
        secret_name: ${DO_DB_SECRET_NAME}
YAML
else
  read -r -d '' DATABASE_URL_ENV <<YAML || true
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${DO_DB_CONNECTION_STRING}
YAML
fi

cat > "${SPEC_FILE}" <<YAML
name: ${DO_APP_NAME}
region: ${DO_REGION}
services:
  - name: api
    dockerfile_path: Dockerfile
    source_dir: .
    http_port: 8000
    instance_size_slug: ${DO_INSTANCE_SIZE}
    instance_count: ${DO_INSTANCE_COUNT}
    routes:
      - path: /
    envs:
${DATABASE_URL_ENV}
      - key: DATABASE_SCHEMA
        scope: RUN_TIME
        value: ${DATABASE_SCHEMA}
      - key: CONTENT_REPO_URL
        scope: RUN_TIME
        value: "${CONTENT_REPO_URL}"
      - key: CONTENT_REPO_BRANCH
        scope: RUN_TIME
        value: ${CONTENT_REPO_BRANCH}
YAML

if [[ -n "${DO_PROJECT_ID:-}" ]]; then
  echo "Associating app with project ${DO_PROJECT_ID}"
fi

if [[ -n "${DO_APP_ID:-}" ]]; then
  echo "Updating existing app: ${DO_APP_ID}"
  doctl apps update "${DO_APP_ID}" --spec "${SPEC_FILE}"
else
  echo "Creating new app from spec: ${SPEC_FILE}"
  doctl apps create --spec "${SPEC_FILE}"
fi

echo "Deployment submitted. Use 'doctl apps list' and 'doctl apps logs' to monitor."

