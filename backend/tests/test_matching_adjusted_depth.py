"""Synthetic quantity/depth alignment checks; no real source evidence inferred."""

import pytest
from pydantic import ValidationError
from test_quantities import collection as quantity_collection
from test_quantities import evidence

from backend.app.comparison.adjusted_depth import build_adjusted_depth
from backend.app.processing.quantities import derive_quantities
from backend.app.schemas.observations import ObservationCollection
from backend.app.schemas.quantities import QuantityEvidence, QuantityReport
from backend.app.storage.product_common import ProductError

FILE_SHA = "2" * 64


@pytest.fixture(scope="module")
def collection(tmp_path_factory):
    # All mutations below target freshly dumped/revalidated models, so the small
    # source fixture can be prepared once instead of doing fourteen disk jobs.
    return quantity_collection.__wrapped__(tmp_path_factory.mktemp("adjusted_depth"))


def test_adjusted_bridge_preserves_raw_collection(collection):
    original = collection.model_dump_json()
    quantities = derive_quantities(collection, evidence(collection))
    report = build_adjusted_depth(collection, quantities, FILE_SHA)
    row = report.results[0]
    assert row.status == "converted"
    assert row.input.selected_kind == "adjusted"
    assert row.input.pressure_dbar == 5.5
    assert collection.samples[0].pressure_dbar == 5
    assert row.input.source_pressure_name == "PRES_ADJUSTED"
    assert row.input.pressure_error_dbar == 0.1
    assert row.pressure_sensitivity.status == "evaluated"
    assert row.input.source_depth_m is None
    assert report.reference_evidence == "Synthetic provider definition"
    assert report.source_collection.collection_sha256 == FILE_SHA
    assert FILE_SHA != quantities.source_collection_canonical_sha256
    assert not report.comparison_ready
    assert collection.model_dump_json() == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_collection_id", "o_" + "0" * 24),
        ("source_collection_canonical_sha256", "0" * 64),
        ("data_mode", "real"),
        ("results", []),
    ],
)
def test_collection_binding_rejects_changes(collection, field, value):
    data = derive_quantities(collection, evidence(collection)).model_dump(mode="json")
    data[field] = value
    with pytest.raises(ProductError, match="identity"):
        build_adjusted_depth(collection, QuantityReport.model_validate(data), FILE_SHA)


@pytest.mark.parametrize(
    "field,value", [("sample_id", "s_" + "0" * 24), ("source_sample_index", 999)]
)
def test_native_row_identity_checked(collection, field, value):
    data = derive_quantities(collection, evidence(collection)).model_dump(mode="json")
    data["results"][0][field] = value
    with pytest.raises(ProductError, match="identities"):
        build_adjusted_depth(collection, QuantityReport.model_validate(data), FILE_SHA)


def test_forged_selected_pressure_name_rejected(collection):
    data = derive_quantities(collection, evidence(collection)).model_dump(mode="json")
    data["results"][0]["parameters"][0]["selected_name"] = "PRES"
    with pytest.raises(ProductError, match="differs from inputs"):
        build_adjusted_depth(collection, QuantityReport.model_validate(data), FILE_SHA)


@pytest.mark.parametrize(
    "field,value,status,sensitivity",
    [
        ("adjusted", None, "rejected", "not_converted"),
        ("adjusted_qc", "4", "rejected", "not_converted"),
        ("adjusted_error", None, "converted", "missing_error"),
        ("adjusted_error", 10.0, "converted", "outside_pressure_domain"),
    ],
)
def test_no_raw_fallback_or_uncertainty_clamp(
    collection, field, value, status, sensitivity
):
    data = collection.model_dump(mode="json")
    data["samples"][0]["values"]["PRES"][field] = value
    checked = ObservationCollection.model_validate(data)
    quantities = derive_quantities(checked, evidence(checked))
    row = build_adjusted_depth(checked, quantities, FILE_SHA).results[0]
    assert row.status == status
    assert row.pressure_sensitivity.status == sensitivity
    assert row.input.selected_kind == "adjusted"


def test_unknown_pressure_definition_blocks_bridge(collection):
    data = evidence(collection).model_dump(mode="json")
    data["parameters"][0]["definition"] = "unresolved"
    quantities = derive_quantities(collection, QuantityEvidence.model_validate(data))
    with pytest.raises(ProductError, match="Sea-pressure evidence"):
        build_adjusted_depth(collection, quantities, FILE_SHA)


def test_file_hash_validated_separately(collection):
    quantities = derive_quantities(collection, evidence(collection))
    with pytest.raises(ValidationError):
        build_adjusted_depth(collection, quantities, "not-a-hash")
