"""Read-only exploratory replay/API acceptance; needs development dependencies.

No publication, downloads or source edits. Timings cover a sequential in-process
client, not a browser, cold disk, concurrent users or deployment readiness.
"""

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.storage.product_common import ProductError, describe_file


def _require(condition: bool) -> None:
    if not condition:
        raise ProductError("verification_failed", "Comparison acceptance check failed.")


def _request(client, url, expected=200, **kwargs):
    response = client.get(url, **kwargs)
    _require(response.status_code == expected)
    _require(response.headers.get("cache-control") == "no-store")
    _require(len(response.content) <= 2097152)
    return response


def _pages(client, prefix, expected, matched, page_size):
    from backend.app.schemas.comparison_api import ComparisonPage

    selected = [
        row for row in expected.samples if matched is None or row.matched == matched
    ]
    received, offset, pages = [], 0, 0
    while True:
        params = {"offset": offset, "limit": page_size}
        if matched is not None:
            params["matched"] = str(matched).lower()
        page = ComparisonPage.model_validate(
            _request(client, prefix + "/samples", params=params).json()
        )
        _require(page.metadata == expected.metadata)
        _require(page.offset == offset and page.limit == page_size)
        _require(page.matched == matched and page.total == len(selected))
        _require(list(page.samples) == selected[offset : offset + page_size])
        received.extend(page.samples)
        pages += 1
        next_offset = offset + len(page.samples)
        wanted = next_offset if next_offset < len(selected) else None
        _require(page.next_offset == wanted)
        if wanted is None:
            break
        _require(wanted > offset and pages <= 1000)
        offset = wanted
    _require(received == selected)
    return pages


def verify(
    root: Path,
    identifier: str,
    *,
    policy_path: str = "config/comparison.yaml",
    support_id: str = "b_b18353b728b66639c7787d55",
    page_size: int = 100,
) -> dict:
    """Replay authenticated inputs and check an already published snapshot.

    This is an operator consistency test, not an independent scientific method.
    API validation reuses the established public projection contract deliberately.
    """
    import yaml
    from fastapi.testclient import TestClient

    from backend.app.comparison.metrics import (
        execute_exploratory_metrics,
        serialize_metrics,
    )
    from backend.app.config import Settings
    from backend.app.main import create_app
    from backend.app.processing.prepare_model import private_path
    from backend.app.schemas.comparison_api import ComparisonCatalogue, comparison_id
    from backend.app.schemas.matching_policy import MatchingPolicy
    from backend.app.storage.comparisons import ComparisonStore, _project

    _require(type(page_size) is int and page_size in (5, 100, 500))
    root = root.resolve()
    store = ComparisonStore(root)
    paths = [
        store._path(identifier, name)
        for name in ("manifest.json", "result.json", "report.json")
    ]
    before = [describe_file(path, 2097152) for path in paths]
    policy_file = private_path(root, policy_path)
    policy_before = describe_file(policy_file, 16384)
    with policy_file.open("rb") as stream:
        raw = stream.read(16385)
    _require(len(raw) <= 16384)
    policy = MatchingPolicy.model_validate(yaml.safe_load(raw))
    started = time.perf_counter()
    report = execute_exploratory_metrics(root, policy, support_id)
    replay_seconds = time.perf_counter() - started
    report_bytes = serialize_metrics(report)
    _require(comparison_id(report_bytes) == identifier)
    _require(hashlib.sha256(report_bytes).hexdigest() == before[2].sha256)
    saved = store._snapshot(identifier)
    expected = _project(report, identifier, saved.metadata.prepared_at)
    _require(saved == expected)
    prefix = "/api/v1/comparisons/" + identifier
    settings = Settings(project_root=root, required_product_ids=[], docs_enabled=True)
    with TestClient(create_app(settings)) as client:
        _require(
            _request(client, "/health").json()
            == {"status": "ok", "service": "Project Ocean Backend"}
        )
        # Readiness is deliberately unconfigured, even with a saved comparison.
        _request(client, "/ready", 503)
        catalogue = ComparisonCatalogue.model_validate(
            _request(client, "/api/v1/comparisons").json()
        )
        entries = [e for e in catalogue.comparisons if e.comparison_id == identifier]
        _require(len(entries) == 1 and entries[0].metadata == expected.metadata)
        _require(
            _request(client, prefix).json() == expected.metadata.model_dump(mode="json")
        )
        page_counts = {
            label: _pages(client, prefix, expected, matched, page_size)
            for label, matched in (
                ("all", None),
                ("matched", True),
                ("excluded", False),
            )
        }
        for query in ("limit=501", "offset=-1", "matched=invalid"):
            response = _request(client, prefix + "/samples?" + query, 422)
            _require(response.json()["error"]["code"] == "invalid_request")
        absent = _request(client, prefix + "/samples?offset=5000").json()
        _require(absent["samples"] == [] and absent["next_offset"] is None)
        frame_url = prefix + "/samples?limit=100"
        started = time.perf_counter()
        first = _request(client, frame_url)
        first_seconds = time.perf_counter() - started
        durations = []
        for _ in range(30):
            started = time.perf_counter()
            response = _request(client, frame_url)
            durations.append(time.perf_counter() - started)
            _require(response.content == first.content)
    _require(before == [describe_file(path, 2097152) for path in paths])
    _require(describe_file(policy_file, 16384) == policy_before)
    return {
        "schema_version": 1,
        "status": "local_exploratory_consistency_verified",
        "comparison_id": identifier,
        "data_mode": report.data_mode,
        "comparison_status": report.status,
        "comparison_ready": False,
        "independent_validation": False,
        "summary": report.summary.model_dump(mode="json"),
        "strict_blockers": list(report.matching.strict_assessment.blockers),
        "published_files_and_policy_unchanged": True,
        "page_size": page_size,
        "verified_pages": page_counts,
        "checks": [
            "health",
            "unconfigured_readiness",
            "catalogue",
            "metadata",
            "all_rows",
            "filtered_rows",
            "invalid_queries",
            "beyond_last_page",
            "repeat_identity",
        ],
        "platform": platform.platform(),
        "python": platform.python_version(),
        "measurement_scope": "sequential_in_process_not_browser_or_cold_disk",
        "replay_seconds": replay_seconds,
        "first_measured_page_seconds": first_seconds,
        "warm_repetitions": len(durations),
        "warm_page_p95_seconds": sorted(durations)[
            math.ceil(0.95 * len(durations)) - 1
        ],
        "page_response_bytes": len(first.content),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_id")
    parser.add_argument("--accept-assumptions", action="store_true", required=True)
    parser.add_argument("--policy", default="config/comparison.yaml")
    parser.add_argument("--support-id", default="b_b18353b728b66639c7787d55")
    parser.add_argument("--page-size", type=int, choices=(5, 100, 500), default=100)
    args = parser.parse_args(argv)
    try:
        result = verify(
            PROJECT_ROOT,
            args.comparison_id,
            policy_path=args.policy,
            support_id=args.support_id,
            page_size=args.page_size,
        )
        print(json.dumps(result, allow_nan=False))
        return 0
    except Exception:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "verification_failed",
                        "message": "Comparison verification did not complete.",
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
