"""Bounded in-memory Argo adjusted selection and TEOS-10 quantity conversion.

File verification and provider/client row alignment are caller obligations.
No matching, storage writes, networking, or implicit model-definition repair.
"""

import hashlib
import math

from ..schemas.observations import ObservationCollection
from ..schemas.quantities import (
    AdjustedParameter,
    QuantityEvidence,
    QuantityReport,
    QuantityResult,
)
from ..storage.product_common import ProductError

UNITS = {
    "PRES": {"dbar", "decibar", "decibars"},
    "TEMP": {
        "degree_Celsius",
        "degrees_Celsius",
        "degree_C",
        "degrees_C",
        "degC",
        "deg C",
        "Celsius",
    },
    "PSAL": {"psu", "PSU", "1", "1e-3", "PSS-78", "PSS_78"},
}
DEFINITIONS = {
    "PRES": "sea_pressure_dbar",
    "TEMP": "in_situ_ITS90_C",
    "PSAL": "practical_salinity_PSS78",
}


def _gsw():
    try:
        import gsw
    except ImportError:
        raise ProductError(
            "dependency_unavailable", "Pinned GSW is unavailable."
        ) from None
    if gsw.__version__ != "3.6.23":
        raise ProductError(
            "dependency_version_mismatch", "Pinned GSW version is required."
        )
    return gsw


def potential_temperature(
    sp: float, t: float, p: float, lon: float, lat: float
) -> tuple[float, float]:
    """Verified PSS-78/ITS-90/sea-dbar inputs only; return SA and zero-dbar pt.

    This intentionally narrow prototype domain is not an ocean/wet-mask check.
    Negative SP is rejected before GSW can silently clip it to zero.
    """
    if not all(math.isfinite(v) for v in (sp, t, p, lon, lat)) or not (
        0 <= sp <= 42
        and -2.5 <= t <= 40
        and 0 <= p <= 12000
        and -180 <= lon <= 360
        and -90 <= lat <= 90
    ):
        raise ProductError(
            "quantity_outside_domain", "Quantity inputs exceed the supported domain."
        )
    gsw = _gsw()
    sa = float(gsw.SA_from_SP(sp, p, lon, lat))
    pt = float(gsw.pt0_from_t(sa, t, p))
    if not math.isfinite(sa) or sa < 0 or not math.isfinite(pt):
        raise ProductError(
            "invalid_quantity_result", "Quantity conversion returned invalid values."
        )
    return sa, pt


def derive_quantities(
    collection: ObservationCollection, evidence: QuantityEvidence
) -> QuantityReport:
    """Select A/D adjusted core values without changing the original collection.

    Existing raw-selection eligibility is not reused for adjusted quantities:
    check adjusted QC/mode/bounds plus original time/position QC independently.
    Values already removed upstream are not recovered or replaced from raw.
    """
    collection = ObservationCollection.model_validate_json(collection.model_dump_json())
    evidence = QuantityEvidence.model_validate_json(evidence.model_dump_json())
    if (
        collection.source_id != "argo"
        or not {"PRES", "TEMP", "PSAL"} <= collection.variables.keys()
    ):
        raise ProductError(
            "unsupported_quantity_source", "Core Argo metadata is required."
        )
    if evidence.client_input_sha256 != collection.input_file.sha256:
        raise ProductError(
            "quantity_evidence_mismatch",
            "Evidence does not identify the collection input.",
        )
    provider = {p.name: p for p in evidence.parameters}
    results = []
    for sample in collection.samples:
        selected = {}
        for name in ("PRES", "TEMP", "PSAL"):
            value, info, source = (
                sample.values[name],
                collection.variables[name],
                provider[name],
            )
            exclusions = []
            if value.data_mode not in {"A", "D"}:
                exclusions.append("adjusted_mode_required")
            if value.adjusted is None or not info.adjusted_name:
                exclusions.append("missing_adjusted_value")
            if value.adjusted_qc not in {"1", "2"}:
                exclusions.append("adjusted_qc_rejected")
            if sample.time_qc not in {"1", "2"} or sample.position_qc not in {"1", "2"}:
                exclusions.append("coordinate_qc_rejected")
            if source.definition != DEFINITIONS[name]:
                exclusions.append("source_definition_unresolved")
            if (
                source.units not in UNITS[name]
                or info.adjusted_units not in UNITS[name]
            ):
                exclusions.append("unsupported_units")
            if info.adjusted_valid_min is None or info.adjusted_valid_max is None:
                exclusions.append("client_range_unresolved")
            else:
                low = max(source.valid_min, info.adjusted_valid_min)
                high = min(source.valid_max, info.adjusted_valid_max)
                if low > high:
                    exclusions.append("range_metadata_conflict")
                elif value.adjusted is not None and not low <= value.adjusted <= high:
                    exclusions.append("outside_provider_client_range")
            selected[name] = AdjustedParameter(
                name=name,
                original=value,
                selected_name=info.adjusted_name,
                provider_adjusted_name=source.adjusted_name,
                value=value.adjusted,
                error=value.adjusted_error,
                exclusions=tuple(exclusions),
            )
        p, t, sp = (selected[name] for name in ("PRES", "TEMP", "PSAL"))
        salinity_reasons = [f"{q.name}:{r}" for q in (p, sp) for r in q.exclusions]
        if p.value is not None and not 0 <= p.value <= 12000:
            salinity_reasons.append("pressure_outside_domain")
        if p.value is not None and not (
            collection.selection.pressure_min_dbar
            <= p.value
            <= collection.selection.pressure_max_dbar
        ):
            salinity_reasons.append("adjusted_pressure_outside_original_selection")
        if sp.value is not None and not 0 <= sp.value <= 42:
            salinity_reasons.append("salinity_outside_domain")
        conversion_reasons = [*salinity_reasons, *(f"TEMP:{r}" for r in t.exclusions)]
        sa = pt = None
        if not conversion_reasons:
            try:
                sa, pt = potential_temperature(
                    sp.value, t.value, p.value, sample.longitude, sample.latitude
                )
            except ProductError as error:
                if error.code not in {
                    "quantity_outside_domain",
                    "invalid_quantity_result",
                }:
                    raise
                conversion_reasons.append(error.code)
        if evidence.model_salinity != "practical_salinity_PSS78":
            salinity_reasons.append("model_salinity_unresolved")
        temperature_reasons = list(conversion_reasons)
        if evidence.model_temperature != "potential_temperature":
            temperature_reasons.append("model_temperature_unresolved")
        if evidence.model_temperature_scale != "ITS90":
            temperature_reasons.append(
                "model_temperature_scale_unsupported_or_unresolved"
            )
        if evidence.model_reference_pressure_dbar != 0:
            temperature_reasons.append("model_zero_dbar_reference_unverified")
        results.append(
            QuantityResult(
                sample_id=sample.sample_id,
                source_sample_index=sample.source_sample_index,
                parameters=tuple(selected.values()),
                practical_salinity=sp.value if not salinity_reasons else None,
                absolute_salinity_g_kg=sa,
                potential_temperature_0_dbar_ITS90_C=pt,
                salinity_exclusions=tuple(salinity_reasons),
                temperature_exclusions=tuple(temperature_reasons),
                conversion_exclusions=tuple(conversion_reasons),
            )
        )
    return QuantityReport(
        source_collection_id=collection.collection_id,
        data_mode=collection.data_mode,
        source_collection_canonical_sha256=hashlib.sha256(
            collection.model_dump_json().encode()
        ).hexdigest(),
        evidence=evidence,
        results=tuple(results),
    )
