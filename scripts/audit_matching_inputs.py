"""Read-only native model/adjusted Argo verification; no matching or downloads."""

import argparse
import json
import sys

from backend.app.comparison.local import audit_local_matching, serialize_local_audit
from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_model import private_path
from backend.app.schemas.matching_policy import MatchingPolicy
from backend.app.storage.product_common import ProductError, describe_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/comparison.yaml")
    args = parser.parse_args(argv)
    import yaml

    try:
        path = private_path(PROJECT_ROOT, args.policy)
        before = describe_file(path, 16384)
        with path.open("r", encoding="utf-8") as stream:
            raw = stream.read(16385)
        if len(raw.encode()) > 16384:
            raise ValueError("policy_limit")
        policy = MatchingPolicy.model_validate(yaml.safe_load(raw))
        report = audit_local_matching(PROJECT_ROOT, policy)
        if describe_file(path, 16384) != before:
            raise ProductError("policy_changed", "Policy changed during the audit.")
        sys.stdout.write(serialize_local_audit(report).decode())
        return 3  # Verified inputs, unresolved matching support; never success pairs.
    except ProductError as error:
        code = error.code
    except (
        ValueError,
        TypeError,
        OSError,
        KeyError,
        AttributeError,
        IndexError,
        RuntimeError,
        yaml.YAMLError,
    ):
        code = "invalid_matching_audit_input"
    print(
        json.dumps(
            {
                "error": {
                    "code": code,
                    "message": "Matching input verification was not completed.",
                }
            }
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
