"""Private, caller-verified native matching inputs; never an HTTP contract."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, field_validator, model_validator

from .depth import DepthReport, PressureSensitivity
from .matching_policy import Digest, MatchingContext, MatchingPolicy, ModelTimeCell
from .models import ModelAxes
from .observations import ObservationCollection
from .products import Contract
from .quantities import QuantityReport


class ColumnSupport(Contract):
    """One time/latitude/longitude column, in that flattened order."""

    wet: bool | None
    shallowest_centre_m: FiniteFloat | None
    deepest_centre_m: FiniteFloat | None
    bottom_m: FiniteFloat | None

    @model_validator(mode="after")
    def ordered(self):
        a, b, c = self.shallowest_centre_m, self.deepest_centre_m, self.bottom_m
        if any(v is not None and v < 0 for v in (a, b, c)):
            raise ValueError("Support depths must be nonnegative")
        if a is not None and b is not None and a > b:
            raise ValueError("Local centre support must increase")
        if b is not None and c is not None and b > c:
            raise ValueError("Centre support exceeds bottom")
        return self


class ObservationSupport(Contract):
    sample_id: str = Field(min_length=1, max_length=64)
    source_sample_index: int = Field(ge=0)
    wet: bool | None
    # Connectivity is only valid for this native candidate, never a global flag.
    candidate_latitude_index: Annotated[int, Field(ge=0)] | None
    candidate_longitude_index: Annotated[int, Field(ge=0)] | None
    connected: bool | None

    @model_validator(mode="after")
    def candidate_identity(self):
        missing_y = self.candidate_latitude_index is None
        missing_x = self.candidate_longitude_index is None
        if missing_y != missing_x or (
            missing_y and (self.wet is not None or self.connected is not None)
        ):
            raise ValueError(
                "Absent candidate requires both indices and support unknown"
            )
        return self


class NativeMatchingInput(Contract):
    """Trusted internal snapshot. File authentication belongs in an adapter.

    Local file assembly exists, but verified physical-support integration remains
    incomplete. The engine rejects real mode; synthetic evidence cannot silently
    become real scientific readiness.
    """

    policy: MatchingPolicy
    context: MatchingContext
    axes: ModelAxes
    scientific_file_sha256: Digest
    source_variable: Literal["so", "thetao"]
    quantity_units: Literal["1 (PSS-78)", "degree_Celsius (ITS-90)"]
    scientific_resolution: Literal["native_no_decimation"] = "native_no_decimation"
    values: tuple[FiniteFloat | None, ...] = Field(max_length=250000)
    valid_mask: tuple[bool | None, ...] = Field(max_length=250000)
    columns: tuple[ColumnSupport, ...] = Field(max_length=250000)
    collection: ObservationCollection
    quantities: QuantityReport
    depths: DepthReport
    observation_support: tuple[ObservationSupport, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def dimensions_and_budget(self):
        expected = (
            ("so", "1 (PSS-78)")
            if self.policy.quantity == "practical_salinity"
            else ("thetao", "degree_Celsius (ITS-90)")
        )
        if (self.source_variable, self.quantity_units) != expected:
            raise ValueError("Native field variable/units differ from policy quantity")
        a = self.axes
        horizontal = len(a.latitude) * len(a.longitude)
        size = len(a.times) * len(a.depth_m) * horizontal
        if size > 250000 or horizontal * len(self.collection.samples) > 1000000:
            raise ValueError("Native matching grid/work budget exceeded")
        if len(self.values) != size or len(self.valid_mask) != size:
            raise ValueError("Field/mask shape differs from native axes")
        if len(self.columns) != len(a.times) * horizontal:
            raise ValueError("Column support shape differs")
        if (
            a.times != self.context.source_time_labels
            or a.source_time_indices != self.context.source_time_indices
        ):
            raise ValueError("Time axes differ from verified context")
        return self


class MatchCandidate(Contract):
    source_time_index: int = Field(ge=0)
    source_depth_index: int = Field(ge=0)
    source_latitude_index: int = Field(ge=0)
    source_longitude_index: int = Field(ge=0)
    model_time_label: datetime
    time_start: datetime
    time_end: datetime
    model_depth_m: FiniteFloat = Field(ge=0)
    model_latitude: FiniteFloat = Field(ge=-90, le=90)
    model_longitude: FiniteFloat = Field(ge=-180, lt=180)
    model_value: FiniteFloat | None
    horizontal_offset_m: FiniteFloat = Field(ge=0)
    vertical_offset_m: FiniteFloat = Field(ge=0)
    midpoint_offset_seconds: FiniteFloat = Field(ge=0)

    @model_validator(mode="after")
    def verified_daily_bounds(self):
        ModelTimeCell(
            source_time_index=self.source_time_index,
            label=self.model_time_label,
            start=self.time_start,
            end=self.time_end,
        )
        return self


class MatchResult(Contract):
    sample_id: str = Field(pattern=r"^s_[a-f0-9]{24}$")
    source_sample_index: int = Field(ge=0)
    observation_value: FiniteFloat | None
    observation_longitude: FiniteFloat = Field(ge=-180, lt=180)
    observation_latitude: FiniteFloat = Field(ge=-90, le=90)
    observation_time: datetime
    observation_depth_m: Annotated[FiniteFloat, Field(ge=0)] | None
    pressure_error_endpoints: PressureSensitivity
    reported_adjusted_errors: dict[
        Literal["PRES", "TEMP", "PSAL"],
        Annotated[FiniteFloat, Field(ge=0)] | None,
    ] = Field(min_length=3, max_length=3)
    exclusions: tuple[Annotated[str, Field(max_length=128)], ...] = Field(max_length=64)
    candidate: MatchCandidate | None
    matched: bool

    @field_validator("observation_time")
    @classmethod
    def utc_observation(cls, value):
        if value.utcoffset() != timedelta(0):
            raise ValueError("Observation time must be explicit UTC")
        return value

    @model_validator(mode="after")
    def outcome(self):
        expected = not self.exclusions and self.candidate is not None
        if self.matched != expected:
            raise ValueError("Match outcome differs from exclusions")
        if self.matched and (
            self.observation_value is None
            or self.candidate.model_value is None
            or self.observation_depth_m is None
        ):
            raise ValueError("Matched values cannot be missing")
        if not self.matched and not self.exclusions:
            raise ValueError("Unmatched samples must retain an exclusion")
        if self.candidate is not None:
            candidate = self.candidate
            if self.observation_depth_m is None or (
                candidate.vertical_offset_m
                != abs(candidate.model_depth_m - self.observation_depth_m)
            ):
                raise ValueError("Candidate depth offset differs from observation")
            if not candidate.time_start <= self.observation_time < candidate.time_end:
                raise ValueError("Candidate interval does not contain observation")
            midpoint = (
                candidate.time_start + (candidate.time_end - candidate.time_start) / 2
            )
            if candidate.midpoint_offset_seconds != abs(
                (self.observation_time - midpoint).total_seconds()
            ):
                raise ValueError("Candidate time offset differs from observation")
        if self.matched:
            sensitivity = self.pressure_error_endpoints
            if sensitivity.status != "evaluated" or not (
                sensitivity.depth_lower_m
                <= self.observation_depth_m
                <= sensitivity.depth_upper_m
            ):
                raise ValueError("Matched depth requires evaluated error endpoints")
            if any(
                self.reported_adjusted_errors[name] is None for name in ("PRES", "PSAL")
            ):
                raise ValueError("Matched samples require reported adjusted errors")
        return self


class NativeMatchingReport(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["matching_native_1"] = "matching_native_1"
    input_sha256: Digest
    policy_id: str = Field(pattern=r"^mp_[a-f0-9]{64}$")
    policy: MatchingPolicy
    context: MatchingContext
    scientific_file_sha256: Digest
    source_variable: Literal["so", "thetao"]
    data_mode: Literal["real", "synthetic"]
    quantity_units: Literal["1 (PSS-78)", "degree_Celsius (ITS-90)"]
    distance_metric: Literal["great_circle_mean_sphere_6371008.8_m"]
    comparison_ready: Literal[False] = False
    blockers: tuple[Annotated[str, Field(max_length=128)], ...] = Field(max_length=64)
    status: Literal["blocked", "evaluated", "partially_blocked"]
    overlap_status: Literal["not_evaluated", "matched", "no_valid_pairs"]
    matched_pair_count: int = Field(ge=0, le=5000)
    results: tuple[MatchResult, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def consistent(self):
        expected = (
            ("so", "1 (PSS-78)")
            if self.policy.quantity == "practical_salinity"
            else ("thetao", "degree_Celsius (ITS-90)")
        )
        if (self.source_variable, self.quantity_units) != expected:
            raise ValueError("Output variable/units differ from policy quantity")
        if self.policy_id != self.policy.policy_id():
            raise ValueError("Result policy identity differs")
        if self.matched_pair_count != sum(row.matched for row in self.results):
            raise ValueError("Pair count differs from results")
        if self.data_mode != self.policy.data_mode:
            raise ValueError("Result data mode differs")
        if len({r.sample_id for r in self.results}) != len(self.results) or len(
            {r.source_sample_index for r in self.results}
        ) != len(self.results):
            raise ValueError("Result sample identities must be unique")
        if self.status == "blocked":
            if (
                not self.blockers
                or self.results
                or self.overlap_status != "not_evaluated"
            ):
                raise ValueError("Blocked matching cannot evaluate overlap")
        elif self.blockers or len(self.results) != self.context.sample_count:
            raise ValueError("Evaluated results must account for every sample")
        if self.status != "blocked":
            if (
                self.policy.tolerances.review != "reviewed_for_selection"
                or not self.context.joint_eligible_count
                or self.context.sample_count > self.policy.max_samples
                or not self.context.source_time_indices
                or any(
                    getattr(self.context, name).status != "verified_for_input_snapshot"
                    for name in (
                        "time_support",
                        "vertical_reference",
                        "wet_mask",
                        "bottom_support",
                        "coastline_connectivity",
                        "adjusted_depth_alignment",
                    )
                )
            ):
                raise ValueError("Evaluated results require satisfied matching policy")
            if any(
                getattr(self.policy, name) != getattr(self.context, name)
                for name in (
                    "model_id",
                    "collection_id",
                    "acquisition_id",
                    "quantity",
                    "data_mode",
                )
            ):
                raise ValueError("Evaluated report context differs from policy")
            unresolved = any("support_unresolved" in r.exclusions for r in self.results)
            if (self.status == "partially_blocked") != unresolved:
                raise ValueError("Partial blocking must reflect unresolved support")
            expected_overlap = (
                "matched"
                if self.matched_pair_count
                else "not_evaluated"
                if unresolved
                else "no_valid_pairs"
            )
            if self.overlap_status != expected_overlap:
                raise ValueError("Overlap status differs from matching outcomes")
            if self.matched_pair_count > self.context.joint_eligible_count:
                raise ValueError("Pair count exceeds jointly eligible samples")
            for row in self.results:
                if row.candidate is not None:
                    candidate = row.candidate
                    cell = next(
                        (
                            c
                            for c in self.context.time_cells
                            if c.source_time_index == candidate.source_time_index
                        ),
                        None,
                    )
                    if cell is None or (
                        candidate.model_time_label,
                        candidate.time_start,
                        candidate.time_end,
                    ) != (cell.label, cell.start, cell.end):
                        raise ValueError(
                            "Candidate daily interval differs from context"
                        )
                if not row.matched:
                    continue
                if (
                    row.reported_adjusted_errors["PRES"]
                    > self.policy.maximum_pressure_error_dbar
                ):
                    raise ValueError("Matched pressure error exceeds policy")
                if (
                    self.policy.quantity != "practical_salinity"
                    and row.reported_adjusted_errors["TEMP"] is None
                ):
                    raise ValueError("Matched temperature requires reported error")
                for distance, limit in (
                    (
                        row.candidate.horizontal_offset_m,
                        self.policy.tolerances.horizontal_m,
                    ),
                    (
                        row.candidate.vertical_offset_m,
                        self.policy.tolerances.vertical_m,
                    ),
                    (
                        row.candidate.midpoint_offset_seconds,
                        self.policy.tolerances.time_seconds,
                    ),
                ):
                    if limit is None or distance > limit:
                        raise ValueError("Matched offsets exceed reviewed limits")
        if self.data_mode == "real" and self.status != "blocked":
            raise ValueError("Real adapter not implemented")
        return self
