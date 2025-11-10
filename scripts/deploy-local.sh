#!/usr/bin/env bash
set -euo pipefail

# Spin up the local docker-compose stack for development/testing and
# stream all container logs into a single file for later inspection.
#
# Usage: scripts/deploy-local.sh
#   - Builds the API image, starts the Postgres dependency, and tails logs.
#   - Press Ctrl+C to stop; the script will tear everything down cleanly.
#
# Optional env vars:
#   LOG_DIR   Directory to place the aggregated log file (default: ./logs)
#   LOG_FILE  Explicit log file path (default: $LOG_DIR/local-deploy.log)
#
# Requires docker compose v2 or newer.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/local-deploy.log}"
ENV_FILE_CANDIDATE="${ENV_FILE_CANDIDATE:-${ROOT_DIR}/.env.local}"
COMPOSE_ENV_ARGS=()

if [[ -f "${ENV_FILE_CANDIDATE}" ]]; then
  echo "Using env file: ${ENV_FILE_CANDIDATE}"
  COMPOSE_ENV_ARGS+=("--env-file" "${ENV_FILE_CANDIDATE}")
fi

if ! command -v docker &>/dev/null; then
  echo "docker is required to run the local deployment" >&2
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "docker compose v2 is required. Install Docker Desktop or the docker-compose-plugin." >&2
  exit 1
fi

pushd "${ROOT_DIR}" >/dev/null

cleanup() {
  echo "\nStopping local stack..."
  docker compose -f "${COMPOSE_FILE}" down
}
trap cleanup EXIT INT TERM

echo "Building and starting services defined in ${COMPOSE_FILE}"
docker compose -f "${COMPOSE_FILE}" "${COMPOSE_ENV_ARGS[@]}" up --build -d

: > "${LOG_FILE}"
echo "Streaming logs to ${LOG_FILE} (Ctrl+C to stop)"
docker compose -f "${COMPOSE_FILE}" "${COMPOSE_ENV_ARGS[@]}" logs -f --no-color | tee -a "${LOG_FILE}"

popd >/dev/null
