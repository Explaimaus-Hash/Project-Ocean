"""Read-only policy preflight; blocked metadata is not a successful empty match."""

import argparse
import json
import sys

from pydantic import ValidationError

from backend.app.comparison.policy import serialize_policy_assessment
from backend.app.comparison.preflight import local_policy_preflight
from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_model import private_path
from backend.app.schemas.matching_policy import MatchingPolicy
from backend.app.storage.product_common import ProductError, describe_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/comparison.yaml")
    args = parser.parse_args(argv)
    try:
        import yaml

        path = private_path(PROJECT_ROOT, args.policy)
        before = describe_file(path, 16384)
        with path.open("r", encoding="utf-8") as stream:
            data = stream.read(16385)
        if len(data.encode()) > 16384:
            raise ValueError("policy_limit")
        policy = MatchingPolicy.model_validate(yaml.safe_load(data))
        report = local_policy_preflight(PROJECT_ROOT, policy)
        if describe_file(path, 16384) != before:
            raise ProductError("policy_changed", "Policy changed during preflight.")
        sys.stdout.write(serialize_policy_assessment(report).decode())
        return 3 if report.blockers else 0
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
        yaml.YAMLError,
    ):
        code = "invalid_matching_policy_input"
    print(
        json.dumps(
            {
                "error": {
                    "code": code,
                    "message": "Matching policy preflight was not completed.",
                }
            }
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
