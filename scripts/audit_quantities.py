"""Print a verified local quantity report; no data writes, downloads or matches."""

import argparse
import json
import sys

from pydantic import ValidationError

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.quantity_audit import audit_quantities
from backend.app.schemas.quantities import QuantityReport
from backend.app.storage.product_common import ProductError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--acquisition-id", required=True)
    parser.add_argument("--model-id", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_quantities(
            PROJECT_ROOT, args.collection_id, args.acquisition_id, args.model_id
        )
        report = QuantityReport.model_validate_json(report.model_dump_json())
        payload = (report.model_dump_json() + "\n").encode()
        if len(payload) > 16 * 1024 * 1024:
            raise ValueError("report_limit")
        sys.stdout.write(payload.decode())
        return 0
    except ProductError as error:
        code = error.code
    except (
        ValidationError,
        ValueError,
        TypeError,
        OSError,
        KeyError,
        AttributeError,
        IndexError,
        RuntimeError,
    ):
        code = "invalid_quantity_source"
    print(
        json.dumps(
            {"error": {"code": code, "message": "Quantity report was not produced."}}
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
