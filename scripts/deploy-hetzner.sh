#!/usr/bin/env bash
set -euo pipefail

: "${HETZNER_HOST:?Set HETZNER_HOST (e.g. 65.21.x.x)}"
: "${SSH_USER:=root}"
: "${REMOTE_IMAGE:=cybergrader:latest}"
: "${REMOTE_ENV_FILE:=/etc/cybergrader/.env}"

if [[ -n "${BUILD_LOCALLY:-}" ]]; then
  docker build -t "${REMOTE_IMAGE}" .
  docker save "${REMOTE_IMAGE}" | bzip2 | ssh "${SSH_USER}@${HETZNER_HOST}" "bunzip2 | docker load"
fi

read -r -d '' COMPOSE_CONTENT <<EOF
version: "3.8"
services:
  api:
    image: ${REMOTE_IMAGE}
    restart: unless-stopped
    env_file: ${REMOTE_ENV_FILE}
    ports:
      - "80:8000"
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

ssh "${SSH_USER}@${HETZNER_HOST}" "set -euo pipefail
mkdir -p /etc/cybergrader
cat <<'COMPOSE' > /etc/cybergrader/docker-compose.yml
${COMPOSE_CONTENT}
COMPOSE
docker compose -f /etc/cybergrader/docker-compose.yml pull || true
docker compose -f /etc/cybergrader/docker-compose.yml up -d
"

echo "Deployment triggered on ${HETZNER_HOST}"
