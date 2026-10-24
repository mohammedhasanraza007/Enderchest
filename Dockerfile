# syntax=docker/dockerfile:1
# Targets (docs/ARCHITECTURE.md 3): frontend-build, runtime, tools, e2e; bakeoff (Phase 3, on demand).
# Base images are pinned by tag; bump them deliberately and record it in docs/logs/evidence-log.md.

ARG PYTHON_IMAGE=python:3.13-slim-bookworm
ARG NODE_IMAGE=node:22-bookworm-slim
# Must equal the @playwright/test version in frontend/package.json (ARCHITECTURE 3).
ARG PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright:v1.64.1-noble

# ---- frontend-deps --------------------------------------------------------------------------
# node_modules from the lock file. Cached until package.json or package-lock.json change.
FROM ${NODE_IMAGE} AS frontend-deps
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

# ---- frontend-build ------------------------------------------------------------------------
# The Vite bundle. `assets/logo` sits beside `frontend` here as in the repository, because the
# build reads the supplied logo and icons from `../assets/logo`.
FROM frontend-deps AS frontend-build
COPY assets/logo /assets/logo
COPY frontend/ ./
RUN npm run build

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
# The build date is the last layer so a new date never re-runs the steps above. build.bat sets it;
# a build without it reports "not recorded" in Settings, never an invented date.
ARG BUILD_DATE=""
ENV ENDERCHEST_BUILD_DATE=${BUILD_DATE}
USER enderchest
EXPOSE 8470
# One worker only: the single-instance lock, the scheduler and the SQLite writer all assume it.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8470", \
     "--workers", "1", "--no-server-header"]

# ---- tools: lint, unit and integration tests, OpenAPI export, frontend checks ----------------
# Python and Node together. The Node binary comes from the pinned Node image (same Debian
# release as the Python image, so the same libc).
FROM python-base AS tools
# scripts/export_openapi.py imports the app; a script's own folder is what Python puts first.
ENV PYTHONPATH=/app
COPY --from=frontend-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-deps /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY backend/requirements-dev.lock ./requirements-dev.lock
RUN pip install -r requirements-dev.lock
COPY --from=frontend-deps /frontend/node_modules /frontend/node_modules
COPY assets/logo /assets/logo
COPY frontend/ /frontend/
COPY scripts/export_openapi.py ./scripts/export_openapi.py
# Text fixtures the unit tests read (the owner's private photos never enter an image).
COPY tests/fixtures/expiry_cases.csv /fixtures/expiry_cases.csv
ENV ENDERCHEST_FIXTURES=/fixtures
COPY backend/ ./
CMD ["pytest", "-q"]

# ---- e2e: Playwright against the test app ---------------------------------------------------
# The official image brings the matching browsers. Tests live in tests/e2e and talk to the test
# app by sharing its network (compose.test.yaml), so the Host header is a local one.
FROM ${PLAYWRIGHT_IMAGE} AS e2e
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY assets/logo /assets/logo
COPY frontend/ ./
COPY tests/e2e /tests/e2e
# The specs sit outside /frontend, so give them the same node_modules (same files, same modules).
RUN ln -s /frontend/node_modules /tests/node_modules
CMD ["npx", "playwright", "test"]

# ---- bakeoff: the Phase 3 OCR engine measurement (D-099), built only by "test.bat bakeoff" ------
# All four candidates: RapidOCR (as in the app), EasyOCR (PyTorch, CPU wheels), docTR (onnxtr)
# and Tesseract (Debian package). Never used by the app. The engines' models are fetched while
# the image is built, so the measurement itself runs with no network (test.bat uses --network none).
# EasyOCR brings the full OpenCV wheel, which needs libGL and GLib even without a screen.
FROM python-base AS bakeoff
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
       libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-bakeoff.txt ./requirements-bakeoff.txt
RUN pip install -c requirements.lock --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements-bakeoff.txt
ENV PYTHONPATH=/app
COPY backend/app ./app
COPY scripts/ocr_bakeoff.py ./scripts/ocr_bakeoff.py
RUN python scripts/ocr_bakeoff.py --warm
CMD ["python", "scripts/ocr_bakeoff.py", "--photos", "/photos", "--out", "/results"]
