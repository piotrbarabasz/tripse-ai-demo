# MAKE-001: one entry point; application/deployment logic stays in existing modules.
.DEFAULT_GOAL := help
.NOTPARALLEL:
ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
.SHELLFLAGS := /d /s /c
PYTHON ?= python
else
PYTHON ?= python3
endif

# Values travel as environment variables, never as interpolated shell commands.
export ENV TAG CONFIRM CONFIG_DIR OFFLINE HOST PORT BASE_URL

# 1. Help / Configuration (GNU Make builtins only; no Python/shell needed)
define HELP
TRIPSE AI Demo - GNU Make

Help / Configuration:
  help             Show targets, parameters and examples (default)
  doctor           Report Python/pip/venv, Git, Make, Docker/Compose; optional gcloud
Installation:
  install          Create/reuse .venv; pip install -r requirements.txt (Python 3.12+)
  install-dev      Install requirements-dev.txt (includes runtime dependencies)
  install-browser  Install Playwright Chromium after install-dev
Local Development:
  dev              Local API using .env + shell configuration, no worker
  dev-mock         Local API with explicit PLANNING_MODE=mock, no worker
  dev-live         Validate live provider configuration, then start local API
  worker           Start ONE app.worker with the same .env + shell configuration
Docker:
  docker-up        compose.yaml up --build -d api worker (no WAHA)
  docker-down      Stop Compose; preserve volumes and local data
  docker-build     Build API/worker images; no cloud operations
  docker-logs      Follow Compose logs
  docker-ps        Show Compose services
  docker-restart   Restart API/worker (configuration is unchanged)
  docker-mock      Recreate API/worker with explicit mock mode
  docker-waha      Start existing whatsapp profile (configure WAHA first)
Testing / Quality:
  test, test-unit   Standard pytest suite
  test-browser     All 8 browser smoke scripts; temporary API/worker as needed
  test-container   Existing optional local Docker Cloud Preview smoke
  test-all         pytest -> browser smoke -> container smoke (requires Docker)
  check            git diff --check; Docker Compose config (no new linter)
Demo (opens an existing local API; never starts another server):
  demo-hub         /hub
  demo-docs        /documents/demo
  demo-planner     / (worker needed for generated results)
  demo-whatsapp    /demo/chat (requires mock API AND mock worker)
GCP Deployment (delegates to scripts/gcp/deployment.py):
  gcp-preflight    ENV=dev|prod [TAG=SHA] [OFFLINE=1]; ENV defaults to dev
  gcp-setup        ENV=dev (explicit; modifies GCP resources)
  gcp-build        ENV=dev (explicit; clean committed HEAD required)
  deploy-dev       [TAG=SHA]; deploy to DEV (modifies GCP)
  deploy-prod      TAG=SHA CONFIRM=prod; promote existing image, no rebuild
  gcp-smoke        ENV=dev|prod [TAG=SHA]; PROD requires TAG, default ENV=dev
  gcp-rollback     ENV=dev|prod TAG=SHA CONFIRM=rollback
  gcp-dry-run      ENV=dev|prod [TAG=SHA]; default ENV=dev, PROD requires TAG
Maintenance:
  clean            Only Python/test caches outside user data; no .env/DB/volumes/assets

Parameters: PYTHON=bootstrap-executable HOST=127.0.0.1 PORT=8000
            BASE_URL=http://localhost:8000 CONFIG_DIR=directory-with-both-GCP-env-files
            TAG=full-lowercase-40-character-commit-SHA (never latest)
Examples:
  make install-dev
  make install-browser
  make dev-mock                 # terminal 1
  make worker PLANNING_MODE=mock # terminal 2
  make test
  make gcp-preflight ENV=dev OFFLINE=1
  make gcp-dry-run ENV=dev
  make deploy-prod TAG=SHA CONFIRM=prod
GNU Make returns nonzero on a failed child; its own exit code is usually 2.
endef

help:
	$(info $(HELP))

# 2. Installation
install install-dev install-browser:
	@"$(PYTHON)" scripts/dev.py $@

# 3. Local Development
dev dev-mock dev-live worker:
	@"$(PYTHON)" scripts/dev.py $@

# 4. Docker
docker-up docker-down docker-build docker-logs docker-ps docker-restart docker-mock docker-waha:
	@"$(PYTHON)" scripts/dev.py $@

# 5. Testing / Quality
test test-unit test-browser test-container test-all check:
	@"$(PYTHON)" scripts/dev.py $@

# 6. Demo
demo-hub demo-docs demo-planner demo-whatsapp:
	@"$(PYTHON)" scripts/dev.py $@

# 7. GCP Deployment
gcp-preflight gcp-setup gcp-build deploy-dev deploy-prod gcp-smoke gcp-rollback gcp-dry-run:
	@"$(PYTHON)" scripts/dev.py $@

# 8. Maintenance / Configuration
clean doctor:
	@"$(PYTHON)" scripts/dev.py $@

.PHONY: help doctor install install-dev install-browser dev dev-mock dev-live worker \
 docker-up docker-down docker-build docker-logs docker-ps docker-restart docker-mock docker-waha \
 test test-unit test-browser test-container test-all check \
 demo-hub demo-docs demo-planner demo-whatsapp \
 gcp-preflight gcp-setup gcp-build deploy-dev deploy-prod gcp-smoke gcp-rollback gcp-dry-run clean
