"""Read-only model-minus-observation metrics with explicit exploratory assumptions."""

import argparse
import json
import sys

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.storage.product_common import ProductError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/comparison.yaml")
    parser.add_argument("--support-id", default="b_b18353b728b66639c7787d55")
    parser.add_argument("--accept-assumptions", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        import yaml

        from backend.app.comparison.metrics import (
            execute_exploratory_metrics,
            serialize_metrics,
        )
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
        report = execute_exploratory_metrics(PROJECT_ROOT, policy, args.support_id)
        payload = serialize_metrics(report)
        if describe_file(path, 16384) != before:
            raise ValueError("Policy changed")
        sys.stdout.write(payload.decode())
        return 0 if report.status == "evaluated" else 3
    except Exception as error:
        code = (
            error.code
            if isinstance(error, ProductError)
            else "invalid_exploratory_metrics"
        )
        print(
            json.dumps(
                {
                    "error": {
                        "code": code,
                        "message": "Exploratory metrics did not complete.",
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
