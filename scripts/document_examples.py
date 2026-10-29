"""Explicit offline/DEV maintenance; never invoked by application startup."""
import argparse
import json
from pathlib import Path

from app.document_studio.examples import catalog, seed, obsolete_inventory
from app.document_studio.repository import JsonRepository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["dry-run", "init", "verify", "obsolete", "manifest"])
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--dev-bucket")
    parser.add_argument("--confirm-dev-init", action="store_true", help="Operator approval after reviewing dry-run and backing up the selected DEV bucket")
    args = parser.parse_args()
    if args.action == "manifest":
        print(json.dumps(catalog(), ensure_ascii=True, indent=2))
        return
    if bool(args.data_root) == bool(args.dev_bucket):
        parser.error("Select exactly one explicit --data-root or --dev-bucket; no default environment")
    if args.dev_bucket:
        if args.action == "init" and not args.confirm_dev_init:
            parser.error("Review dry-run and backup DEV, then explicitly pass --confirm-dev-init. No PROD operation is supported.")
        # Exact naming convention is an additional guard, not an environment inference.
        if "-dev-" not in args.dev_bucket.lower() or "prod" in args.dev_bucket.lower():
            parser.error("Only an explicitly named -dev- bucket is supported")
        from google.cloud import storage
        from app.document_studio.cloud_storage import GCSRepository
        repo = GCSRepository(storage.Client().bucket(args.dev_bucket))
    else:
        repo = JsonRepository(args.data_root)
        if args.action == "init":
            repo.initialize()
    result = obsolete_inventory(repo) if args.action == "obsolete" else seed(repo, apply=args.action == "init")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if any(r["status"] == "conflict_preserved" or args.action == "verify" and r["status"] == "would_create" for r in result):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
