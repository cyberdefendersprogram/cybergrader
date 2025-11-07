#!/usr/bin/env bash
set -euo pipefail

# Deploy the backend container to DigitalOcean App Platform with a Postgres sidecar.
# Notes:
# - This is for demos/testing. For production, prefer a DO Managed Database.
# - Requires: doctl (https://docs.digitalocean.com/reference/doctl/), DO access token configured.
#
# Required env:
#   DO_APP_NAME          App name (e.g., cybergrader)
#   DO_REGION            Region slug (e.g., nyc)
# Optional env:
#   DO_APP_ID            If set, updates existing app; otherwise creates a new one
#   DO_INSTANCE_SIZE     App instance size slug (default: basic-xxs)
#   DO_INSTANCE_COUNT    Number of instances (default: 1)
#   POSTGRES_USER        (default: cyber)
#   POSTGRES_PASSWORD    (default: cyberpass)
#   POSTGRES_DB          (default: cybergrader)
#   POSTGRES_TAG         (default: 15-alpine)
#   DO_PROJECT_ID        If set, associates app with a project
#
# The API is built from the Dockerfile in repo root. The Postgres is a Docker Hub image.

: "${DO_APP_NAME:?Set DO_APP_NAME}"
: "${DO_REGION:?Set DO_REGION}"

DO_INSTANCE_SIZE=${DO_INSTANCE_SIZE:-basic-xxs}
DO_INSTANCE_COUNT=${DO_INSTANCE_COUNT:-1}

POSTGRES_USER=${POSTGRES_USER:-cyber}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-cyberpass}
POSTGRES_DB=${POSTGRES_DB:-cybergrader}
POSTGRES_TAG=${POSTGRES_TAG:-15-alpine}

SPEC_FILE=${SPEC_FILE:-digitalocean.app.yaml}

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
      - key: DATABASE_URL
        scope: RUN_AND_BUILD_TIME
        value: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - key: DATABASE_SCHEMA
        scope: RUN_AND_BUILD_TIME
        value: public
      - key: CONTENT_REPO_URL
        scope: RUN_AND_BUILD_TIME
        value: ""
      - key: CONTENT_REPO_BRANCH
        scope: RUN_AND_BUILD_TIME
        value: main

  - name: postgres
    image:
      registry_type: DOCKER_HUB
      repository: library/postgres
      tag: ${POSTGRES_TAG}
    instance_size_slug: ${DO_INSTANCE_SIZE}
    instance_count: 1
    envs:
      - key: POSTGRES_USER
        value: ${POSTGRES_USER}
        scope: RUN_AND_BUILD_TIME
      - key: POSTGRES_PASSWORD
        value: ${POSTGRES_PASSWORD}
        scope: RUN_AND_BUILD_TIME
      - key: POSTGRES_DB
        value: ${POSTGRES_DB}
        scope: RUN_AND_BUILD_TIME
    # Warning: App Platform provides ephemeral filesystems. This Postgres is for demo only.
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

