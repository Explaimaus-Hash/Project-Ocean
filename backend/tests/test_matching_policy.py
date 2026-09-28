"""Synthetic, offline preflight contracts: never an assertion of matched pairs."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.app.comparison.policy import assess_policy, serialize_policy_assessment
from backend.app.schemas.matching_policy import (
    MatchingContext,
    MatchingPolicy,
    MatchingPolicyAssessment,
    MatchingTolerances,
    ModelTimeCell,
    SupportEvidence,
)

DAY = datetime(2019, 1, 29, tzinfo=UTC)
VERIFIED = {
    "status": "verified_for_input_snapshot",
    "reference": "Synthetic fixture evidence only; not provider metadata",
}


def policy(**changes):
    return MatchingPolicy.model_validate(
        {
            "model_id": "m_" + "1" * 24,
            "collection_id": "o_" + "2" * 24,
            "acquisition_id": "a_" + "3" * 24,
            "data_mode": "synthetic",
            "quantity": "practical_salinity",
            "tolerances": {
                "horizontal_m": 100,
                "vertical_m": 1,
                "time_seconds": 43200,
                "review": "reviewed_for_selection",
                "rationale": "Synthetic boundary testing, not an operational default",
            },
            **changes,
        }
    )


def cell(**changes):
    return ModelTimeCell.model_validate(
        {
            "source_time_index": 7,
            "label": DAY,
            "start": DAY,
            "end": DAY + timedelta(days=1),
            **changes,
        }
    )


def context(**changes):
    identity = policy().model_dump()
    return MatchingContext.model_validate(
        {
            **{
                name: identity[name]
                for name in (
                    "model_id",
                    "collection_id",
                    "acquisition_id",
                    "data_mode",
                    "quantity",
                )
            },
            **{
                name: str(index) * 64
                for index, name in enumerate(
                    (
                        "model_manifest_sha256",
                        "collection_file_sha256",
                        "collection_canonical_sha256",
                        "client_input_sha256",
                        "provider_input_sha256",
                    ),
                    start=1,
                )
            },
            "sample_count": 2,
            "strict_qc_eligible_count": 2,
            "quantity_eligible_count": 2,
            "joint_eligible_count": 2,
            "source_time_indices": (7,),
            "source_time_labels": (DAY,),
            "time_cells": (cell(),),
            **{
                name: VERIFIED
                for name in (
                    "time_support",
                    "vertical_reference",
                    "wet_mask",
                    "bottom_support",
                    "coastline_connectivity",
                    "adjusted_depth_alignment",
                )
            },
            **changes,
        }
    )


@pytest.mark.parametrize("name", ["horizontal_m", "vertical_m", "time_seconds"])
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), -float("inf")])
def test_tolerances_reject_negative_or_nonfinite(name, value):
    with pytest.raises(ValidationError):
        MatchingTolerances(**{name: value})


@pytest.mark.parametrize(
    ("name", "maximum"),
    [("horizontal_m", 100000), ("vertical_m", 1000), ("time_seconds", 86400)],
)
def test_tolerance_numeric_boundaries(name, maximum):
    assert getattr(MatchingTolerances(**{name: 0}), name) == 0
    assert getattr(MatchingTolerances(**{name: maximum}), name) == maximum
    with pytest.raises(ValidationError):
        MatchingTolerances(**{name: maximum + 1})


@pytest.mark.parametrize(
    "missing", ["horizontal_m", "vertical_m", "time_seconds", "rationale"]
)
def test_review_requires_every_limit_and_rationale(missing):
    values = policy().tolerances.model_dump()
    values[missing] = None
    with pytest.raises(ValidationError):
        MatchingTolerances.model_validate(values)


def test_digest_stable_across_roundtrip_and_changes_with_policy():
    original = policy()
    assert (
        original.policy_id()
        == MatchingPolicy.model_validate_json(original.model_dump_json()).policy_id()
    )
    assert original.policy_id() != policy(max_samples=1).policy_id()
    assert (
        original.policy_id()
        != policy(quantity="potential_temperature_0_dbar_ITS90_C").policy_id()
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("model_id", "m_" + "4" * 24),
        ("collection_id", "o_" + "4" * 24),
        ("acquisition_id", "a_" + "4" * 24),
        ("data_mode", "real"),
        ("quantity", "potential_temperature_0_dbar_ITS90_C"),
    ],
)
def test_identity_and_mode_mismatch_block(name, value):
    report = assess_policy(policy(), context(**{name: value}))
    assert name + "_mismatch" in report.blockers
    assert report.status == "blocked"


@pytest.mark.parametrize(
    "name",
    [
        "time_support",
        "vertical_reference",
        "wet_mask",
        "bottom_support",
        "coastline_connectivity",
        "adjusted_depth_alignment",
    ],
)
def test_unresolved_support_blocks_without_claiming_no_overlap(name):
    changes = {name: {}}
    if name == "time_support":
        changes["time_cells"] = ()
    report = assess_policy(policy(), context(**changes))
    assert name + "_unresolved" in report.blockers
    assert report.status == "blocked"
    assert report.overlap_status == "not_evaluated"
    assert report.matched_pair_count == 0
    assert report.comparison_ready is False


def test_missing_tolerances_are_unknown_not_zero():
    report = assess_policy(policy(tolerances={}), context())
    assert set(report.blockers) == {
        "tolerances_unreviewed",
        "horizontal_m_unresolved",
        "vertical_m_unresolved",
        "time_seconds_unresolved",
    }


def test_verified_support_requires_reference():
    with pytest.raises(ValidationError):
        SupportEvidence(status="verified_for_input_snapshot")


def test_daily_interval_boundaries_and_original_midnight_label():
    interval = cell()
    assert interval.contains(DAY)
    assert interval.contains(DAY + timedelta(days=1, microseconds=-1))
    assert not interval.contains(DAY - timedelta(microseconds=1))
    assert not interval.contains(DAY + timedelta(days=1))
    assert interval.label == DAY
    assert interval.label != interval.start + timedelta(hours=12)
    noon_label = cell(label=DAY + timedelta(hours=12))
    assert noon_label.start == DAY
    assert noon_label.label == DAY + timedelta(hours=12)


def test_noon_to_noon_bounds_are_not_calendar_daily_cells():
    with pytest.raises(ValidationError):
        cell(start=DAY - timedelta(hours=12), end=DAY + timedelta(hours=12))


@pytest.mark.parametrize("name", ["label", "start", "end"])
@pytest.mark.parametrize(
    "bad", [DAY.replace(tzinfo=None), DAY.astimezone(timezone(timedelta(hours=1)))]
)
def test_interval_requires_explicit_utc(name, bad):
    with pytest.raises(ValidationError):
        cell(**{name: bad})


def test_observation_interval_lookup_requires_utc():
    with pytest.raises(ValueError):
        cell().contains(DAY.replace(tzinfo=None))


@pytest.mark.parametrize("hours", [-24, 0, 12, 25])
def test_only_one_day_interval_supported(hours):
    with pytest.raises(ValidationError):
        cell(end=DAY + timedelta(hours=hours))


@pytest.mark.parametrize(
    "changes",
    [
        {"time_cells": ()},
        {"source_time_labels": ()},
        {"source_time_indices": (8,)},
        {"source_time_labels": (DAY + timedelta(hours=12),)},
        {"time_support": {}},
        {"source_time_labels": (DAY.replace(tzinfo=None),)},
    ],
)
def test_missing_misaligned_or_inferred_intervals_rejected(changes):
    with pytest.raises(ValidationError):
        context(**changes)


def test_overlapping_intervals_and_duplicate_indices_rejected():
    next_cell = cell(
        source_time_index=8,
        label=DAY + timedelta(days=1),
        start=DAY,
        end=DAY + timedelta(days=1),
    )
    with pytest.raises(ValidationError):
        context(
            source_time_indices=(7, 8),
            source_time_labels=(DAY, DAY + timedelta(days=1)),
            time_cells=(cell(), next_cell),
        )
    with pytest.raises(ValidationError):
        context(
            source_time_indices=(7, 7),
            source_time_labels=(DAY, DAY),
            time_cells=(cell(), cell()),
        )


def test_mixed_naive_aware_source_labels_raise_validation_error():
    with pytest.raises(ValidationError):
        context(
            source_time_indices=(7, 8),
            source_time_labels=(DAY, (DAY + timedelta(days=1)).replace(tzinfo=None)),
            time_cells=(),
            time_support={},
        )


@pytest.mark.parametrize(
    "name", ["strict_qc_eligible_count", "quantity_eligible_count"]
)
def test_eligibility_count_cannot_exceed_population(name):
    with pytest.raises(ValidationError):
        context(**{name: 3})


def test_empty_selection_and_sample_budget_are_explicit_blockers():
    report = assess_policy(
        policy(),
        context(
            sample_count=0,
            strict_qc_eligible_count=0,
            quantity_eligible_count=0,
            joint_eligible_count=0,
        ),
    )
    assert "observation_selection_empty" in report.blockers
    assert report.overlap_status == "not_evaluated"
    assert "sample_limit" in assess_policy(policy(max_samples=1), context()).blockers
    empty_model = context(
        source_time_indices=(), source_time_labels=(), time_cells=(), time_support={}
    )
    assert "model_time_selection_empty" in assess_policy(policy(), empty_model).blockers


@pytest.mark.parametrize("value", [0, 5001])
def test_max_samples_bounded(value):
    with pytest.raises(ValidationError):
        policy(max_samples=value)


def test_satisfied_policy_is_still_not_matched_or_ready():
    report = assess_policy(policy(), context())
    assert report.status == "policy_satisfied_not_matched"
    assert report.blockers == ()
    assert report.overlap_status == "not_evaluated"
    assert report.matched_pair_count == 0
    assert report.comparison_ready is False


def test_disjoint_eligible_populations_do_not_satisfy_policy():
    report = assess_policy(
        policy(),
        context(
            strict_qc_eligible_count=1,
            quantity_eligible_count=1,
            joint_eligible_count=0,
        ),
    )
    assert "no_jointly_eligible_observations" in report.blockers
    assert report.status == "blocked"


@pytest.mark.parametrize(
    "name", ["strict_qc_eligible_count", "quantity_eligible_count"]
)
def test_joint_count_cannot_exceed_either_marginal(name):
    with pytest.raises(ValidationError):
        context(**{name: 1})


def test_contracts_frozen_and_assessment_does_not_mutate_inputs(monkeypatch):
    selected_policy, selected_context = policy(), context()
    original = (selected_policy.model_dump_json(), selected_context.model_dump_json())

    def forbidden(*args, **kwargs):
        raise AssertionError("Policy assessment must not perform file/network I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    assess_policy(selected_policy, selected_context)
    assert original == (
        selected_policy.model_dump_json(),
        selected_context.model_dump_json(),
    )
    with pytest.raises(ValidationError):
        selected_policy.max_samples = 1
    with pytest.raises(ValidationError):
        selected_context.sample_count = 1


def test_safe_serialization_roundtrip_and_tamper_detection():
    report = assess_policy(policy(), context())
    payload = serialize_policy_assessment(report)
    assert payload.endswith(b"\n")
    assert len(payload) <= report.policy.maximum_report_bytes
    assert MatchingPolicyAssessment.model_validate_json(payload) == report
    altered = json.loads(payload)
    altered["policy_id"] = "mp_" + "f" * 64
    with pytest.raises(ValidationError):
        MatchingPolicyAssessment.model_validate(altered)
    altered = json.loads(payload)
    altered["status"] = "blocked"
    with pytest.raises(ValidationError):
        MatchingPolicyAssessment.model_validate(altered)
    altered = json.loads(payload)
    altered["comparison_ready"] = True
    with pytest.raises(ValidationError):
        MatchingPolicyAssessment.model_validate(altered)


def test_serialization_recomputes_blockers_not_just_internal_consistency():
    blocked = assess_policy(policy(tolerances={}), context())
    forged = MatchingPolicyAssessment.model_validate(
        {
            **blocked.model_dump(),
            "status": "policy_satisfied_not_matched",
            "blockers": (),
        }
    )
    with pytest.raises(ValueError):
        serialize_policy_assessment(forged)


def test_module_does_not_import_scientific_or_provider_clients():
    probe = """
import sys
from backend.app.comparison.policy import assess_policy
for name in ('numpy', 'xarray', 'netCDF4', 'gsw', 'argopy', 'copernicusmarine'):
    assert name not in sys.modules, name
"""
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
