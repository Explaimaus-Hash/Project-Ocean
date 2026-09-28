"""Latitude-aware GSW conversion in memory; no provider, storage or API work."""

import math

from ..schemas.depth import (
    DepthReport,
    DepthRequest,
    DepthResult,
    PressureSample,
    PressureSensitivity,
)
from ..schemas.observations import ObservationSample
from ..storage.product_common import ProductError

GSW_VERSION = "3.6.23"
MAX_PRESSURE_DBAR = 12000


def pressure_input(sample: ObservationSample) -> PressureSample:
    """Preserve existing selected pressure; never choose/fall back to adjusted."""
    source = ObservationSample.model_validate_json(sample.model_dump_json())
    pressure = source.values["PRES"]
    error = pressure.adjusted_error if pressure.selected_kind == "adjusted" else None
    return PressureSample(
        sample_id=source.sample_id,
        pressure_dbar=source.pressure_dbar,
        latitude=source.latitude,
        source_pressure_name=pressure.selected_source_name,
        selected_kind=pressure.selected_kind,
        source_data_mode=pressure.data_mode,
        pressure_qc=pressure.selected_qc,
        position_qc=source.position_qc,
        time_qc=source.time_qc,
        source_qc_eligible=source.coordinate_qc_eligible,
        pressure_error_dbar=error,
        error_source="selected_adjusted_error" if error is not None else "unknown",
        retained_adjusted_error_dbar=pressure.adjusted_error,
        source_depth_m=source.depth_m,
    )


def _rejection(sample: PressureSample) -> str | None:
    if sample.pressure_dbar is None:
        return "missing_pressure"
    if sample.latitude is None:
        return "missing_latitude"
    if not 0 <= sample.pressure_dbar <= MAX_PRESSURE_DBAR:
        return "pressure_outside_domain"
    if not -90 <= sample.latitude <= 90:
        return "latitude_outside_domain"
    if not sample.source_pressure_name:
        return "missing_source_identity"
    if sample.source_data_mode is None or (
        sample.selected_kind == "adjusted" and sample.source_data_mode not in {"A", "D"}
    ):
        return "source_mode_unsupported"
    if not sample.source_qc_eligible or any(
        flag not in {"1", "2"}
        for flag in (sample.time_qc, sample.position_qc, sample.pressure_qc)
    ):
        return "qc_rejected"
    return None


def _depth(gsw, pressure: float, latitude: float) -> float:
    value = -float(
        gsw.z_from_p(
            pressure, latitude, geo_strf_dyn_height=0, sea_surface_geopotential=0
        )
    )
    if not math.isfinite(value) or value < 0:
        raise ProductError(
            "invalid_depth_result", "Depth conversion returned invalid values."
        )
    return 0.0 if value == 0 else value


def convert_pressures(request: DepthRequest) -> DepthReport:
    """Convert at most 5,000 independently checked rows; keep exclusions aligned."""
    request = DepthRequest.model_validate_json(request.model_dump_json())
    try:
        import gsw
    except ImportError:
        raise ProductError(
            "dependency_unavailable", "Pinned GSW is unavailable."
        ) from None
    if gsw.__version__ != GSW_VERSION:
        raise ProductError(
            "dependency_version_mismatch", "Pinned GSW version is required."
        )
    results = []
    for sample in request.samples:
        reason = _rejection(sample)
        if reason is not None:
            results.append(
                DepthResult(
                    input=sample,
                    status="rejected",
                    reason=reason,
                    depth_m=None,
                    pressure_sensitivity=PressureSensitivity(status="not_converted"),
                )
            )
            continue
        p, lat = sample.pressure_dbar, sample.latitude
        depth = _depth(gsw, p, lat)
        error = sample.pressure_error_dbar
        if error is None:
            sensitivity = PressureSensitivity(status="missing_error")
        else:
            lower, upper = p - error, p + error
            if not math.isfinite(lower) or not math.isfinite(upper):
                raise ProductError(
                    "uncertainty_limit", "Pressure-error endpoints overflow."
                )
            endpoints = {"pressure_lower_dbar": lower, "pressure_upper_dbar": upper}
            if lower < 0 or upper > MAX_PRESSURE_DBAR:
                sensitivity = PressureSensitivity(
                    status="outside_pressure_domain", **endpoints
                )
            else:
                sensitivity = PressureSensitivity(
                    status="evaluated",
                    **endpoints,
                    depth_lower_m=_depth(gsw, lower, lat),
                    depth_upper_m=_depth(gsw, upper, lat),
                )
        results.append(
            DepthResult(
                input=sample,
                status="converted",
                reason=None,
                depth_m=depth,
                pressure_sensitivity=sensitivity,
            )
        )
    return DepthReport(
        gsw_version=gsw.__version__,
        pressure_reference=request.pressure_reference,
        reference_evidence=request.reference_evidence,
        assumptions=request.assumptions,
        source_collection=request.source_collection,
        results=tuple(results),
    )
