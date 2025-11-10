FROM node:20-alpine AS webbuild

WORKDIR /app/frontend

# Install deps and build frontend
COPY frontend/package*.json ./
# Install git in case any npm dependencies resolve from git sources
RUN apk add --no-cache git \
 && npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app/backend

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/backend/requirements.txt

# App source
COPY backend/app /app/backend/app

# Include local course content in the image so the API can load it
COPY content /app/content

# Copy built frontend assets into expected location for FastAPI static serving
COPY --from=webbuild /app/frontend/dist /app/frontend/dist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
