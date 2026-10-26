"""Explicit operator dispatch recovery, without resetting jobs or paid generation.

Run as a module after reviewing the selected DEV job and queue logs. ADC needs
only the selected database/queue and actAs on its task account. No deployment.
"""
import argparse
from pathlib import Path
from uuid import UUID

from scripts.gcp.deployment_contract import ROOT, load_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=["dev", "prod"])
    parser.add_argument("--config-dir", type=Path, default=ROOT)
    parser.add_argument("--trip-id", type=UUID, required=True)
    args = parser.parse_args()
    config = load_pair(args.environment, args.config_dir)
    if config["CLOUD_FEATURE_MODE"] != "cloud_demo":
        parser.error("Recovery is only available for cloud_demo")
    from app.cloud_runtime import build_components
    jobs = build_components(config.demo_settings()).jobs
    queued = jobs.recover(str(args.trip_id))
    print("Recovery task submitted" if queued else "No recovery: missing, terminal or active lease")


if __name__ == "__main__":
    main()
