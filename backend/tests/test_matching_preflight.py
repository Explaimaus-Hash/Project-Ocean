"""Strict matching QC and operator-only CLI checks on synthetic inputs."""

import json

import pytest
from test_quantities import collection as _quantity_collection
from test_quantities import evidence

from backend.app.comparison.policy import assess_policy
from backend.app.comparison.preflight import strict_argo_issues
from backend.app.processing.quantities import derive_quantities
from backend.app.schemas.matching_policy import MatchingContext, MatchingPolicy
from backend.app.schemas.observations import ObservationCollection
from backend.app.schemas.quantities import QuantityResult
from backend.app.storage.product_common import ProductError
from scripts import check_matching_policy as cli

quantity_collection = _quantity_collection


def policy(**changes):
    return MatchingPolicy.model_validate(
        {
            "model_id": "m_" + "1" * 24,
            "collection_id": "o_" + "2" * 24,
            "acquisition_id": "a_" + "3" * 24,
            "data_mode": "synthetic",
            "quantity": "practical_salinity",
            **changes,
        }
    )


def row_pair(collection, name=None, **changes):
    data = collection.model_dump(mode="json")
    for sample in data["samples"]:
        for value in sample["values"].values():
            value["adjusted_qc"] = "1"
    if name is not None:
        data["samples"][0]["values"][name].update(changes)
    checked = ObservationCollection.model_validate(data)
    result = derive_quantities(checked, evidence(checked)).results[0]
    return checked.samples[0], result


def test_strict_delayed_qc1_preserves_original(quantity_collection):
    before = quantity_collection.model_dump_json()
    sample, result = row_pair(quantity_collection)
    assert strict_argo_issues(sample, result, policy()) == ()
    assert quantity_collection.model_dump_json() == before


@pytest.mark.parametrize("mode", ["A", "R"])
def test_strict_delayed_mode_required(quantity_collection, mode):
    sample, result = row_pair(quantity_collection, "PSAL", data_mode=mode)
    assert "PSAL_delayed_mode_required" in strict_argo_issues(sample, result, policy())


def test_qc2_is_not_strict_qc1(quantity_collection):
    sample, result = row_pair(quantity_collection, "PSAL", adjusted_qc="2")
    assert not result.salinity_exclusions
    assert "PSAL_adjusted_qc1_required" in strict_argo_issues(sample, result, policy())


@pytest.mark.parametrize("error,missing", [(None, True), (0, False)])
def test_missing_error_is_not_zero(quantity_collection, error, missing):
    sample, result = row_pair(quantity_collection, "PSAL", adjusted_error=error)
    assert (
        "PSAL_adjusted_error_missing" in strict_argo_issues(sample, result, policy())
    ) == missing


@pytest.mark.parametrize("error,rejected", [(20, False), (20.000001, True)])
def test_pressure_error_boundary(quantity_collection, error, rejected):
    sample, result = row_pair(quantity_collection, "PRES", adjusted_error=error)
    assert (
        "pressure_error_above_20_dbar" in strict_argo_issues(sample, result, policy())
    ) == rejected


@pytest.mark.parametrize(
    "field,value", [("sample_id", "s_" + "9" * 24), ("source_sample_index", 999)]
)
def test_result_identity_mismatch(quantity_collection, field, value):
    sample, result = row_pair(quantity_collection)
    data = result.model_dump(mode="json")
    data[field] = value
    result = QuantityResult.model_validate(data)
    assert strict_argo_issues(sample, result, policy()) == ("sample_identity_mismatch",)


def test_parameter_original_mismatch(quantity_collection):
    sample, result = row_pair(quantity_collection)
    _, other = row_pair(quantity_collection, "PSAL", adjusted_error=0.2)
    assert "PSAL_provenance_mismatch" in strict_argo_issues(sample, other, policy())
    assert not strict_argo_issues(sample, result, policy())


def test_salinity_does_not_require_temperature_qc(quantity_collection):
    sample, result = row_pair(quantity_collection, "TEMP", adjusted_qc="2")
    assert not strict_argo_issues(sample, result, policy())
    temperature = policy(quantity="potential_temperature_0_dbar_ITS90_C")
    assert "TEMP_adjusted_qc1_required" in strict_argo_issues(
        sample, result, temperature
    )


def blocked_report(selected):
    context = MatchingContext(
        model_id=selected.model_id,
        collection_id=selected.collection_id,
        acquisition_id=selected.acquisition_id,
        data_mode=selected.data_mode,
        quantity=selected.quantity,
        model_manifest_sha256="1" * 64,
        collection_file_sha256="2" * 64,
        collection_canonical_sha256="3" * 64,
        client_input_sha256="4" * 64,
        provider_input_sha256="5" * 64,
        sample_count=1,
        strict_qc_eligible_count=1,
        quantity_eligible_count=1,
        joint_eligible_count=1,
        source_time_indices=(0,),
        source_time_labels=("2024-01-01T00:00:00Z",),
    )
    return assess_policy(selected, context)


@pytest.fixture
def cli_policy(tmp_path, monkeypatch):
    path = tmp_path / "policy.yaml"
    path.write_text(policy().model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    return path


def test_cli_blocked_is_exit_three_json(cli_policy, monkeypatch, capsys):
    before = cli_policy.read_bytes()
    monkeypatch.setattr(
        cli, "local_policy_preflight", lambda root, p: blocked_report(p)
    )
    assert cli.main(["--policy", "policy.yaml"]) == 3
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["status"] == "blocked"
    assert report["matched_pair_count"] == 0
    assert report["overlap_status"] == "not_evaluated"
    assert captured.err == ""
    assert cli_policy.read_bytes() == before


def test_cli_safe_product_error(cli_policy, monkeypatch, capsys):
    def fail(root, selected):
        raise ProductError("test_block", "PRIVATE_LOCAL_PATH")

    monkeypatch.setattr(cli, "local_policy_preflight", fail)
    assert cli.main(["--policy", "policy.yaml"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "test_block"
    assert "PRIVATE_LOCAL_PATH" not in captured.err


@pytest.mark.parametrize(
    "text",
    ["[unterminated", "!!python/object/apply:os.system []", "unknown: PRIVATE_VALUE"],
)
def test_cli_invalid_yaml_safe(cli_policy, monkeypatch, capsys, text):
    cli_policy.write_text(text, encoding="utf-8")
    monkeypatch.setattr(
        cli, "local_policy_preflight", lambda *_: pytest.fail("must not run")
    )
    assert cli.main(["--policy", "policy.yaml"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "invalid_matching_policy_input"
    assert "PRIVATE_VALUE" not in captured.err


def test_cli_private_path_escape(cli_policy, monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "local_policy_preflight", lambda *_: pytest.fail("must not run")
    )
    assert cli.main(["--policy", "../outside.yaml"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "outside.yaml" not in captured.err
    assert json.loads(captured.err)["error"]["code"]


def test_cli_policy_changed_is_not_reported(cli_policy, monkeypatch, capsys):
    before = cli.describe_file(cli_policy, 16384)
    after = type(before).model_validate(
        {**before.model_dump(), "modified_ns": before.modified_ns + 1}
    )
    checks = iter((before, after))
    monkeypatch.setattr(cli, "describe_file", lambda *_: next(checks))
    monkeypatch.setattr(
        cli, "local_policy_preflight", lambda root, p: blocked_report(p)
    )
    assert cli.main(["--policy", "policy.yaml"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "policy_changed"
