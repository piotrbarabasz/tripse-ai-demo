# TRIPSE_FRONTEND_BUILD_V1
# Official Node multi-platform index verified from registry-1.docker.io 2026-10-31.
# Version matches frontend/.nvmrc. Builder tooling never enters the Python image.
FROM node:24.18.0-bookworm-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json frontend/.nvmrc ./
RUN test "$(node --version)" = "v$(tr -d '\r\n' < .nvmrc)" && npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

# Official multi-platform index verified 2026-10-29. Refresh deliberately with
# the API/worker/container checks in docs/CI_002_DOCKER_OPTIMIZATION.md.
FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/tripse.sqlite3
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY demo-fixtures/gt-v1 ./demo-fixtures/gt-v1
COPY --from=frontend-build /build/frontend/dist ./app/spa_dist
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "8"]
