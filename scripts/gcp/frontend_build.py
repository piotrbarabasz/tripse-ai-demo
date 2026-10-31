"""Versioned frontend input contract; historical Python-only contexts stay exact."""
import json
from pathlib import PurePosixPath

MARKER = b"# TRIPSE_FRONTEND_BUILD_V1"
NODE_IMAGE = "node:24.18.0-bookworm-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d"
PYTHON_IMAGE = "python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159"
CONFIG_FILES = frozenset({"frontend/package.json", "frontend/package-lock.json", "frontend/.nvmrc",
                          "frontend/index.html", "frontend/tsconfig.json", "frontend/vite.config.ts"})


def is_frontend_input(name):
    path = PurePosixPath(name)
    return name in CONFIG_FILES or (
        name.startswith("frontend/src/") and path.suffix in {".ts", ".tsx", ".css"}
        and not {"node_modules", "dist", "coverage", ".vite", ".cache"}.intersection(path.parts))


def validate_frontend_source(files):
    recipe = files.get("Dockerfile", b"")
    if MARKER not in recipe:
        return  # Do not widen the source context of pre-integration releases.
    lines = [line.strip() for line in recipe.decode().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if [line for line in lines if line.startswith("FROM ")] != [f"FROM {NODE_IMAGE} AS frontend-build", f"FROM {PYTHON_IMAGE}"]:
        raise ValueError("Unreviewed frontend image recipe; explicit pin review required")
    required = CONFIG_FILES | {"frontend/src/main.tsx"}
    if not required <= files.keys():
        raise ValueError("Committed frontend build inputs are incomplete")
    if files["frontend/.nvmrc"].strip() != b"24.18.0":
        raise ValueError("Frontend Node pin differs from reviewed builder")
    if "RUN npm run build" not in lines or "COPY --from=frontend-build /build/frontend/dist ./app/spa_dist" not in lines:
        raise ValueError("Frontend output build/copy contract differs")
    if 'RUN test "$(node --version)" = "v$(tr -d \'\\r\\n\' < .nvmrc)" && npm ci' not in lines:
        raise ValueError("Frontend install must use reviewed Node and npm ci")
    package = json.loads(files["frontend/package.json"])
    lock = json.loads(files["frontend/package-lock.json"])
    root = lock.get("packages", {}).get("", {})
    if lock.get("lockfileVersion") != 3 or any(root.get(key, {}) != package.get(key, {}) for key in ("dependencies", "devDependencies", "engines")):
        raise ValueError("Frontend package and lockfile inputs differ")
