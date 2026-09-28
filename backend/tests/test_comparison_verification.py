"""Offline verifier checks; real replay is a separately invoked operator job."""

import json
import socket
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.app.comparison import metrics
from backend.app.storage.comparisons import ComparisonStore
from backend.app.storage.product_common import ProductError
from backend.tests.test_comparison_metrics import matching as matching
from backend.tests.test_comparison_metrics import reject_rows
from backend.tests.test_comparison_metrics import report as report
from backend.tests.test_exploratory_matching import example as example
from backend.tests.test_matching_engine import collection as collection
from backend.tests.test_matching_execution import integrated as integrated
from backend.tests.test_matching_local import audit_inputs as audit_inputs
from backend.tests.test_matching_local import pipeline as pipeline
from scripts import verify_comparison as cli


def prepare(root, report):
    policy = root / "config/comparison.yaml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        yaml.safe_dump(
            report.matching.strict_assessment.policy.model_dump(mode="json")
        ),
        encoding="utf-8",
    )
    return ComparisonStore(root).publish(report)["comparison_id"]


@pytest.fixture
def published(tmp_path, report, monkeypatch):
    identifier = prepare(tmp_path, report)
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: report)
    return tmp_path, identifier


def test_replay_api_paging_no_network_no_writes(published, monkeypatch):
    root, identifier = published
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }
    opened = Path.open
    connect = socket.socket.connect

    def read_only(path, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+")
        return opened(path, mode, *args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail("Verifier attempted network or publication")

    def no_external_network(sock, address):
        # Windows asyncio uses a loopback socket pair for its event-loop wakeup.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return connect(sock, address)
        forbidden()

    monkeypatch.setattr(Path, "open", read_only)
    monkeypatch.setattr(socket.socket, "connect", no_external_network)
    monkeypatch.setattr(ComparisonStore, "publish", forbidden)
    result = cli.verify(root, identifier, page_size=5)
    assert result["data_mode"] == "synthetic"
    assert result["summary"]["matched_pair_count"] == 6
    assert result["summary"]["bias"] == -0.25
    assert result["verified_pages"] == {"all": 2, "matched": 2, "excluded": 1}
    assert result["warm_repetitions"] == 30
    assert result["warm_page_p95_seconds"] >= 0
    assert not result["comparison_ready"] and not result["independent_validation"]
    assert before == {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("partial", [False, True])
def test_zero_pairs_and_partial_are_not_fabricated_success(
    tmp_path, matching, monkeypatch, partial
):
    report = metrics.summarize_exploratory(
        reject_rows(
            matching,
            range(6),
            reason="support_unresolved" if partial else "nearest_cell_masked",
            partial=partial,
        )
    )
    identifier = prepare(tmp_path, report)
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: report)
    result = cli.verify(tmp_path, identifier)
    assert result["summary"]["bias"] is None
    assert result["summary"]["rmse"] is None
    assert result["comparison_status"] == (
        "partially_blocked" if partial else "evaluated"
    )
    assert result["summary"]["excluded_sample_count"] == 6


@pytest.mark.parametrize("name", ["report.json", "result.json", "manifest.json"])
def test_changed_saved_file_rejected(published, name):
    root, identifier = published
    path = root / "data/comparisons" / identifier / name
    path.write_bytes(path.read_bytes() + b"!")
    with pytest.raises((ProductError, ValueError)):
        cli.verify(root, identifier)


def test_missing_snapshot_does_not_prepare(published):
    root, _ = published
    absent = "c_" + "0" * 24
    with pytest.raises(ProductError):
        cli.verify(root, absent)
    assert not (root / "data/comparisons" / absent).exists()


def test_different_replay_rejected(published, matching, monkeypatch):
    root, identifier = published
    report = metrics.summarize_exploratory(reject_rows(matching, [0]))
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: report)
    with pytest.raises(ProductError):
        cli.verify(root, identifier)


def test_policy_changes_during_replay_rejected(published, report, monkeypatch):
    root, identifier = published

    def changed(*args):
        path = root / "config/comparison.yaml"
        path.write_bytes(path.read_bytes() + b"\n")
        return report

    monkeypatch.setattr(metrics, "execute_exploratory_metrics", changed)
    with pytest.raises(ProductError):
        cli.verify(root, identifier)


@pytest.mark.parametrize("change", ["status", "header", "rows", "metadata"])
def test_http_contract_regression_rejected(published, monkeypatch, change):
    root, identifier = published
    get = TestClient.get

    def broken(client, url, *args, **kwargs):
        response = get(client, url, *args, **kwargs)
        if url.endswith("/samples"):
            if change == "status":
                response.status_code = 503
            elif change == "header":
                response.headers.pop("cache-control", None)
            else:
                payload = response.json()
                if change == "rows":
                    payload["samples"] = []
                else:
                    payload["metadata"]["independent_validation"] = True
                response._content = json.dumps(payload).encode()
        return response

    monkeypatch.setattr(TestClient, "get", broken)
    with pytest.raises((ProductError, ValueError)):
        cli.verify(root, identifier)


@pytest.mark.parametrize("page_size", [0, 1, 501, True])
def test_unbounded_page_configuration_rejected(published, page_size):
    with pytest.raises(ProductError):
        cli.verify(*published, page_size=page_size)


def test_cli_opt_in_and_sanitized_error(published, monkeypatch, capsys):
    root, identifier = published
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    with pytest.raises(SystemExit):
        cli.main([identifier])
    capsys.readouterr()
    assert cli.main([identifier, "--accept-assumptions"]) == 0
    assert json.loads(capsys.readouterr().out)["published_files_and_policy_unchanged"]
    assert cli.main(["../private", "--accept-assumptions"]) == 2
    error = capsys.readouterr().err
    assert "../private" not in error and str(root) not in error
    assert json.loads(error)["error"]["code"] == "verification_failed"
