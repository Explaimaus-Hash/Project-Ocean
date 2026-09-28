"""List input states or explicitly inspect one local dataset; never download."""

import argparse
import json
import sys
from collections.abc import Sequence

from backend.app.ingestion.incois_bio_roms import input_status, inspect_local_dataset
from backend.app.ingestion.registry import (
    PROJECT_ROOT,
    RegistryError,
    find_dataset,
    load_registry,
)
from backend.app.storage.inspection_reports import save_inspection_report


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit local-only operator work; nonzero means no usable inspection."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Stat configured final paths; no content reads")
    inspect_parser = commands.add_parser("inspect", help="Read a local NetCDF header")
    inspect_parser.add_argument("dataset_id")
    inspect_parser.add_argument(
        "--verify-checksum",
        action="store_true",
        help="Explicitly read all file bytes in chunks to verify the published MD5",
    )
    inspect_parser.add_argument(
        "--save", action="store_true", help="Atomically save report below data/metadata"
    )
    arguments = parser.parse_args(argv)
    try:
        registry = load_registry()
        if arguments.command == "status":
            reports = [
                input_status(entry, PROJECT_ROOT).model_dump(mode="json")
                for entry in registry.datasets
            ]
            print(json.dumps({"schema_version": 1, "datasets": reports}, indent=2))
            return 0
        definition = find_dataset(registry, arguments.dataset_id)
        report = inspect_local_dataset(
            definition, PROJECT_ROOT, verify_checksum=arguments.verify_checksum
        )
        if arguments.save:
            save_inspection_report(report, PROJECT_ROOT)
        print(report.model_dump_json(indent=2))
        return 0 if report.status == "not_prepared" else 2
    except (RegistryError, OSError, ValueError):
        print(
            json.dumps(
                {
                    "error": "operator_request_failed",
                    "message": "Check registry, dataset ID, and local report access.",
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
