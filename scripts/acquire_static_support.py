"""Explicit bounded static-data acquisition, isolated from API/startup."""

import argparse
import json
import subprocess
import sys

from backend.app.ingestion.registry import PROJECT_ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default="m_35e4c0ab33c1469a334ca837")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.worker:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.acquire_static_support",
                    "--worker",
                    "--model-id",
                    args.model_id,
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                timeout=180,
            )
            if len(result.stdout) > 65536 or len(result.stderr) > 65536:
                raise ValueError("output_limit")
            sys.stdout.buffer.write(result.stdout)
            sys.stderr.buffer.write(result.stderr)
            return result.returncode
        except (subprocess.TimeoutExpired, ValueError, OSError):
            print(json.dumps({"error": "static_worker_not_completed"}), file=sys.stderr)
            return 2
    from backend.app.ingestion.static_support import acquire_static
    from backend.app.storage.product_common import ProductError

    try:
        result = acquire_static(PROJECT_ROOT, args.model_id)
        print(json.dumps(result, allow_nan=False))
        return 0  # Acquisition only, never matched pairs.
    except Exception as error:
        code = (
            error.code
            if isinstance(error, ProductError)
            else "static_acquisition_failed"
        )
        print(
            json.dumps(
                {
                    "error": {
                        "code": code,
                        "message": (
                            "Static acquisition did not complete; "
                            "any private stage is unpublished."
                        ),
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
