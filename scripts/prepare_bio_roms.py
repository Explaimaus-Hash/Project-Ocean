"""Operator-only bounded preparation of an already verified local V2 file."""

import argparse
import json
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_bio_roms import prepare_product
from backend.app.schemas.products import PreparationRequest, Region
from backend.app.storage.product_common import ProductError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default="incois_bio_roms_v2")
    parser.add_argument("--variables", nargs="+", required=True)
    for name in ("west", "east", "south", "north"):
        parser.add_argument(f"--{name}", type=float, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args(argv)
    try:
        request = PreparationRequest(
            dataset_id=args.dataset_id,
            variables=args.variables,
            region=Region(
                west=args.west, east=args.east, south=args.south, north=args.north
            ),
            start_date=args.start,
            end_date=args.end,
        )
        manifest = prepare_product(request, PROJECT_ROOT)
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "prepared",
                    "product_id": manifest.product_id,
                    "dataset_id": manifest.dataset_id,
                    "data_mode": manifest.data_mode,
                    "variables": list(manifest.variables),
                    "shape": [
                        len(manifest.times),
                        len(manifest.latitude),
                        len(manifest.longitude),
                    ],
                    "times": manifest.times,
                    "preview_stride": manifest.preview_stride,
                    "scientific_bytes": manifest.scientific_file.size_bytes,
                    "preview_bytes": manifest.preview_file.size_bytes,
                    "capabilities": manifest.capabilities.model_dump(),
                }
            )
        )
        return 0
    except ValidationError:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "invalid_selection",
                        "message": "Selection does not satisfy preparation limits.",
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2
    except ProductError as error:
        print(
            json.dumps({"error": {"code": error.code, "message": error.message}}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
