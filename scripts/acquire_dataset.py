"""Explicit operator CLI: JSON request -> immutable acquisition, never data ready."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.ingestion.acquisition import (
    acquire_dataset,
    list_acquisitions,
    run_worker,
)
from backend.app.schemas.acquisition import AcquisitionRequest
from backend.app.storage.product_common import ProductError, contained, read_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", help="Project-relative JSON request file")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List completed local acquisitions without contacting providers",
    )
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.worker:
        run_worker(Path(args.worker), root)
        return 0
    try:
        if args.list:
            if args.request:
                parser.error("--list does not accept a request")
            result = [
                {
                    "acquisition_id": item.acquisition_id,
                    "source_id": item.source_id,
                    "dataset_id": item.dataset_id,
                    "status": item.status,
                    "data_mode": item.data_mode,
                }
                for item in list_acquisitions(root)
            ]
        else:
            if not args.request:
                parser.error("Supply a request JSON file or --list")
            request = AcquisitionRequest.model_validate(
                read_json(contained(root, args.request), 65536)
            )
            item = acquire_dataset(request, root)
            result = {
                "acquisition_id": item.acquisition_id,
                "source_id": item.source_id,
                "dataset_id": item.dataset_id,
                "status": item.status,
                "data_mode": item.data_mode,
                "size_bytes": item.input_file.size_bytes,
                "sha256": item.input_file.sha256,
            }
        print(json.dumps({"schema_version": 1, "result": result}, indent=2))
        return 0
    except (ProductError, ValidationError, OSError, ValueError) as error:
        code = (
            error.code
            if isinstance(error, ProductError)
            else "invalid_acquisition_request"
        )
        print(json.dumps({"schema_version": 1, "status": "not_acquired", "code": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
