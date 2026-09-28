"""Integrated input assembly with unresolved support; no live provider access."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.comparison import execution as mod
from backend.app.comparison import matching
from backend.app.comparison.preflight import strict_argo_issues
from backend.app.schemas.matching import ObservationSupport
from backend.app.schemas.static_support import StaticSupportSnapshot
from backend.app.storage.product_common import ProductError
from backend.tests.test_matching_local import audit_inputs as audit_inputs
from backend.tests.test_matching_local import pipeline as pipeline
from scripts import run_local_matching as cli


@pytest.fixture
def integrated(pipeline, monkeypatch):
    x = pipeline
    checks = [
        (
            not strict_argo_issues(s, q, x.policy),
            not q.salinity_exclusions and q.practical_salinity is not None,
        )
        for s, q in zip(x.collection.samples, x.quantities.results, strict=True)
    ]
    monkeypatch.setattr(
        x,
        "context",
        x.context.model_copy(
            update={
                "strict_qc_eligible_count": sum(qc for qc, _ in checks),
                "quantity_eligible_count": sum(ok for _, ok in checks),
                "joint_eligible_count": sum(qc and ok for qc, ok in checks),
            }
        ),
    )
    # Assembly unit tests mock the verified reader boundary, not acquisition.
    # This synthetic snapshot is not a claim of authentic on-disk static files.
    record = {"sha256": "a" * 64, "size_bytes": 1}
    keys = (
        "catalogue.json",
        "catalogue_end.json",
        "metadata_end.json",
        ".zmetadata",
        "elevation/0",
        "latitude/0",
        "longitude/0",
    )
    static = StaticSupportSnapshot(
        support_id="b_" + "a" * 24,
        manifest_file=x.file,
        manifest={
            "schema_version": 1,
            "processing_version": "static_acquisition_1",
            "status": "acquired_grid_checked_not_matching_ready",
            "data_mode": "synthetic",
            "model_id": x.policy.model_id,
            "model_manifest": x.field.manifest_file,
            "dataset_id": "cmems_mod_glo_phy_my_0.083deg_static_202311--ext--bathy",
            "source_asset": "https://example.invalid/synthetic",
            "retrieved_at": x.field.manifest.identity.axes.times[0],
            "source_read_set": dict.fromkeys(keys, record),
            "source_read_set_is_complete_global_store": False,
            "source_latitude_indices": (0, 1),
            "source_longitude_indices": (0, 1),
            "source_elevation_indices": tuple(range(50)),
            "axis_interpretation": (
                "original_negative_elevation_and_attributes_preserved"
            ),
            "transfer_bytes": 7,
            "decoded_chunk_bytes": 1,
            "subset": x.file,
            "checks": {
                "surface_wet_count": 4,
                "surface_dry_count": 0,
                "wet_level_count_equals_deptho_lev": True,
                "bottom_level_numbering": (
                    "unresolved_not_inferred_from_numeric_agreement"
                ),
                "vertical_reference": "unresolved",
                "coastline_connectivity": "not_evaluated",
            },
            "comparison_ready": False,
        },
        model_axes=x.field.manifest.identity.axes,
        source_elevation_m=tuple(-49.5 + i for i in range(50)),
        model_depth_to_source_elevation_index=(49, 48),
        mask=(1,) * 200,
        deptho_m=(500,) * 4,
        deptho_lev=(50,) * 4,
    )
    monkeypatch.setattr(mod, "read_native_field", lambda *a: x.field)
    monkeypatch.setattr(mod, "read_static_support", lambda *a: static)
    monkeypatch.setattr(mod, "audit_quantities", lambda *a: x.quantities)
    monkeypatch.setattr(
        mod,
        "ObservationStore",
        lambda *a: SimpleNamespace(collection=lambda cid: x.collection),
    )
    return x, static


def run(integrated):
    x, s = integrated
    return mod.execute_local_matching(x.root, x.policy, s.support_id)


def test_engine_invoked_but_pair_selection_never_runs(integrated, monkeypatch):
    seen = []
    original = mod.match_native

    def engine(request):
        seen.append(request)
        return original(request)

    monkeypatch.setattr(mod, "match_native", engine)
    monkeypatch.setattr(
        matching, "_select", lambda *a: pytest.fail("Unresolved support searched pairs")
    )
    result = run(integrated)
    assert len(seen) == 1
    req = seen[0]
    assert req.values == integrated[0].field.values
    assert req.valid_mask == integrated[0].field.valid_mask
    assert all(c.wet is None and c.bottom_m is None for c in req.columns)
    assert all(s.wet is None and s.connected is None for s in req.observation_support)
    assert all(s.candidate_latitude_index is None for s in req.observation_support)
    assert result.engine.status == "blocked" and result.engine.results == ()
    assert result.engine.overlap_status == "not_evaluated"
    assert not result.comparison_ready
    assert mod.serialize_local_execution(result) == mod.serialize_local_execution(
        run(integrated)
    )


@pytest.mark.parametrize(
    "kind", ["model", "scientific", "metadata", "collection", "static_mode"]
)
def test_cross_stage_binding_rejected(integrated, monkeypatch, kind):
    x, s = integrated
    if kind == "collection":
        changed = x.collection.model_copy(update={"data_mode": "real"})
        monkeypatch.setattr(
            mod,
            "ObservationStore",
            lambda *a: SimpleNamespace(collection=lambda cid: changed),
        )
    elif kind == "static_mode":
        changed = s.model_copy(
            update={"manifest": s.manifest.model_copy(update={"data_mode": "real"})}
        )
        monkeypatch.setattr(mod, "read_static_support", lambda *a: changed)
    else:
        d = x.field.model_dump()
        if kind == "model":
            d["manifest_file"]["sha256"] = "f" * 64
        else:
            name = "scientific_file" if kind == "scientific" else "source_metadata_file"
            d["manifest"][name]["sha256"] = "f" * 64
        changed = type(x.field).model_validate(d)
        monkeypatch.setattr(mod, "read_native_field", lambda *a: changed)
    with pytest.raises(ProductError, match="Verified inputs differ"):
        run(integrated)


@pytest.mark.parametrize(
    "source", ["audit_local_matching", "read_native_field", "read_static_support"]
)
def test_post_read_changes_rejected(integrated, monkeypatch, source):
    original = getattr(mod, source)
    count = 0

    def changed(*args):
        nonlocal count
        count += 1
        value = original(*args)
        return None if count == 2 else value

    monkeypatch.setattr(mod, source, changed)
    with pytest.raises(ProductError, match="Inputs changed"):
        run(integrated)


@pytest.mark.parametrize(
    "y,x,wet,connected",
    [
        (None, 0, None, None),
        (0, None, None, None),
        (None, None, True, None),
        (None, None, None, False),
    ],
)
def test_absent_candidate_cannot_invent_support(y, x, wet, connected):
    with pytest.raises(ValidationError):
        ObservationSupport(
            sample_id="s_" + "a" * 24,
            source_sample_index=0,
            candidate_latitude_index=y,
            candidate_longitude_index=x,
            wet=wet,
            connected=connected,
        )


@pytest.mark.parametrize("kind", ["blocker", "ready", "model", "limit"])
def test_report_contract_rejects_forgery(integrated, monkeypatch, kind):
    report = run(integrated)
    if kind == "limit":
        monkeypatch.setattr(mod, "MAX_EXECUTION_BYTES", 1)
        with pytest.raises(ProductError):
            mod.serialize_local_execution(report)
        return
    if kind == "ready":
        report = report.model_copy(update={"comparison_ready": True})
    elif kind == "model":
        report = report.model_copy(
            update={
                "spatial": report.spatial.model_copy(
                    update={"model_id": "m_" + "f" * 24}
                )
            }
        )
    else:
        report = report.model_copy(
            update={"engine": report.engine.model_copy(update={"blockers": ("fake",)})}
        )
    with pytest.raises(ValueError):
        mod.serialize_local_execution(report)


def test_cli_blocked_and_sanitized(integrated, monkeypatch, tmp_path, capsys):
    x, _ = integrated
    path = tmp_path / "policy.yaml"
    path.write_text(x.policy.model_dump_json())
    before = path.read_bytes()
    result = run(integrated)
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mod, "execute_local_matching", lambda *a: result)
    assert cli.main(["--policy", "policy.yaml"]) == 3
    assert json.loads(capsys.readouterr().out)["engine"]["status"] == "blocked"
    assert path.read_bytes() == before
    path.write_text("private: SECRET")
    assert cli.main(["--policy", "policy.yaml"]) == 2
    output = capsys.readouterr()
    assert not output.out and "SECRET" not in output.err
