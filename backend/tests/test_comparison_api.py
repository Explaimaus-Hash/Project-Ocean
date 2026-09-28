"""Prepared comparison storage and public HTTP tests; no live provider access."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.comparison import metrics
from backend.app.comparison.exploratory import match_exploratory
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.schemas.comparison_api import ComparisonPage, ComparisonSnapshot
from backend.app.schemas.matching import NativeMatchingInput
from backend.app.storage import comparisons as mod
from backend.app.storage.comparisons import ComparisonStore
from backend.app.storage.product_common import ProductError, describe_file
from backend.tests.test_comparison_metrics import matching as matching
from backend.tests.test_comparison_metrics import reject_rows
from backend.tests.test_comparison_metrics import report as report
from backend.tests.test_exploratory_matching import example as example
from backend.tests.test_matching_engine import collection as collection
from backend.tests.test_matching_execution import integrated as integrated
from backend.tests.test_matching_local import audit_inputs as audit_inputs
from backend.tests.test_matching_local import pipeline as pipeline
from scripts import prepare_comparison as cli


@pytest.fixture
def prepared(tmp_path, report):
    store = ComparisonStore(tmp_path)
    metadata = store.publish(report)
    return store, metadata["comparison_id"]


def client_for(root):
    return TestClient(create_app(Settings(project_root=root)))


def test_publication_reuse_preserves_bytes_stats_and_raw_report(prepared, report):
    store, cid = prepared
    paths = [
        store._path(cid, n) for n in ("report.json", "result.json", "manifest.json")
    ]
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
    assert (
        json.loads(before[0][0])["matching"]["strict_assessment"]["status"] == "blocked"
    )
    assert store.publish(report)["comparison_id"] == cid
    assert before == [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
    assert not (store.root / "data/comparisons/.publish.lock").exists()
    assert len(list((store.root / "data/comparisons").iterdir())) == 1
    assert (
        store.metadata(cid)["snapshot_semantics"]
        == "immutable_result_not_live_source_status"
    )


def test_empty_catalogue_and_missing_result_never_create_data(tmp_path):
    with client_for(tmp_path) as client:
        assert client.get("/api/v1/comparisons").json() == {
            "schema_version": 1,
            "comparisons": [],
        }
        response = client.get("/api/v1/comparisons/c_" + "0" * 24)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_prepared"
        assert response.headers["cache-control"] == "no-store"
    assert not (tmp_path / "data").exists()


def test_routes_are_read_only_and_public_projection_omits_private_evidence(
    prepared, monkeypatch
):
    store, cid = prepared
    original_open = Path.open

    def only_public(path, *args, **kwargs):
        assert path.name != "report.json", "HTTP must not read private metrics report"
        assert "data/comparisons" in path.as_posix(), "HTTP must not read source files"
        return original_open(path, *args, **kwargs)

    def forbidden(*a, **k):
        pytest.fail("HTTP invoked processing/publication")

    with client_for(store.root) as client:
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", only_public)
            patch.setattr(metrics, "execute_exploratory_metrics", forbidden)
            patch.setattr(metrics, "execute_exploratory", forbidden)
            patch.setattr(ComparisonStore, "publish", forbidden)
            for route in ("", f"/{cid}", f"/{cid}/samples"):
                response = client.get("/api/v1/comparisons" + route)
                assert response.status_code == 200
                assert response.headers["cache-control"] == "no-store"
                for private in (
                    "matching_sha256",
                    "strict_assessment",
                    "manifest_file",
                    "modified_ns",
                    "size_bytes",
                    "verification_evidence",
                    "static_manifest_sha256",
                    "source_filename",
                ):
                    assert private not in response.text
            for method in ("post", "put", "delete", "patch"):
                assert (
                    getattr(client, method)(f"/api/v1/comparisons/{cid}").status_code
                    == 405
                )
            assert client.get("/health").status_code == 200


def test_pagination_filter_values_and_assurance(prepared):
    store, cid = prepared
    with client_for(store.root) as client:
        route = f"/api/v1/comparisons/{cid}/samples"
        response = client.get(route, params={"limit": 2})
        body = response.json()
        assert body["total"] == 6 and len(body["samples"]) == 2
        assert body["next_offset"] == 2
        assert body["metadata"]["summary"]["bias"] == -0.25
        assert body["metadata"]["assurance"] == "exploratory_assumptions"
        assert not body["metadata"]["comparison_ready"]
        assert body["samples"][0]["model_minus_observation"] == -0.25
        assert body["samples"][0]["quantity_units"] == "1 (PSS-78)"
        assert client.get(route, params={"matched": "false"}).json()["samples"] == []
        last = client.get(route, params={"offset": 5, "limit": 2}).json()
        assert len(last["samples"]) == 1 and last["next_offset"] is None
        beyond = client.get(route, params={"offset": 5000}).json()
        assert beyond["samples"] == [] and beyond["next_offset"] is None


def test_exclusions_and_partial_statistics_survive_publication(tmp_path, matching):
    report = metrics.summarize_exploratory(
        reject_rows(matching, [0, 2], "support_unresolved", True)
    )
    store = ComparisonStore(tmp_path)
    cid = store.publish(report)["comparison_id"]
    page = ComparisonPage.model_validate(store.samples(cid, matched=False, limit=1))
    assert page.total == 2 and page.next_offset == 1
    assert page.metadata.status == "partially_blocked"
    assert page.metadata.summary.matched_pair_count == 4
    assert page.samples[0].model_minus_observation is None
    assert page.samples[0].exclusions == ("support_unresolved",)


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 0},
        {"limit": 501},
        {"offset": -1},
        {"offset": 5001},
        {"matched": "PRIVATE_SECRET"},
    ],
)
def test_bad_query_sanitized(prepared, query):
    store, cid = prepared
    with client_for(store.root) as client:
        response = client.get(f"/api/v1/comparisons/{cid}/samples", params=query)
        assert response.status_code == 422 and "PRIVATE_SECRET" not in response.text
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("identifier", ["bad", "../private", "c_" + "G" * 24])
def test_identifier_is_contained(tmp_path, identifier):
    with pytest.raises(ProductError):
        ComparisonStore(tmp_path).metadata(identifier)


@pytest.mark.parametrize(
    "kind", ["result", "manifest", "missing", "rehashed_residual", "rehashed_identity"]
)
def test_corruption_never_serves_success(prepared, kind):
    store, cid = prepared
    result_path = store._path(cid, "result.json")
    manifest_path = store._path(cid, "manifest.json")
    if kind == "missing":
        result_path.unlink()
    elif kind == "manifest":
        manifest_path.write_text("PRIVATE_SECRET")
    elif kind == "result":
        result_path.write_text("PRIVATE_SECRET")
    else:
        result = json.loads(result_path.read_bytes())
        if kind == "rehashed_residual":
            result["samples"][0]["model_minus_observation"] = 999
        else:
            result["metadata"]["comparison_id"] = "c_" + "0" * 24
        result_path.write_text(json.dumps(result))
        manifest = json.loads(manifest_path.read_bytes())
        manifest["result_file"] = describe_file(
            result_path, mod.MAX_RESULT_BYTES
        ).model_dump()
        manifest_path.write_text(json.dumps(manifest))
    with client_for(store.root) as client:
        response = client.get(f"/api/v1/comparisons/{cid}/samples")
        assert response.status_code == 409
        assert (
            "PRIVATE_SECRET" not in response.text
            and str(store.root) not in response.text
        )


def test_same_size_mtime_tampering_is_detected_by_hash(prepared):
    import os

    store, cid = prepared
    path = store._path(cid, "result.json")
    stat = path.stat()
    original = path.read_bytes()
    changed = original.replace(b'"bias":-0.25', b'"bias":-0.35')
    assert changed != original and len(changed) == len(original)
    path.write_bytes(changed)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ProductError, match="changed"):
        store.metadata(cid)


def test_catalogue_retains_unavailable_entries_and_ignores_stages(prepared):
    store, cid = prepared
    (store.root / "data/comparisons/.comparison_incomplete").mkdir()
    store._path(cid, "result.json").unlink()
    entries = store.catalogue()["comparisons"]
    assert len(entries) == 1 and entries[0]["availability"] == "unavailable"
    assert "metadata" not in entries[0]


def test_publisher_lock_does_not_remove_another_operators_lock(tmp_path, report):
    directory = tmp_path / "data/comparisons"
    directory.mkdir(parents=True)
    lock = directory / ".publish.lock"
    lock.write_text("owner")
    with pytest.raises(ProductError) as error:
        ComparisonStore(tmp_path).publish(report)
    assert error.value.code == "comparison_busy" and lock.read_text() == "owner"


def test_publication_failure_leaves_no_visible_partial(tmp_path, report, monkeypatch):
    original = Path.rename

    def fail(path, target):
        if path.name.startswith(".comparison_"):
            raise OSError("PRIVATE_SECRET")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", fail)
    store = ComparisonStore(tmp_path)
    with pytest.raises(ProductError) as error:
        store.publish(report)
    assert error.value.code == "publication_failed" and "PRIVATE_SECRET" not in str(
        error.value
    )
    assert store.catalogue()["comparisons"] == []
    assert list((tmp_path / "data/comparisons").iterdir()) == []


def test_conflicting_reuse_does_not_overwrite(prepared, report):
    store, cid = prepared
    path = store._path(cid, "report.json")
    path.write_text("preserve me")
    with pytest.raises(ProductError):
        store.publish(report)
    assert path.read_text() == "preserve me"


def test_capacity_and_output_bounds(tmp_path, report, monkeypatch):
    store = ComparisonStore(tmp_path)
    monkeypatch.setattr(mod, "MAX_RESULTS", 0)
    with pytest.raises(ProductError):
        store.publish(report)
    monkeypatch.setattr(mod, "MAX_RESULTS", 32)
    monkeypatch.setattr(mod, "MAX_RESULT_BYTES", 1)
    with pytest.raises(ProductError) as error:
        store.publish(report)
    assert error.value.http_status == 413
    assert not (tmp_path / "data/comparisons/.publish.lock").exists()


def test_prepared_snapshot_rejects_false_assurance(prepared):
    store, cid = prepared
    d = json.loads(store._path(cid, "result.json").read_bytes())
    d["metadata"]["comparison_ready"] = True
    with pytest.raises(ValueError):
        ComparisonSnapshot.model_validate(d)


def test_cli_explicit_publication_and_reuse(
    tmp_path, report, example, monkeypatch, capsys
):
    path = tmp_path / "policy.yaml"
    path.write_text(example[0].policy.model_dump_json())
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: report)
    with pytest.raises(SystemExit):
        cli.main(["--policy", "policy.yaml"])
    capsys.readouterr()
    for _ in range(2):
        assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 0
        metadata = json.loads(capsys.readouterr().out)
        assert metadata["summary"]["matched_pair_count"] == 6
    assert len(ComparisonStore(tmp_path).catalogue()["comparisons"]) == 1
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    path.write_text("private: PRIVATE_SECRET")
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 2
    output = capsys.readouterr()
    assert not output.out and "PRIVATE_SECRET" not in output.err


@pytest.mark.parametrize("state", ["empty", "blocked"])
def test_empty_and_blocked_public_results_keep_null_metrics(
    tmp_path, matching, example, state
):
    if state == "empty":
        result = metrics.summarize_exploratory(reject_rows(matching, range(6)))
    else:
        request, static = example
        data = request.model_dump()
        data["context"]["adjusted_depth_alignment"] = {"status": "unresolved"}
        result = metrics.summarize_exploratory(
            match_exploratory(NativeMatchingInput.model_validate(data), static)
        )
    store = ComparisonStore(tmp_path)
    cid = store.publish(result)["comparison_id"]
    with client_for(tmp_path) as client:
        response = client.get(f"/api/v1/comparisons/{cid}/samples?matched=true")
        assert response.status_code == 200
        page = response.json()
        assert page["samples"] == [] and page["total"] == 0
        assert page["metadata"]["summary"]["bias"] is None
        assert page["metadata"]["summary"]["rmse"] is None
        assert page["metadata"]["status"] == (
            "blocked" if state == "blocked" else "evaluated"
        )


def test_catalogue_scan_is_bounded(tmp_path, monkeypatch):
    directory = tmp_path / "data/comparisons"
    directory.mkdir(parents=True)
    for i in range(3):
        (directory / f".unused_{i}").mkdir()
    monkeypatch.setattr(mod, "MAX_DIRECTORY_ENTRIES", 2)
    with client_for(tmp_path) as client:
        response = client.get("/api/v1/comparisons")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "catalogue_limit"


def test_invalid_public_projection_is_sanitized(prepared, monkeypatch):
    store, cid = prepared
    monkeypatch.setattr(
        ComparisonStore, "metadata", lambda *a: {"private": "PRIVATE_SECRET"}
    )
    with client_for(store.root) as client:
        response = client.get(f"/api/v1/comparisons/{cid}")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "invalid_response"
        assert "PRIVATE_SECRET" not in response.text


@pytest.mark.parametrize("code", [5, 32, 33])
@pytest.mark.parametrize("persistent", [False, True])
def test_windows_rename_retry_is_bounded(
    tmp_path, report, monkeypatch, code, persistent
):
    original = Path.rename
    calls = []
    sleeps = []

    def rename(path, target):
        if path.name.startswith(".comparison_"):
            calls.append((path, target))
            if persistent or len(calls) == 1:
                error = PermissionError(13, "Synthetic Windows denial")
                error.winerror = code
                raise error
        return original(path, target)

    monkeypatch.setattr(Path, "rename", rename)
    monkeypatch.setattr(mod.time, "sleep", sleeps.append)
    store = ComparisonStore(tmp_path)
    if persistent:
        with pytest.raises(ProductError) as error:
            store.publish(report)
        assert error.value.code == "publication_failed"
        assert len(calls) == 4 and sleeps == [0.05, 0.1, 0.2]
        assert store.catalogue()["comparisons"] == []
    else:
        assert store.publish(report)["summary"]["matched_pair_count"] == 6
        assert len(calls) == 2 and sleeps == [0.05]
    assert len(set(calls)) == 1  # Retry same already-validated stage/target only.
    assert not (tmp_path / "data/comparisons/.publish.lock").exists()


def test_retry_never_replaces_newly_created_destination(tmp_path, report, monkeypatch):
    targets = []

    def deny(path, target):
        target.mkdir()
        (target / "owner.txt").write_text("other operator")
        targets.append(target)
        error = PermissionError(13, "Synthetic race")
        error.winerror = 5
        raise error

    monkeypatch.setattr(Path, "rename", deny)
    monkeypatch.setattr(mod.time, "sleep", lambda *a: None)
    with pytest.raises(ProductError):
        ComparisonStore(tmp_path).publish(report)
    assert len(targets) == 1
    assert (targets[0] / "owner.txt").read_text() == "other operator"
    assert not (targets[0] / "manifest.json").exists()
