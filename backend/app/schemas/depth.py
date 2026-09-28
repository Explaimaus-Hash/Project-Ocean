"""Separate pressure-derived depths; never mutate source observation depths."""

from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .observations import QCFlag
from .products import Contract

SampleId = Annotated[str, Field(pattern=r"^s_[a-f0-9]{24}$")]
Nonnegative = Annotated[FiniteFloat, Field(ge=0)]


class PressureSample(Contract):
    sample_id: SampleId
    pressure_dbar: FiniteFloat | None
    latitude: FiniteFloat | None
    source_pressure_name: Annotated[str, Field(min_length=1, max_length=128)] | None
    selected_kind: Literal["raw", "adjusted"]
    source_data_mode: Literal["R", "A", "D"] | None
    pressure_qc: QCFlag | None
    position_qc: QCFlag | None
    time_qc: QCFlag | None
    source_qc_eligible: bool
    pressure_error_dbar: Nonnegative | None
    error_source: Literal["selected_adjusted_error", "operator_raw_error", "unknown"]
    # Preserve this even when raw selection makes it inapplicable to conversion.
    retained_adjusted_error_dbar: Nonnegative | None
    source_depth_m: Nonnegative | None

    @model_validator(mode="after")
    def consistent_error(self) -> "PressureSample":
        if (self.error_source == "unknown") != (self.pressure_error_dbar is None):
            raise ValueError("Missing uncertainty is unknown, not zero")
        if self.error_source == "selected_adjusted_error" and (
            self.selected_kind != "adjusted"
            or self.pressure_error_dbar != self.retained_adjusted_error_dbar
        ):
            raise ValueError("Adjusted error requires selected adjusted pressure")
        if self.error_source == "operator_raw_error" and self.selected_kind != "raw":
            raise ValueError("Raw error cannot describe an adjusted value")
        return self


class DepthCollectionReference(Contract):
    collection_id: Annotated[str, Field(pattern=r"^o_[a-f0-9]{24}$")]
    collection_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    data_mode: Literal["real", "synthetic"]


class DepthRequest(Contract):
    schema_version: Literal[1] = 1
    pressure_units: Literal["dbar"]
    pressure_reference: Literal["sea_pressure_zero_at_surface"]
    reference_evidence: Annotated[str, Field(min_length=1, max_length=2048)]
    assumptions: Literal["zero_dynamic_height_zero_surface_geopotential"]
    source_collection: DepthCollectionReference | None = None
    samples: tuple[PressureSample, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def unique_samples(self) -> "DepthRequest":
        if len({s.sample_id for s in self.samples}) != len(self.samples):
            raise ValueError("Sample identities must be unique")
        return self


class PressureSensitivity(Contract):
    status: Literal[
        "evaluated", "missing_error", "outside_pressure_domain", "not_converted"
    ]
    pressure_lower_dbar: FiniteFloat | None = None
    pressure_upper_dbar: FiniteFloat | None = None
    depth_lower_m: Nonnegative | None = None
    depth_upper_m: Nonnegative | None = None
    interpretation: Literal["pressure_error_endpoints_not_confidence_interval"] = (
        "pressure_error_endpoints_not_confidence_interval"
    )

    @model_validator(mode="after")
    def consistent_bounds(self) -> "PressureSensitivity":
        pressure = (self.pressure_lower_dbar, self.pressure_upper_dbar)
        depth = (self.depth_lower_m, self.depth_upper_m)
        if self.status in {"evaluated", "outside_pressure_domain"}:
            if any(v is None for v in pressure) or pressure[0] > pressure[1]:
                raise ValueError("Pressure endpoints must be present and ordered")
        elif any(v is not None for v in pressure):
            raise ValueError("No pressure endpoints without an error estimate")
        if self.status == "evaluated":
            if any(v is None for v in depth) or depth[0] > depth[1]:
                raise ValueError("Converted endpoints must be present and ordered")
        elif any(v is not None for v in depth):
            raise ValueError("Uncomputed endpoints remain null")
        return self


class DepthResult(Contract):
    input: PressureSample
    status: Literal["converted", "rejected"]
    reason: (
        Literal[
            "missing_pressure",
            "missing_latitude",
            "pressure_outside_domain",
            "latitude_outside_domain",
            "qc_rejected",
            "source_mode_unsupported",
            "missing_source_identity",
        ]
        | None
    )
    depth_m: Nonnegative | None
    pressure_sensitivity: PressureSensitivity
    total_depth_uncertainty_m: None = None
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def converted_or_rejected(self) -> "DepthResult":
        if self.status == "converted":
            if self.depth_m is None or self.reason is not None:
                raise ValueError("Converted results require depth and no rejection")
            if self.pressure_sensitivity.status == "not_converted":
                raise ValueError("Converted result cannot have unconverted sensitivity")
            error = self.input.pressure_error_dbar
            bounds = self.pressure_sensitivity
            if (bounds.status == "missing_error") != (error is None):
                raise ValueError("Sensitivity must reflect available pressure error")
            if error is not None and (
                self.input.pressure_dbar is None
                or bounds.pressure_lower_dbar != self.input.pressure_dbar - error
                or bounds.pressure_upper_dbar != self.input.pressure_dbar + error
            ):
                raise ValueError("Sensitivity endpoints differ from original error")
            if bounds.status == "evaluated" and not (
                bounds.depth_lower_m <= self.depth_m <= bounds.depth_upper_m
            ):
                raise ValueError("Central depth must lie inside evaluated endpoints")
        elif (
            self.depth_m is not None
            or self.reason is None
            or (self.pressure_sensitivity.status != "not_converted")
        ):
            raise ValueError("Rejected rows retain reasons but no derived depth")
        return self


class DepthReport(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["pressure_depth_1"] = "pressure_depth_1"
    method: Literal["negative_gsw_z_from_p"] = "negative_gsw_z_from_p"
    gsw_version: Literal["3.6.23"]
    pressure_reference: Literal["sea_pressure_zero_at_surface"]
    reference_evidence: Annotated[str, Field(min_length=1, max_length=2048)]
    assumptions: Literal["zero_dynamic_height_zero_surface_geopotential"]
    source_collection: DepthCollectionReference | None = None
    dynamic_height_m2_s2: Literal[0] = 0
    sea_surface_geopotential_m2_s2: Literal[0] = 0
    depth_reference: Literal["gsw_zero_sea_pressure_surface_assumption"] = (
        "gsw_zero_sea_pressure_surface_assumption"
    )
    qc_policy: Literal["source_eligible_and_time_position_pressure_flags_1_2"] = (
        "source_eligible_and_time_position_pressure_flags_1_2"
    )
    limitations: tuple[
        Literal[
            "not_ellipsoid_or_verified_model_datum",
            "latitude_dynamic_height_geopotential_uncertainty_unquantified",
            "no_matching_or_raw_adjusted_policy_change",
        ],
        ...,
    ] = (
        "not_ellipsoid_or_verified_model_datum",
        "latitude_dynamic_height_geopotential_uncertainty_unquantified",
        "no_matching_or_raw_adjusted_policy_change",
    )
    results: tuple[DepthResult, ...] = Field(max_length=5000)
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def unique_results(self) -> "DepthReport":
        if len({r.input.sample_id for r in self.results}) != len(self.results):
            raise ValueError("Derived sample identifiers must be unique")
        return self


def serialize_depth_report(report: DepthReport) -> bytes:
    """Operator-sized report, not a new HTTP response or storage publisher."""
    checked = DepthReport.model_validate_json(report.model_dump_json())
    payload = (checked.model_dump_json() + "\n").encode("utf-8")
    if len(payload) > 16 * 1024 * 1024:
        raise ValueError("Depth report exceeds the byte budget")
    return payload
