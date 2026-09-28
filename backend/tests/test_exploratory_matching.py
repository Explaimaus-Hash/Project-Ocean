"""Offline assumption-labelled matching, isolated from strict evidence approval."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta

import pytest

from backend.app.comparison import execution, exploratory
from backend.app.comparison.adjusted_depth import build_adjusted_depth
from backend.app.comparison.matching import match_native
from backend.app.comparison.preflight import strict_argo_issues
from backend.app.processing.quantities import derive_quantities
from backend.app.schemas.exploratory_matching import ExploratoryAssumptions
from backend.app.schemas.matching import NativeMatchingInput
from backend.app.schemas.observations import ObservationCollection
from backend.app.schemas.static_support import StaticSupportSnapshot
from backend.tests.test_matching_engine import collection as collection
from backend.tests.test_matching_engine import make_request
from backend.tests.test_matching_execution import integrated as integrated
from backend.tests.test_matching_local import audit_inputs as audit_inputs
from backend.tests.test_matching_local import pipeline as pipeline
from scripts import run_exploratory_matching as cli


def rebind(r, data):
    collection = ObservationCollection.model_validate(data)
    q = derive_quantities(collection, r.quantities.evidence)
    d = r.model_dump()
    d["collection"] = collection
    d["quantities"] = q
    d["depths"] = build_adjusted_depth(collection, q, r.context.collection_file_sha256)
    d["context"]["collection_canonical_sha256"] = hashlib.sha256(
        collection.model_dump_json().encode()
    ).hexdigest()
    checks = [
        (
            not strict_argo_issues(s, v, r.policy),
            not v.salinity_exclusions and v.practical_salinity is not None,
        )
        for s, v in zip(collection.samples, q.results, strict=True)
    ]
    d["context"].update(
        strict_qc_eligible_count=sum(a for a, _ in checks),
        quantity_eligible_count=sum(b for _, b in checks),
        joint_eligible_count=sum(a and b for a, b in checks),
    )
    return NativeMatchingInput.model_validate(d)


@pytest.fixture
def example(collection, integrated):
    r = make_request(collection)
    d = r.model_dump()
    d["axes"]["depth_m"] = (0.5, 6, 10)
    d["policy"]["tolerances"] = {}
    for name in (
        "time_support",
        "vertical_reference",
        "wet_mask",
        "bottom_support",
        "coastline_connectivity",
    ):
        d["context"][name] = {"status": "unresolved"}
    d["context"]["time_cells"] = ()
    r = NativeMatchingInput.model_validate(d)
    s = integrated[1].model_dump()
    s["model_axes"] = r.axes
    s["manifest"]["model_id"] = r.policy.model_id
    s["manifest"]["model_manifest"]["sha256"] = r.context.model_manifest_sha256
    s["source_elevation_m"] = tuple(-v for v in range(57, 10, -1)) + (-10, -6, -0.5)
    s["model_depth_to_source_elevation_index"] = (49, 48, 47)
    return r, StaticSupportSnapshot.model_validate(s)


def run(example):
    return exploratory.match_exploratory(*example)


def test_pairs_are_explicit_assumptions_without_mutating_inputs(example):
    r, s = example
    before = r.model_dump_json(), s.model_dump_json()
    result = run(example)
    assert result.status == "evaluated" and result.matched_pair_count == 6
    assert all(row.assurance == "exploratory_assumptions" for row in result.results)
    assert not result.comparison_ready and not result.independent_validation
    assert result.strict_assessment.status == "blocked"
    assert result.strict_assessment.context.time_cells == ()
    assert result.strict_assessment.context.vertical_reference.status == "unresolved"
    assert result.results[0].candidate.source_time_index == 8
    assert result.results[0].candidate.midpoint_offset_seconds == 43200
    assert result.results[0].observation_value == 35.5
    assert result.results[0].candidate.model_value == 35.25
    assert before == (r.model_dump_json(), s.model_dump_json())
    assert exploratory.serialize_exploratory(
        result
    ) == exploratory.serialize_exploratory(run(example))


def test_real_data_never_relabelled_synthetic(example):
    r, s = example
    d = r.model_dump()
    d["policy"]["data_mode"] = d["context"]["data_mode"] = "real"
    d["collection"]["data_mode"] = d["quantities"]["data_mode"] = "real"
    # Explicit synthetic fixture relabel for contract regression, not file evidence.
    c = ObservationCollection.model_validate(d["collection"])
    q = derive_quantities(c, r.quantities.evidence)
    d["quantities"] = q
    d["depths"] = build_adjusted_depth(c, q, r.context.collection_file_sha256)
    d["context"]["collection_canonical_sha256"] = hashlib.sha256(
        c.model_dump_json().encode()
    ).hexdigest()
    r = NativeMatchingInput.model_validate(d)
    sd = s.model_dump()
    sd["manifest"]["data_mode"] = "real"
    result = run((r, StaticSupportSnapshot.model_validate(sd)))
    assert result.data_mode == "real" and result.matched_pair_count == 6
    assert match_native(r)["status"] == "blocked"
    assert (
        "real_field_and_support_adapter_not_implemented"
        in result.strict_assessment.blockers
    )


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("valid_mask", False, "nearest_cell_masked"),
        ("values", None, "nearest_value_missing"),
    ],
)
def test_nearest_bad_value_never_falls_back(example, field, value, reason):
    r, s = example
    d = r.model_dump()
    d[field] = list(d[field])
    d[field][16] = value
    result = run((NativeMatchingInput.model_validate(d), s))
    assert result.matched_pair_count == 0
    assert all(reason in row.exclusions for row in result.results)
    assert all(row.candidate.source_depth_index == 11 for row in result.results)


@pytest.mark.parametrize(
    "kind", ["dry", "mixed", "bottom_missing", "bottom_inconsistent"]
)
def test_grid_proxy_rejects_unsafe_support(example, kind):
    r, s = example
    d = s.model_dump()
    if kind in ("dry", "mixed"):
        d["mask"] = tuple(0 if i % 4 == 0 else 1 for i in range(200))
        d["manifest"]["checks"].update(surface_wet_count=3, surface_dry_count=1)
        if kind == "mixed":
            rd = r.model_dump()
            rd["axes"]["latitude"] = (4.99, 6)
            r = NativeMatchingInput.model_validate(rd)
            d["model_axes"] = r.axes
    else:
        d["deptho_m"] = (None if kind == "bottom_missing" else 1,) + s.deptho_m[1:]
    result = run((r, StaticSupportSnapshot.model_validate(d)))
    assert result.matched_pair_count == 0
    expected = (
        "exploratory_grid_support_rejected"
        if kind in ("dry", "mixed")
        else "support_unresolved"
    )
    assert all(expected in row.exclusions for row in result.results)
    assert result.status == (
        "evaluated" if kind in ("dry", "mixed") else "partially_blocked"
    )


@pytest.mark.parametrize(
    "kind,reason",
    [
        ("outside", "outside_horizontal_support"),
        ("distance", "horizontal_tolerance_exceeded"),
        ("vertical", "vertical_tolerance_exceeded"),
        ("endpoints", "pressure_endpoints_outside_local_support"),
        ("time", "outside_time_support"),
    ],
)
def test_selection_and_full_endpoint_limits(example, kind, reason):
    r, s = example
    d = r.model_dump()
    if kind == "outside":
        d["axes"]["latitude"] = (6, 7)
    elif kind == "distance":
        d["axes"]["latitude"] = (4.9, 6)
    elif kind == "vertical":
        d["axes"]["depth_m"] = (0.5, 2, 10)
    elif kind == "endpoints":
        cd = r.collection.model_dump()
        for sample in cd["samples"]:
            sample["values"]["PRES"]["adjusted_error"] = 6
        r = rebind(r, cd)
        result = run((r, s))
        assert result.matched_pair_count == 0
        assert all(
            "pressure_endpoints_unavailable" in row.exclusions for row in result.results
        )
        return
    else:
        d["axes"]["times"] = tuple(t - timedelta(days=2) for t in r.axes.times)
        d["context"]["source_time_labels"] = d["axes"]["times"]
    r = NativeMatchingInput.model_validate(d)
    sd = s.model_dump()
    sd["model_axes"] = r.axes
    if kind == "vertical":
        sd["source_elevation_m"] = tuple(-v for v in range(57, 10, -1)) + (
            -10,
            -2,
            -0.5,
        )
    result = run((r, StaticSupportSnapshot.model_validate(sd)))
    assert result.matched_pair_count == 0
    assert all(reason in row.exclusions for row in result.results)


def test_full_valid_pressure_endpoints_cannot_exceed_prepared_depths(example):
    r, s = example
    d = r.collection.model_dump()
    for sample in d["samples"]:
        sample["values"]["PRES"]["adjusted_error"] = 5
    result = run((rebind(r, d), s))
    assert result.matched_pair_count == 0
    assert all(
        "pressure_endpoints_outside_local_support" in row.exclusions
        for row in result.results
    )


def test_one_bad_qc_is_retained_and_excluded(example):
    r, s = example
    d = r.collection.model_dump()
    d["samples"][0]["values"]["PSAL"]["adjusted_qc"] = "4"
    result = run((rebind(r, d), s))
    assert len(result.results) == 6 and result.matched_pair_count == 5
    assert result.results[0].exclusions


@pytest.mark.parametrize(
    "kind", ["identity", "depth_alignment", "temperature", "deep", "noon"]
)
def test_non_assumable_gates_block_before_selection(example, monkeypatch, kind):
    r, s = example
    d = r.model_dump()
    if kind == "identity":
        d["policy"]["acquisition_id"] = "a_" + "9" * 24
    elif kind == "depth_alignment":
        d["context"]["adjusted_depth_alignment"] = {"status": "unresolved"}
    elif kind == "temperature":
        d["policy"]["quantity"] = d["context"]["quantity"] = (
            "potential_temperature_0_dbar_ITS90_C"
        )
        d["context"]["quantity_eligible_count"] = d["context"][
            "joint_eligible_count"
        ] = 0
        d["source_variable"] = "thetao"
        d["quantity_units"] = "degree_Celsius (ITS-90)"
    elif kind == "deep":
        d["axes"]["depth_m"] = (0.5, 6, 11)
    else:
        d["axes"]["times"] = tuple(t + timedelta(hours=12) for t in r.axes.times)
        d["context"]["source_time_labels"] = d["axes"]["times"]
    r = NativeMatchingInput.model_validate(d)
    sd = s.model_dump()
    sd["model_axes"] = r.axes
    if kind == "deep":
        sd["source_elevation_m"] = tuple(-v for v in range(58, 11, -1)) + (
            -11,
            -6,
            -0.5,
        )
    monkeypatch.setattr(
        exploratory, "select_candidate", lambda *a: pytest.fail("Blocked search")
    )
    result = run((r, StaticSupportSnapshot.model_validate(sd)))
    assert result.status == "blocked" and not result.results and result.blockers


@pytest.mark.parametrize(
    "field,value",
    [
        ("horizontal_m", 100000),
        ("vertical_m", float("nan")),
        ("assurance", "verified_for_input_snapshot"),
    ],
)
def test_assumption_contract_cannot_be_silently_widened(field, value):
    with pytest.raises(ValueError):
        ExploratoryAssumptions.model_validate({field: value})


@pytest.mark.parametrize(
    "kind", ["count", "ready", "assumption_id", "mode", "limits", "budget"]
)
def test_serialization_rejects_inconsistent_reports(example, monkeypatch, kind):
    result = run(example)
    d = result.model_dump()
    if kind == "count":
        d["matched_pair_count"] = 0
    elif kind == "ready":
        d["comparison_ready"] = True
    elif kind == "assumption_id":
        d["assumption_id"] = "ea_" + "0" * 64
    elif kind == "mode":
        d["data_mode"] = "real"
    elif kind == "limits":
        d["results"][0]["candidate"]["horizontal_offset_m"] = 7001
    else:
        monkeypatch.setattr(exploratory, "MAX_REPORT_BYTES", 1)
    with pytest.raises(ValueError):
        exploratory.serialize_exploratory(type(result).model_construct(**d))


def test_static_identity_and_budget_fail(example, monkeypatch):
    r, s = example
    d = s.model_dump()
    d["manifest"]["model_id"] = "m_" + "0" * 24
    with pytest.raises(ValueError, match="binding"):
        run((r, StaticSupportSnapshot.model_validate(d)))
    monkeypatch.setattr(exploratory, "MAX_REPORT_BYTES", 1)
    with pytest.raises(ValueError, match="budget"):
        run(example)


def test_cli_opt_in_success_and_sanitized_errors(
    example, tmp_path, monkeypatch, capsys
):
    r, _ = example
    report = run(example)
    path = tmp_path / "policy.yaml"
    path.write_text(r.policy.model_dump_json())
    before = path.read_bytes()
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(exploratory, "execute_exploratory", lambda *a: report)
    with pytest.raises(SystemExit):
        cli.main(["--policy", "policy.yaml"])
    capsys.readouterr()
    assert cli.main(["--accept-assumptions", "--policy", "policy.yaml"]) == 0
    assert json.loads(capsys.readouterr().out)["assurance"] == "exploratory_assumptions"
    assert path.read_bytes() == before
    path.write_text("private: SECRET")
    assert cli.main(["--accept-assumptions", "--policy", "policy.yaml"]) == 2
    output = capsys.readouterr()
    assert not output.out and "SECRET" not in output.err


def test_local_adapter_rechecks_inputs_and_daily_version(integrated, monkeypatch):
    x, s = integrated
    loaded = execution.load_matching_inputs(x.root, x.policy, s.support_id)
    monkeypatch.setattr(exploratory, "load_matching_inputs", lambda *a: loaded)
    checks = []
    monkeypatch.setattr(
        exploratory, "verify_matching_inputs_unchanged", lambda *a: checks.append(a)
    )
    exploratory.execute_exploratory(x.root, x.policy, s.support_id)
    assert len(checks) == 1
    provenance = loaded.field.manifest.identity.provenance.model_copy(
        update={"source_version": "unknown"}
    )
    bad = replace(
        loaded,
        field=loaded.field.model_copy(
            update={
                "manifest": loaded.field.manifest.model_copy(
                    update={
                        "identity": loaded.field.manifest.identity.model_copy(
                            update={"provenance": provenance}
                        )
                    }
                )
            }
        ),
    )
    monkeypatch.setattr(exploratory, "load_matching_inputs", lambda *a: bad)
    with pytest.raises(ValueError, match="daily 202311"):
        exploratory.execute_exploratory(x.root, x.policy, s.support_id)
