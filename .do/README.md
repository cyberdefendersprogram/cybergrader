DigitalOcean deployment options
================================

This repo includes App Platform specs for production and demo deployments.

- Production: use a DigitalOcean Managed Database for Postgres (recommended)
- Demo/dev: use a Postgres sidecar container (ephemeral; not for production)

Files
- `.do/app.prod.yaml` — App Platform spec for production. Uses the repo Dockerfile and expects a `DATABASE_URL` secret that points to your DO Managed Postgres.
- `.do/app.dev.yaml` — App Platform spec for demo. Adds a Postgres sidecar and wires `DATABASE_URL` to it. Data is NOT persisted.

Usage (with doctl)
1) Authenticate doctl and choose your project/region.
2) Production (Managed DB):
   - Set a `DATABASE_URL` app secret to your Managed DB connection string (or edit the spec to put the value and mark it as secret in the UI).
   - Create/update the app: `doctl apps create --spec .do/app.prod.yaml` or `doctl apps update <APP_ID> --spec .do/app.prod.yaml`.
3) Demo (sidecar): `doctl apps create --spec .do/app.dev.yaml`.

Local development
- Use `docker-compose.yml` at repo root to run the API (`localhost:8000`) and Postgres (`localhost:5432`).

HTTPS strategy
- App Platform automatically provisions HTTPS certificates for app-provided and custom domains; no Nginx needed.
- On Droplets, place the API behind Nginx as a reverse proxy and use Let's Encrypt (Certbot) for TLS. See `scripts/setup-nginx-letsencrypt.sh` for a guided setup and the included Nginx config snippet.

