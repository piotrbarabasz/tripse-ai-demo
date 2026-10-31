"""Offline local/mock schema export. Never enters lifespan or starts a worker."""
import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/api/openapi.json"


@contextmanager
def isolated_app():
    # Clear inherited cloud/provider/storage configuration BEFORE importing main:
    # main deliberately composes its module-level ASGI app at import time.
    with TemporaryDirectory(prefix="tripse-openapi-") as directory:
        root = Path(directory)
        environment = {
            "CLOUD_FEATURE_MODE": "local", "PLANNING_MODE": "mock",
            "DATABASE_PATH": str(root / "jobs.sqlite3"),
            "DOCUMENT_STUDIO_DATA_PATH": str(root / "documents"),
            "DOCUMENT_STUDIO_FIXTURES_PATH": str(root / "fixtures"),
        }
        with patch.dict(os.environ, environment, clear=True):
            from app.main import create_app
            from app.waha import WahaSettings
            app = create_app(
                database_path=root / "jobs.sqlite3",
                document_data_path=root / "documents",
                document_fixtures_path=root / "fixtures",
                frontend_dist=root / "unbuilt",
                waha_settings=WahaSettings("", frozenset()),
            )
            yield app


def schema_text():
    with isolated_app() as app:
        schema = app.openapi()
    return json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    content = schema_text()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, "OpenAPI drift: run python -m scripts.export_openapi\n")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
