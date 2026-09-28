"""Tampered output contracts fail independently of normal kernel generation."""

import copy

import pytest
from pydantic import ValidationError
from test_matching_engine import make_request
from test_quantities import collection as quantity_collection

from backend.app.comparison.matching import match_native
from backend.app.schemas.matching import NativeMatchingReport


@pytest.fixture(scope="module")
def original_report(tmp_path_factory):
    collection = quantity_collection.__wrapped__(
        tmp_path_factory.mktemp("output_contract")
    )
    return match_native(make_request(collection))


def test_kernel_report_roundtrips(original_report):
    checked = NativeMatchingReport.model_validate(original_report)
    assert (
        NativeMatchingReport.model_validate_json(checked.model_dump_json()) == checked
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity_units", "degree_Celsius (ITS-90)"),
        ("source_variable", "thetao"),
        ("overlap_status", "no_valid_pairs"),
        ("overlap_status", "not_evaluated"),
        ("status", "partially_blocked"),
        ("matched_pair_count", 0),
    ],
)
def test_report_status_quantity_count_binding(original_report, field, value):
    data = copy.deepcopy(original_report)
    data[field] = value
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


@pytest.mark.parametrize("field", ["sample_id", "source_sample_index"])
def test_duplicate_output_identity_rejected(original_report, field):
    data = copy.deepcopy(original_report)
    data["results"][1][field] = data["results"][0][field]
    with pytest.raises(ValidationError, match="unique"):
        NativeMatchingReport.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("observation_longitude", 180),
        ("observation_latitude", 91),
        ("observation_depth_m", -1),
        ("observation_depth_m", None),
        ("observation_time", "2024-01-02T00:00:00"),
        ("observation_time", "2024-01-02T00:00:00+01:00"),
        ("observation_time", "2024-01-03T00:00:00Z"),
    ],
)
def test_observation_ranges_and_utc(original_report, field, value):
    data = copy.deepcopy(original_report)
    data["results"][0][field] = value
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_time_label", "2024-01-02T00:00:00"),
        ("time_start", "2024-01-02T01:00:00Z"),
        ("time_end", "2024-01-04T00:00:00Z"),
        ("vertical_offset_m", 0),
        ("midpoint_offset_seconds", 0),
        ("source_time_index", 999),
    ],
)
def test_candidate_temporal_and_offset_contract(original_report, field, value):
    data = copy.deepcopy(original_report)
    data["results"][0]["candidate"][field] = value
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


@pytest.mark.parametrize("value", [None, -0.1, 20.1])
def test_matched_pressure_errors_cannot_be_missing_negative_or_excessive(
    original_report, value
):
    data = copy.deepcopy(original_report)
    data["results"][0]["reported_adjusted_errors"]["PRES"] = value
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


def test_error_components_cannot_disappear(original_report):
    data = copy.deepcopy(original_report)
    del data["results"][0]["reported_adjusted_errors"]["TEMP"]
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


def test_matched_endpoint_evidence_required(original_report):
    data = copy.deepcopy(original_report)
    data["results"][0]["pressure_error_endpoints"] = {"status": "missing_error"}
    with pytest.raises(ValidationError):
        NativeMatchingReport.model_validate(data)


def test_matched_distances_respect_policy(original_report):
    data = copy.deepcopy(original_report)
    data["results"][0]["candidate"]["horizontal_offset_m"] = 100001
    with pytest.raises(ValidationError, match="reviewed limits"):
        NativeMatchingReport.model_validate(data)


def test_partially_blocked_requires_and_preserves_unresolved_reason(original_report):
    data = copy.deepcopy(original_report)
    row = data["results"][0]
    row["matched"] = False
    row["exclusions"] = ["support_unresolved"]
    data["matched_pair_count"] -= 1
    with pytest.raises(ValidationError, match="Partial blocking"):
        NativeMatchingReport.model_validate(data)
    data["status"] = "partially_blocked"
    assert NativeMatchingReport.model_validate(data).matched_pair_count == 5
