"""Prepare one local acquired Copernicus selection; no download or HTTP service."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_model import prepare_model
from backend.app.schemas.models import ModelPreparationRequest
from backend.app.storage.product_common import ProductError, read_json, stat_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        path = Path(args.request)
        stat_file(path, 16384)
        request = ModelPreparationRequest.model_validate(read_json(path, 16384))
        result = prepare_model(request, PROJECT_ROOT)
        axes = result.identity.axes
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "model_id": result.model_id,
                    "status": result.status,
                    "variables": list(request.variables),
                    "shape": [
                        len(axes.times),
                        len(axes.depth_m),
                        len(axes.latitude),
                        len(axes.longitude),
                    ],
                    "scientific_bytes": result.scientific_file.size_bytes,
                    "comparison_ready": False,
                    "api_serving": False,
                }
            )
        )
        return 0
    except (ValidationError, ValueError):
        code = "invalid_request"
    except ProductError as error:
        code = error.code
    print(
        json.dumps(
            {"error": {"code": code, "message": "Model preparation was not completed."}}
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
