"""Pure adjusted-pressure bridge; caller verifies input files, never mutates them."""

import hashlib

from ..processing.depth import convert_pressures
from ..processing.quantities import derive_quantities
from ..schemas.depth import (
    DepthCollectionReference,
    DepthReport,
    DepthRequest,
    PressureSample,
)
from ..schemas.observations import ObservationCollection
from ..schemas.quantities import QuantityReport
from ..storage.product_common import ProductError


def build_adjusted_depth(
    collection: ObservationCollection,
    quantities: QuantityReport,
    collection_file_sha256: str,
) -> DepthReport:
    """Bind adjusted pressure to quantity rows before diagnostic GSW conversion.

    The file hash is caller-verified and distinct from canonical JSON identity.
    This is not file authentication, model-datum evidence or strict matching QC.
    The matching engine must still apply D-mode/QC1 and all support/error gates.
    """
    collection = ObservationCollection.model_validate_json(collection.model_dump_json())
    quantities = QuantityReport.model_validate_json(quantities.model_dump_json())
    reference = DepthCollectionReference(
        collection_id=collection.collection_id,
        collection_sha256=collection_file_sha256,
        data_mode=collection.data_mode,
    )
    canonical = hashlib.sha256(collection.model_dump_json().encode()).hexdigest()
    if (
        quantities.source_collection_id != collection.collection_id
        or quantities.source_collection_canonical_sha256 != canonical
        or quantities.data_mode != collection.data_mode
        or quantities.evidence.client_input_sha256 != collection.input_file.sha256
        or len(quantities.results) != len(collection.samples)
    ):
        raise ProductError(
            "adjusted_depth_provenance_mismatch",
            "Quantity collection identity differs.",
        )
    identities = tuple(
        (sample.sample_id, sample.source_sample_index) for sample in collection.samples
    )
    if len({index for _, index in identities}) != len(
        identities
    ) or identities != tuple(
        (row.sample_id, row.source_sample_index) for row in quantities.results
    ):
        raise ProductError(
            "adjusted_depth_sample_mismatch", "Quantity sample identities differ."
        )
    for sample, row in zip(collection.samples, quantities.results, strict=True):
        if any(sample.values.get(p.name) != p.original for p in row.parameters):
            raise ProductError(
                "adjusted_depth_provenance_mismatch",
                "Original parameter values differ.",
            )
    # Re-evaluate selected names, metadata/range exclusions and conversions rather
    # than allowing an otherwise schema-valid report to clear its own QC gates.
    if quantities != derive_quantities(collection, quantities.evidence):
        raise ProductError(
            "adjusted_depth_quantity_mismatch", "Quantity report differs from inputs."
        )
    provider = next(p for p in quantities.evidence.parameters if p.name == "PRES")
    if provider.definition != "sea_pressure_dbar":
        raise ProductError(
            "adjusted_depth_reference_unresolved", "Sea-pressure evidence is required."
        )
    samples = []
    for sample, row in zip(collection.samples, quantities.results, strict=True):
        pressure = next(p for p in row.parameters if p.name == "PRES")
        samples.append(
            PressureSample(
                sample_id=sample.sample_id,
                pressure_dbar=pressure.value,
                latitude=sample.latitude,
                source_pressure_name=pressure.selected_name,
                selected_kind="adjusted",
                source_data_mode=pressure.original.data_mode,
                pressure_qc=pressure.original.adjusted_qc,
                position_qc=sample.position_qc,
                time_qc=sample.time_qc,
                source_qc_eligible=not pressure.exclusions,
                pressure_error_dbar=pressure.error,
                error_source=(
                    "selected_adjusted_error"
                    if pressure.error is not None
                    else "unknown"
                ),
                retained_adjusted_error_dbar=pressure.original.adjusted_error,
                source_depth_m=sample.depth_m,
            )
        )
    return convert_pressures(
        DepthRequest(
            pressure_units="dbar",
            pressure_reference="sea_pressure_zero_at_surface",
            reference_evidence=provider.definition_evidence,
            assumptions="zero_dynamic_height_zero_surface_geopotential",
            source_collection=reference,
            samples=tuple(samples),
        )
    )
