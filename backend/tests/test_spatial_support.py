"""Grid diagnostics remain distinct from physical observation support."""

import hashlib
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.comparison import spatial_support as mod
from backend.app.comparison.static_reader import read_static_support
from backend.app.schemas.spatial_support import SpatialDiagnosticRow, SpatialPosition
from backend.app.schemas.static_support import StaticSupportSnapshot
from backend.app.storage.product_common import ProductError
from backend.tests.test_static_reader import saved as saved_fixture
from scripts import audit_spatial_support as cli


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    root, sid, mid = saved_fixture.__wrapped__(tmp_path_factory)
    return read_static_support(root, sid, mid)


def point(lat=-0.5, lon=65.5, index=0):
    return SpatialPosition(
        sample_id="s_" + f"{index:024x}",
        source_sample_index=index,
        latitude=lat,
        longitude=lon,
    )


def diagnose(snapshot, p=None):
    return mod.diagnose_positions(snapshot, (p or point(),)).results[0]


def with_mask(snapshot, dry_cells=(), dry_levels=()):
    data = snapshot.model_dump()
    mask = list(data["mask"])
    for z in range(50):
        for cell in range(4):
            if cell in dry_cells or z in dry_levels:
                mask[z * 4 + cell] = 0
    data["mask"] = tuple(mask)
    data["manifest"]["checks"]["surface_wet_count"] = sum(mask[-4:])
    data["manifest"]["checks"]["surface_dry_count"] = 4 - sum(mask[-4:])
    return StaticSupportSnapshot.model_validate(data)


@pytest.mark.parametrize(
    "lat,lon,n",
    [(-1, 65, 1), (0, 66, 1), (-1, 65.5, 2), (-0.5, 65, 2), (-0.5, 65.5, 4)],
)
def test_exact_bracketing_and_no_support_promotion(snapshot, lat, lon, n):
    row = diagnose(snapshot, point(lat, lon))
    assert len(row.stencil) == n
    assert row.stencil_surface == "all_wet"
    assert row.observation_wet is None and row.coastline_connected is None
    assert row.observation_bottom_supported is None
    assert row.candidate.prepared_level_wet == (True, True)
    assert row.candidate.full_mask_deepest_depth_coordinate_m == 49.5
    assert row.candidate.full_mask_shallowest_depth_coordinate_m == 0.5
    assert row.candidate.deptho_below_geoid_m == 500
    assert row.candidate.deptho_lev_uninterpreted == 50


@pytest.mark.parametrize(
    "lat,lon", [(-1.00001, 65.5), (0.00001, 65.5), (-0.5, 64.99999), (-0.5, 66.00001)]
)
def test_no_half_cell_extrapolation(snapshot, lat, lon):
    row = diagnose(snapshot, point(lat, lon))
    assert row.status == "outside_centre_envelope"
    assert row.candidate is None and not row.stencil


def test_no_wet_fallback(snapshot):
    s = with_mask(snapshot, dry_cells=(0,))
    row = diagnose(s, point(-0.99, 65.01))
    assert row.candidate.model_latitude_index == 0
    assert row.candidate.model_longitude_index == 0
    assert not row.candidate.surface_wet
    assert row.candidate.full_mask_deepest_depth_coordinate_m is None
    assert row.stencil_surface == "mixed"


def test_all_dry_not_observation_land_certificate(snapshot):
    row = diagnose(with_mask(snapshot, dry_cells=(0, 1, 2, 3)))
    assert row.stencil_surface == "all_dry"
    assert row.observation_wet is None


def test_mask_not_level_number_defines_wet_centres(snapshot):
    s = with_mask(snapshot, dry_levels=tuple(range(48)))
    row = diagnose(s)
    assert row.candidate.full_mask_deepest_depth_coordinate_m == 1.5
    assert row.candidate.deptho_lev_uninterpreted == 50
    assert row.candidate.prepared_level_wet == (True, True)


def test_holey_column_rejected(snapshot):
    with pytest.raises(ValueError, match="Noncontiguous"):
        diagnose(with_mask(snapshot, dry_levels=(20,)))


def test_tie_native_indices_and_distinct_static_indices(snapshot):
    d = snapshot.model_dump()
    d["manifest"]["source_latitude_indices"] = (100, 101)
    d["manifest"]["source_longitude_indices"] = (200, 201)
    row = diagnose(StaticSupportSnapshot.model_validate(d), point(0, 65.5))
    assert row.candidate.model_latitude_index == 1
    assert row.candidate.model_longitude_index == 0
    assert row.candidate.static_latitude_index == 101
    assert row.candidate.static_longitude_index == 200


@pytest.mark.parametrize("kind", ["duplicate", "work", "output", "samples"])
def test_limits_before_unbounded_work(snapshot, monkeypatch, kind):
    points = (point(),)
    if kind == "duplicate":
        points *= 2
    elif kind == "work":
        monkeypatch.setattr(mod, "MAX_CHECKS", 1)
    elif kind == "output":
        monkeypatch.setattr(mod, "MAX_OUTPUT", 1)
    else:
        points *= 5001
    with pytest.raises(ValueError):
        mod.diagnose_positions(snapshot, points)


@pytest.mark.parametrize(
    "field,value",
    [("latitude", float("nan")), ("longitude", 180), ("source_sample_index", True)],
)
def test_bad_position_rejected(field, value):
    d = point().model_dump()
    d[field] = value
    with pytest.raises(ValidationError):
        SpatialPosition.model_validate(d)


def test_report_cannot_promote_connectivity(snapshot):
    d = diagnose(snapshot).model_dump()
    d["coastline_connected"] = True
    with pytest.raises(ValidationError):
        SpatialDiagnosticRow.model_validate(d)


def test_pure_repeatable_and_unchanged(snapshot):
    before = snapshot.model_dump_json()
    report = mod.diagnose_positions(snapshot, (point(),))
    assert report == mod.diagnose_positions(snapshot, (point(),))
    assert snapshot.model_dump_json() == before
    assert not report.comparison_ready


@pytest.mark.parametrize("case", ["ok", "binding", "changed"])
def test_local_wrapper_binding_and_postcheck(snapshot, monkeypatch, tmp_path, case):
    canonical = hashlib.sha256(b"{}").hexdigest()
    collection = SimpleNamespace(
        model_dump_json=lambda: "{}",
        data_mode="synthetic",
        source_id="argo",
        collection_id="o_" + "a" * 24,
        samples=(point(),),
    )
    ctx = SimpleNamespace(
        model_manifest_sha256=snapshot.manifest.model_manifest.sha256,
        data_mode="synthetic",
        collection_id=collection.collection_id,
        collection_canonical_sha256=canonical,
        collection_file_sha256="b" * 64,
    )
    audit = SimpleNamespace(
        assessment=SimpleNamespace(context=ctx, blockers=("unresolved",)),
        field=SimpleNamespace(axes=snapshot.model_axes),
    )
    if case == "binding":
        ctx.model_manifest_sha256 = "f" * 64
    calls = []

    def audit_call(*args):
        calls.append(1)
        return None if case == "changed" and len(calls) == 2 else audit

    monkeypatch.setattr(mod, "audit_local_matching", audit_call)
    monkeypatch.setattr(mod, "read_static_support", lambda *args: snapshot)
    monkeypatch.setattr(
        mod,
        "ObservationStore",
        lambda *args: SimpleNamespace(collection=lambda cid: collection),
    )
    policy = SimpleNamespace(
        model_id=snapshot.manifest.model_id,
        collection_id=collection.collection_id,
        policy_id=lambda: "mp_" + "d" * 64,
    )
    if case != "ok":
        with pytest.raises(ProductError):
            mod.audit_spatial_support(tmp_path, policy, snapshot.support_id)
    else:
        result = mod.audit_spatial_support(tmp_path, policy, snapshot.support_id)
        assert result["remaining_matching_blockers"] == ["unresolved"]
        assert result["matched_pair_count"] == 0
        assert len(calls) == 2


def test_cli_sanitized_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    assert cli.main(["--policy", "../private-secret.yaml"]) == 2
    message = capsys.readouterr().err
    assert "private-secret" not in message and str(tmp_path) not in message
    assert json.loads(message)["error"]["code"]
