DigitalOcean deployment options
================================

This repo includes App Platform specs for production and demo deployments.

- Production: use a DigitalOcean Managed Database for Postgres (recommended)
- Demo/dev: use a Postgres sidecar container (ephemeral; not for production)

Files
- `.do/app.prod.yaml` — App Platform spec for production. Builds from GitHub repo with Dockerfile and expects a `DATABASE_URL` secret pointing to your DO Managed Postgres.
- `.do/app.dev.yaml` — App Platform spec for demo. Builds from GitHub repo and adds a Postgres sidecar. Data is NOT persisted.
- `.do/app.full.yaml` — Single-container build that also compiles the frontend and serves it from the API container (multi-stage Dockerfile).

Usage (with doctl)
1) Connect DigitalOcean to your GitHub account and ensure the repo `cyberdefendersprogram/cybergrader` is authorized.
2) Authenticate `doctl` and choose your project/region.
3) Production (Managed DB):
   - Set a `DATABASE_URL` app secret to your Managed DB connection string (sslmode=require).
   - Create/update the app: `doctl apps create --spec .do/app.prod.yaml` or `doctl apps update <APP_ID> --spec .do/app.prod.yaml`.
4) Demo (sidecar): `doctl apps create --spec .do/app.dev.yaml`.
5) Frontend-in-API container: `doctl apps create --spec .do/app.full.yaml`.

Local development
- Use `docker-compose.yml` at repo root to run the API (`localhost:8000`) and Postgres (`localhost:5432`).

HTTPS strategy
- App Platform automatically provisions HTTPS certificates for app-provided and custom domains; no Nginx needed on App Platform.
- On Droplets, place the API behind Nginx as a reverse proxy and use Let's Encrypt (Certbot) for TLS. See `scripts/setup-nginx-letsencrypt.sh` for a guided setup and the included Nginx config snippet.
