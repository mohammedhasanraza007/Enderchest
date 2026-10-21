# syntax=docker/dockerfile:1
# Three targets (docs/ARCHITECTURE.md 3): frontend-build, runtime, tools.
# Base images are pinned by tag; bump them deliberately and record it in docs/logs/evidence-log.md.

ARG PYTHON_IMAGE=python:3.13-slim-bookworm
ARG NODE_IMAGE=node:22-bookworm-slim

# ---- frontend-build -----------------------------------------------------------------------
# Phase 0 has no frontend. This stage only provides the empty `dist` that `runtime` copies,
# so the three targets exist from the start. Phase 1 replaces it with the real Vite build.
FROM ${NODE_IMAGE} AS frontend-build
WORKDIR /frontend
RUN mkdir -p dist

# ---- python-base (shared by runtime and tools) ----------------------------------------------
FROM ${PYTHON_IMAGE} AS python-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# Non-root user. /data and /backups exist in the image and belong to it, so a brand-new named
# volume mounted on /data inherits that ownership and the app can write to it.
RUN useradd --create-home --uid 10001 enderchest \
    && mkdir -p /data /backups /app \
    && chown enderchest:enderchest /data /backups /app
WORKDIR /app
# Dependencies first, so editing code does not reinstall them.
COPY backend/requirements.lock ./requirements.lock
RUN pip install -r requirements.lock

# ---- runtime --------------------------------------------------------------------------------
FROM python-base AS runtime
COPY --chown=enderchest:enderchest backend/app ./app
COPY --from=frontend-build --chown=enderchest:enderchest /frontend/dist ./frontend-dist
USER enderchest
EXPOSE 8470
# One worker only: the single-instance lock, the scheduler and the SQLite writer all assume it.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8470", \
     "--workers", "1", "--no-server-header"]

# ---- tools: lint, unit and integration tests, OpenAPI export ----------------------------------
# Node joins this target in Phase 1, when the frontend first needs it.
FROM python-base AS tools
COPY backend/requirements-dev.lock ./requirements-dev.lock
RUN pip install -r requirements-dev.lock
COPY backend/ ./
CMD ["pytest", "-q"]
