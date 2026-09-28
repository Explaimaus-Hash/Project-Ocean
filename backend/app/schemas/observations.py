"""Bounded scientific observation contracts; not comparison-ready quantities."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .products import Contract, Identifier, ProductFile, Region

OBSERVATION_PROCESSING_VERSION = "observations_1"
MAX_OBSERVATION_JSON_BYTES = 16 * 1024 * 1024
MAX_OBSERVATION_SAMPLES = 5000
ObservationVariable = Literal[
    "PRES", "TEMP", "PSAL", "GLIDER_DEPTH", "FLUORESCENCE_CHLA"
]
ShortText = Annotated[str, Field(max_length=128)]
QCFlag = Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


class ObservationRequest(Contract):
    region: Region
    start_date: date
    end_date: date
    pressure_min_dbar: FiniteFloat = Field(ge=0, le=12000)
    pressure_max_dbar: FiniteFloat = Field(ge=0, le=12000)
    variables: list[ObservationVariable] = Field(min_length=1, max_length=5)
    value_mode: Literal["raw", "adjusted"]

    @model_validator(mode="after")
    def selection_limits(self) -> "ObservationRequest":
        if not 0 <= (self.end_date - self.start_date).days <= 366:
            raise ValueError("Dates must increase within 366 days")
        if self.pressure_min_dbar > self.pressure_max_dbar:
            raise ValueError("Pressure bounds must increase")
        if (
            len(set(self.variables)) != len(self.variables)
            or "PRES" not in self.variables
        ):
            raise ValueError("Unique variables including PRES are required")
        return self


class ObservationSourceEncoding(Contract):
    scale_factor: FiniteFloat | None = None
    add_offset: FiniteFloat | None = None
    valid_min: FiniteFloat | None = None
    valid_max: FiniteFloat | None = None


class ObservationVariableInfo(Contract):
    source_name: ObservationVariable
    units: ShortText
    long_name: ShortText | None = None
    standard_name: ShortText | None = None
    scientific_definition: Literal["source_definition_not_harmonized"] = (
        "source_definition_not_harmonized"
    )
    raw_name: ShortText | None
    adjusted_name: ShortText | None
    adjusted_error_name: ShortText | None
    adjusted_units: ShortText | None = None
    valid_min: FiniteFloat | None = None
    valid_max: FiniteFloat | None = None
    adjusted_valid_min: FiniteFloat | None = None
    adjusted_valid_max: FiniteFloat | None = None
    range_policy: Literal["declared_bounds_in_decoded_units"] = (
        "declared_bounds_in_decoded_units"
    )
    raw_encoding: ObservationSourceEncoding | None = None
    adjusted_encoding: ObservationSourceEncoding | None = None
    qc_convention: Literal["argo_reference_table_2", "ego_reference_table_2"]
    calibration_status: Literal["not_evaluated"] = "not_evaluated"


class ObservationValue(Contract):
    raw: FiniteFloat | None
    raw_qc: QCFlag | None
    adjusted: FiniteFloat | None
    adjusted_qc: QCFlag | None
    adjusted_error: FiniteFloat | None
    data_mode: Literal["R", "A", "D"] | None
    selected_kind: Literal["raw", "adjusted"]
    selected_source_name: ShortText | None
    selected_value: FiniteFloat | None
    selected_qc: QCFlag | None
    qc_eligible: bool
    exclusions: list[ShortText] = Field(max_length=8)

    @model_validator(mode="after")
    def value_consistency(self) -> "ObservationValue":
        expected = self.raw if self.selected_kind == "raw" else self.adjusted
        flag = self.raw_qc if self.selected_kind == "raw" else self.adjusted_qc
        if self.selected_value != expected or self.selected_qc != flag:
            raise ValueError("Selected value and QC must match the declared kind")
        if self.adjusted_error is not None and self.adjusted_error < 0:
            raise ValueError("Adjusted error must be nonnegative")
        if self.qc_eligible != (not self.exclusions):
            raise ValueError("Eligibility must agree with exclusion reasons")
        if self.qc_eligible and (
            expected is None
            or flag not in {"1", "2"}
            or not self.selected_source_name
            or not self.data_mode
            or (self.selected_kind == "adjusted" and self.data_mode not in {"A", "D"})
        ):
            raise ValueError("Eligible values require valid source flags and mode")
        return self


class ObservationSample(Contract):
    sample_id: Annotated[str, Field(pattern=r"^s_[a-f0-9]{24}$")]
    source_sample_index: int = Field(ge=0)
    source_profile_index: int | None = Field(default=None, ge=0)
    source_level_index: int | None = Field(default=None, ge=0)
    profile_id: Annotated[str, Field(pattern=r"^r_[a-f0-9]{24}$")] | None
    profile_identity_status: Literal["source_profile", "track_only", "ambiguous_points"]
    platform_id: ShortText | None
    cycle_number: int | None = Field(default=None, ge=0)
    direction: Literal["A", "D"] | None
    profile_discriminator: ShortText | None = None
    time: Annotated[str, Field(max_length=32)]
    longitude: FiniteFloat = Field(ge=-180, lt=180)
    latitude: FiniteFloat = Field(ge=-90, le=90)
    source_longitude: FiniteFloat
    pressure_dbar: FiniteFloat
    depth_m: FiniteFloat | None
    time_qc: QCFlag | None
    position_qc: QCFlag | None
    coordinate_qc_eligible: bool
    values: dict[ObservationVariable, ObservationValue] = Field(
        min_length=1, max_length=5
    )

    @model_validator(mode="after")
    def sample_consistency(self) -> "ObservationSample":
        if not self.time.endswith("Z") or "T" not in self.time:
            raise ValueError("Source time must be ISO UTC")
        datetime.fromisoformat(self.time)
        if "PRES" not in self.values:
            raise ValueError("Pressure provenance is required")
        if self.pressure_dbar != self.values["PRES"].selected_value:
            raise ValueError("Pressure must match the selected pressure value")
        if self.coordinate_qc_eligible != self.values["PRES"].qc_eligible:
            raise ValueError("Coordinate eligibility includes pressure QC")
        if self.coordinate_qc_eligible and (
            self.time_qc not in {"1", "2"} or self.position_qc not in {"1", "2"}
        ):
            raise ValueError("Eligible coordinates require time and position QC")
        if not self.coordinate_qc_eligible and any(
            v.qc_eligible for v in self.values.values()
        ):
            raise ValueError("Values cannot be eligible with rejected coordinates")
        depth = self.values.get("GLIDER_DEPTH")
        expected_depth = depth.selected_value if depth and depth.qc_eligible else None
        if self.depth_m != expected_depth or (
            self.depth_m is not None and self.depth_m < 0
        ):
            raise ValueError("Depth requires eligible positive-down source values")
        if (self.profile_id is not None) != (
            self.profile_identity_status == "source_profile"
        ):
            raise ValueError("Profile identity status must match its identifier")
        return self


class ObservationCounts(Contract):
    input_samples: int = Field(ge=0, le=1000000)
    selected_samples: int = Field(ge=0, le=MAX_OBSERVATION_SAMPLES)
    outside_selection: int = Field(ge=0)
    missing_filter_coordinates: int = Field(ge=0)
    coordinate_qc_rejected: int = Field(ge=0)
    variable_qc_rejected: dict[ObservationVariable, int] = Field(max_length=5)


class ObservationCapabilities(Contract):
    tracks: Literal[True] = True
    profiles: bool
    scientific_samples: Literal[True] = True
    display_only: Literal[False] = False
    comparison_ready: Literal[False] = False
    pressure_to_depth_conversion: Literal[False] = False


class ObservationCollection(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["observations_1"] = OBSERVATION_PROCESSING_VERSION
    collection_id: Annotated[str, Field(pattern=r"^o_[a-f0-9]{24}$")]
    source_id: Literal["argo", "ifremer_glider"]
    dataset_id: Identifier
    source_filename: Annotated[str, Field(min_length=1, max_length=255)]
    input_file: ProductFile
    data_mode: Literal["real", "synthetic"]
    client_processing: Literal[
        "local_operator_input_client_processing_unknown", "argopy_expert_no_qc_filter"
    ]
    selection: ObservationRequest
    layout: Literal["argo_profiles", "argo_points", "ego_timeseries"]
    source_time_name: Literal["JULD", "TIME"]
    source_time_units: ShortText
    source_time_calendar: ShortText
    variables: dict[ObservationVariable, ObservationVariableInfo] = Field(
        min_length=1, max_length=5
    )
    samples: list[ObservationSample] = Field(max_length=MAX_OBSERVATION_SAMPLES)
    counts: ObservationCounts
    capabilities: ObservationCapabilities
    qc_policy: Literal["core_flags_1_2_no_fallback_v1"] = (
        "core_flags_1_2_no_fallback_v1"
    )
    warnings: list[ShortText] = Field(max_length=16)

    @model_validator(mode="after")
    def collection_consistency(self) -> "ObservationCollection":
        if self.layout != "ego_timeseries" and self.counts.input_samples > 100000:
            raise ValueError("Argo input sample count exceeds its separate limit")
        if len(self.samples) != self.counts.selected_samples:
            raise ValueError("Selected count does not match samples")
        if self.counts.input_samples != (
            self.counts.selected_samples
            + self.counts.outside_selection
            + self.counts.missing_filter_coordinates
        ):
            raise ValueError("Input accounting does not match")
        if set(self.variables) != set(self.selection.variables):
            raise ValueError("Variable metadata does not match selection")
        if len({sample.sample_id for sample in self.samples}) != len(self.samples):
            raise ValueError("Sample identities must be unique")
        for sample in self.samples:
            if set(sample.values) != set(self.variables):
                raise ValueError("Sample variables do not match metadata")
            region = self.selection.region
            if not (
                region.west <= sample.longitude <= region.east
                and region.south <= sample.latitude <= region.north
                and self.selection.start_date.isoformat()
                <= sample.time[:10]
                <= self.selection.end_date.isoformat()
                and self.selection.pressure_min_dbar
                <= sample.pressure_dbar
                <= self.selection.pressure_max_dbar
            ):
                raise ValueError("Samples must fall within their declared selection")
            for name, value in sample.values.items():
                info = self.variables[name]
                source_name = (
                    info.raw_name
                    if value.selected_kind == "raw"
                    else info.adjusted_name
                )
                if (
                    value.selected_kind != self.selection.value_mode
                    or value.selected_source_name != source_name
                ):
                    raise ValueError("Selected value source does not match metadata")
        if self.capabilities.profiles != any(
            sample.profile_id for sample in self.samples
        ):
            raise ValueError("Profile capability must agree with actual identities")
        if self.counts.coordinate_qc_rejected != sum(
            not sample.coordinate_qc_eligible for sample in self.samples
        ):
            raise ValueError("Coordinate rejection count does not match samples")
        if self.counts.variable_qc_rejected != {
            name: sum(not sample.values[name].qc_eligible for sample in self.samples)
            for name in self.variables
        }:
            raise ValueError("Variable rejection counts do not match samples")
        return self
