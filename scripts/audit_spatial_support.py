"""Read-only local grid-support diagnostics; never downloads or matches."""

import argparse
import json
import sys

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.storage.product_common import ProductError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-id", default="b_b18353b728b66639c7787d55")
    parser.add_argument("--policy", default="config/comparison.yaml")
    args = parser.parse_args(argv)
    try:
        import yaml

        from backend.app.comparison.spatial_support import audit_spatial_support
        from backend.app.processing.prepare_model import private_path
        from backend.app.schemas.matching_policy import MatchingPolicy
        from backend.app.storage.product_common import describe_file

        path = private_path(PROJECT_ROOT, args.policy)
        before = describe_file(path, 16384)
        with path.open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise ValueError("Policy limit")
        policy = MatchingPolicy.model_validate(yaml.safe_load(raw))
        report = audit_spatial_support(PROJECT_ROOT, policy, args.support_id)
        if describe_file(path, 16384) != before:
            raise ValueError("Policy changed")
        print(json.dumps(report, allow_nan=False))
        return 3  # Valid diagnostics, not real matching readiness.
    except Exception as error:
        code = (
            error.code if isinstance(error, ProductError) else "invalid_spatial_input"
        )
        print(
            json.dumps(
                {"error": {"code": code, "message": "Spatial audit did not complete."}}
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
