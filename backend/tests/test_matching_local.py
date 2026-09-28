"""Offline local matching-input audit contracts; no real files or pair search."""

import hashlib
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_model_preparation import local_model as _local_model
from test_quantities import collection as _collection
from test_quantities import evidence

from backend.app.comparison import local
from backend.app.comparison.model_reader import read_native_field
from backend.app.comparison.policy import assess_policy
from backend.app.processing.prepare_model import prepare_model
from backend.app.processing.quantities import derive_quantities
from backend.app.schemas.matching_local import (
    LocalMatchingAudit,
    NativeFieldVerification,
)
from backend.app.schemas.matching_policy import MatchingContext, MatchingPolicy
from backend.app.schemas.products import ProductFile
from backend.app.storage.product_common import ProductError
from scripts import audit_matching_inputs as cli


@pytest.fixture(scope="module")
def audit_inputs(tmp_path_factory):
    root = tmp_path_factory.mktemp("matching_local")
    with pytest.MonkeyPatch.context() as patch:
        _, _, request = _local_model.__wrapped__(root, patch)
        manifest = prepare_model(request, root)
        field = read_native_field(root, manifest.model_id, "so")
        collection = _collection.__wrapped__(root)
        quantities = derive_quantities(
            collection, evidence(collection, model_identity=manifest.model_id)
        )
    policy = MatchingPolicy(
        model_id=manifest.model_id,
        collection_id=collection.collection_id,
        acquisition_id="a_" + "3" * 24,
        data_mode="synthetic",
        quantity="practical_salinity",
    )
    file = ProductFile(size_bytes=123, modified_ns=1, sha256="2" * 64)
    provider = ProductFile(size_bytes=123, modified_ns=1, sha256="1" * 64)
    context = MatchingContext(
        model_id=policy.model_id,
        collection_id=policy.collection_id,
        acquisition_id=policy.acquisition_id,
        data_mode=policy.data_mode,
        quantity=policy.quantity,
        model_manifest_sha256=field.manifest_file.sha256,
        collection_file_sha256=file.sha256,
        collection_canonical_sha256=hashlib.sha256(
            collection.model_dump_json().encode()
        ).hexdigest(),
        client_input_sha256=collection.input_file.sha256,
        provider_input_sha256=provider.sha256,
        sample_count=len(collection.samples),
        strict_qc_eligible_count=0,
        quantity_eligible_count=0,
        joint_eligible_count=0,
        source_time_indices=manifest.identity.axes.source_time_indices,
        source_time_labels=manifest.identity.axes.times,
    )
    return SimpleNamespace(
        root=root,
        field=field,
        collection=collection,
        quantities=quantities,
        policy=policy,
        context=context,
        file=file,
        provider=provider,
    )


@pytest.fixture
def pipeline(audit_inputs, monkeypatch):
    x = audit_inputs
    monkeypatch.setattr(local, "private_path", lambda root, path: root / path)

    def describe(path, maximum):
        if "data/models" in path.as_posix():
            return {
                "manifest.json": x.field.manifest_file,
                "fields.nc": x.field.manifest.scientific_file,
                "source_metadata.json": x.field.manifest.source_metadata_file,
            }[path.name]
        return {
            "collection.json": x.file,
            "input.nc": x.collection.input_file,
            "provider_input.nc": x.provider,
            "manifest.json": x.file,
        }[path.name]

    monkeypatch.setattr(local, "describe_file", describe)
    monkeypatch.setattr(
        local,
        "local_policy_preflight",
        lambda *args: assess_policy(x.policy, x.context),
    )
    monkeypatch.setattr(local, "read_native_field", lambda *args: x.field)
    monkeypatch.setattr(
        local,
        "ObservationStore",
        lambda *args: SimpleNamespace(collection=lambda cid: x.collection),
    )
    monkeypatch.setattr(local, "audit_quantities", lambda *args: x.quantities)
    return x


@pytest.fixture
def report(pipeline):
    return local.audit_local_matching(pipeline.root, pipeline.policy)


def test_pipeline_audits_without_matching_or_support_promotion(report):
    payload = json.loads(local.serialize_local_audit(report))
    assert payload["matched_pair_count"] == 0
    assert payload["comparison_ready"] is False
    assert payload["overlap_status"] == "not_evaluated"
    assert payload["assessment"]["status"] == "blocked"
    assert (
        payload["assessment"]["context"]["adjusted_depth_alignment"]["status"]
        == "verified_for_input_snapshot"
    )
    assert payload["assessment"]["context"]["time_cells"] == []
    assert "values" not in payload["field"]
    assert report.depth_converted_count + report.depth_rejected_count == len(
        report.adjusted_depth_report.results
    )


@pytest.mark.parametrize(
    "name",
    [
        "depth_converted_count",
        "depth_rejected_count",
        "pressure_endpoints_evaluated_count",
        "pressure_endpoints_unavailable_count",
    ],
)
def test_reject_forged_depth_counts(report, name):
    forged = report.model_copy(update={name: getattr(report, name) + 1})
    with pytest.raises(ValidationError):
        local.serialize_local_audit(forged)


@pytest.mark.parametrize(
    "name,value",
    [
        ("matched_pair_count", 1),
        ("comparison_ready", True),
        ("overlap_status", "matched"),
        ("adjusted_depth_report_sha256", "0" * 64),
    ],
)
def test_reject_forged_readiness_and_depth_digest(report, name, value):
    with pytest.raises(ValidationError):
        local.serialize_local_audit(report.model_copy(update={name: value}))


def test_serializer_recomputes_policy_blockers(report):
    forged = report.assessment.model_copy(update={"blockers": ("invented_blocker",)})
    with pytest.raises(ValueError):
        local.serialize_local_audit(report.model_copy(update={"assessment": forged}))


@pytest.mark.parametrize(
    "name", ["value_count", "finite_value_count", "missing_value_count"]
)
def test_field_summary_count_consistency(report, name):
    data = report.field.model_dump()
    data[name] += 1
    with pytest.raises(ValidationError):
        NativeFieldVerification.model_validate(data)


def test_alignment_cannot_promote_vertical_support(report):
    data = report.model_dump()
    data["assessment"]["context"]["vertical_reference"] = {
        "status": "verified_for_input_snapshot",
        "reference": "not datum evidence",
    }
    with pytest.raises(ValidationError, match="cannot promote"):
        LocalMatchingAudit.model_validate(data)


def test_pipeline_rejects_changed_input(pipeline, monkeypatch):
    original = local.describe_file
    calls = 0

    def changing(path, maximum):
        nonlocal calls
        calls += 1
        result = original(path, maximum)
        if calls == 8:
            return result.model_copy(update={"modified_ns": result.modified_ns + 1})
        return result

    monkeypatch.setattr(local, "describe_file", changing)
    with pytest.raises(ProductError) as error:
        local.audit_local_matching(pipeline.root, pipeline.policy)
    assert error.value.code == "matching_inputs_changed"


def test_pipeline_rejects_cross_stage_identity(pipeline, monkeypatch):
    wrong = pipeline.context.model_copy(update={"client_input_sha256": "0" * 64})
    monkeypatch.setattr(
        local,
        "local_policy_preflight",
        lambda *args: assess_policy(pipeline.policy, wrong),
    )
    with pytest.raises(ProductError) as error:
        local.audit_local_matching(pipeline.root, pipeline.policy)
    assert error.value.code == "matching_audit_identity_mismatch"


def test_pipeline_rejects_wrong_returned_variable(pipeline, monkeypatch):
    wrong = read_native_field(pipeline.root, pipeline.field.manifest.model_id, "thetao")
    monkeypatch.setattr(local, "read_native_field", lambda *args: wrong)
    with pytest.raises(ProductError) as error:
        local.audit_local_matching(pipeline.root, pipeline.policy)
    assert error.value.code == "matching_audit_identity_mismatch"


@pytest.fixture
def cli_policy(tmp_path, monkeypatch, audit_inputs):
    path = tmp_path / "policy.yaml"
    path.write_text(audit_inputs.policy.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    return path


def test_cli_blocked_exit_three(cli_policy, report, monkeypatch, capsys):
    before = cli_policy.read_bytes()
    monkeypatch.setattr(cli, "audit_local_matching", lambda *args: report)
    assert cli.main(["--policy", "policy.yaml"]) == 3
    output = capsys.readouterr()
    assert json.loads(output.out)["matched_pair_count"] == 0
    assert output.err == ""
    assert cli_policy.read_bytes() == before


@pytest.mark.parametrize(
    "invalid",
    ["[unterminated", "!!python/object/apply:os.system []", "private: SECRET"],
)
def test_cli_bad_policy_sanitized(cli_policy, monkeypatch, capsys, invalid):
    cli_policy.write_text(invalid, encoding="utf-8")
    monkeypatch.setattr(
        cli, "audit_local_matching", lambda *args: pytest.fail("audit must not run")
    )
    assert cli.main(["--policy", "policy.yaml"]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["error"]["code"] == "invalid_matching_audit_input"
    assert "SECRET" not in output.err


def test_cli_product_error_does_not_expose_private_path(
    cli_policy, monkeypatch, capsys
):
    def fail(*args):
        raise ProductError("source_rejected", "C:/PRIVATE_SECRET/file.nc")

    monkeypatch.setattr(cli, "audit_local_matching", fail)
    assert cli.main(["--policy", "policy.yaml"]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["error"]["code"] == "source_rejected"
    assert "PRIVATE_SECRET" not in output.err


def test_cli_policy_mutation_rejects_output(cli_policy, report, monkeypatch, capsys):
    before = cli.describe_file(cli_policy, 16384)
    checks = iter(
        (before, before.model_copy(update={"modified_ns": before.modified_ns + 1}))
    )
    monkeypatch.setattr(cli, "describe_file", lambda *args: next(checks))
    monkeypatch.setattr(cli, "audit_local_matching", lambda *args: report)
    assert cli.main(["--policy", "policy.yaml"]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["error"]["code"] == "policy_changed"
