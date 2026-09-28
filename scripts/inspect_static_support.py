"""Read-only local static-support inspection; never downloads or matches."""

import argparse
import json
import sys

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.storage.product_common import ProductError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-id", default="b_b18353b728b66639c7787d55")
    parser.add_argument("--model-id", default="m_35e4c0ab33c1469a334ca837")
    args = parser.parse_args(argv)
    try:
        from backend.app.comparison.static_reader import read_static_support

        snapshot = read_static_support(PROJECT_ROOT, args.support_id, args.model_id)
        result = {
            "schema_version": 1,
            "status": snapshot.status,
            "support_id": snapshot.support_id,
            "model_id": snapshot.manifest.model_id,
            "data_mode": snapshot.manifest.data_mode,
            "manifest_sha256": snapshot.manifest_file.sha256,
            "subset_sha256": snapshot.manifest.subset.sha256,
            "source_object_count": len(snapshot.manifest.source_read_set),
            "mask_value_count": len(snapshot.mask),
            "model_depth_to_source_elevation_index": (
                snapshot.model_depth_to_source_elevation_index
            ),
            "checks": snapshot.manifest.checks.model_dump(),
            "scientific_support_status": snapshot.scientific_support_status,
            "comparison_ready": False,
        }
        print(json.dumps(result, allow_nan=False))
        return 0  # Local structural verification only; not matching readiness.
    except Exception as error:
        code = error.code if isinstance(error, ProductError) else "invalid_static_input"
        print(
            json.dumps(
                {
                    "error": {
                        "code": code,
                        "message": "Local static verification did not complete.",
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
