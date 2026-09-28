"""Versioned matching requirements and preflight evidence, not matched pairs."""

import hashlib
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, field_validator, model_validator

from .products import Contract

Text = Annotated[str, Field(min_length=1, max_length=2048)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelId = Annotated[str, Field(pattern=r"^m_[a-f0-9]{24}$")]
CollectionId = Annotated[str, Field(pattern=r"^o_[a-f0-9]{24}$")]


class MatchingTolerances(Contract):
    """No universal defaults: null/unreviewed cannot authorize real matching."""

    horizontal_m: Annotated[FiniteFloat, Field(ge=0, le=100000)] | None = None
    vertical_m: Annotated[FiniteFloat, Field(ge=0, le=1000)] | None = None
    time_seconds: Annotated[FiniteFloat, Field(ge=0, le=86400)] | None = None
    review: Literal["unreviewed", "reviewed_for_selection"] = "unreviewed"
    rationale: Text | None = None

    @model_validator(mode="after")
    def explicit_review(self) -> "MatchingTolerances":
        if self.review == "reviewed_for_selection" and any(
            v is None
            for v in (
                self.horizontal_m,
                self.vertical_m,
                self.time_seconds,
                self.rationale,
            )
        ):
            raise ValueError("Reviewed tolerances need all limits and a rationale")
        return self


class MatchingPolicy(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["matching_policy_1"] = "matching_policy_1"
    model_id: ModelId
    collection_id: CollectionId
    acquisition_id: Annotated[str, Field(pattern=r"^a_[a-f0-9]{24}$")]
    data_mode: Literal["real", "synthetic"]
    quantity: Literal["practical_salinity", "potential_temperature_0_dbar_ITS90_C"]
    tolerances: MatchingTolerances = Field(default_factory=MatchingTolerances)
    method: Literal["nearest_native_no_fallback"] = "nearest_native_no_fallback"
    selection_order: Literal["horizontal_then_time_then_depth_before_masks"] = (
        "horizontal_then_time_then_depth_before_masks"
    )
    tie_break: Literal["lowest_native_source_indices"] = "lowest_native_source_indices"
    boundary_policy: Literal["native_centre_envelope_no_extrapolation"] = (
        "native_centre_envelope_no_extrapolation"
    )
    temporal_policy: Literal["verified_daily_interval_and_midpoint_offset"] = (
        "verified_daily_interval_and_midpoint_offset"
    )
    interval_closure: Literal["left_closed_right_open"] = "left_closed_right_open"
    qc_policy: Literal["argo_D_adjusted_flags_1"] = "argo_D_adjusted_flags_1"
    maximum_pressure_error_dbar: Literal[20] = 20
    uncertainty_policy: Literal[
        "reported_errors_and_full_pressure_endpoint_support"
    ] = "reported_errors_and_full_pressure_endpoint_support"
    missing_uncertainty: Literal["reject_missing_selected_errors_never_zero"] = (
        "reject_missing_selected_errors_never_zero"
    )
    representativeness: Literal[
        "point_vs_daily_cell_mean_not_independent_validation"
    ] = "point_vs_daily_cell_mean_not_independent_validation"
    max_samples: Annotated[int, Field(ge=1, le=5000)] = 5000
    maximum_report_bytes: Literal[1048576] = 1048576

    def policy_id(self) -> str:
        return "mp_" + hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class SupportEvidence(Contract):
    status: Literal["unresolved", "verified_for_input_snapshot"] = "unresolved"
    reference: Text | None = None

    @model_validator(mode="after")
    def reference_required(self) -> "SupportEvidence":
        if self.status == "verified_for_input_snapshot" and self.reference is None:
            raise ValueError("Verified support requires a scoped evidence reference")
        return self


class ModelTimeCell(Contract):
    """Original label remains distinct from verified averaging bounds."""

    source_time_index: Annotated[int, Field(ge=0)]
    label: datetime
    start: datetime
    end: datetime

    @field_validator("label", "start", "end")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("Explicit UTC timestamps are required")
        return value

    @model_validator(mode="after")
    def daily_bounds(self) -> "ModelTimeCell":
        if self.end - self.start != timedelta(days=1):
            raise ValueError("This policy supports verified one-day means only")
        if any(
            (
                self.start.hour,
                self.start.minute,
                self.start.second,
                self.start.microsecond,
            )
        ):
            raise ValueError("Daily averaging bounds must start at midnight UTC")
        return self

    def contains(self, time: datetime) -> bool:
        if time.utcoffset() != timedelta(0):
            raise ValueError("Explicit UTC observation time is required")
        return self.start <= time < self.end


class MatchingContext(Contract):
    """Internal caller evidence bound to exact files; not a public request."""

    model_id: ModelId
    collection_id: CollectionId
    acquisition_id: Annotated[str, Field(pattern=r"^a_[a-f0-9]{24}$")]
    data_mode: Literal["real", "synthetic"]
    model_manifest_sha256: Digest
    collection_file_sha256: Digest
    collection_canonical_sha256: Digest
    client_input_sha256: Digest
    provider_input_sha256: Digest
    quantity: Literal["practical_salinity", "potential_temperature_0_dbar_ITS90_C"]
    sample_count: Annotated[int, Field(ge=0, le=5000)]
    strict_qc_eligible_count: Annotated[int, Field(ge=0, le=5000)]
    quantity_eligible_count: Annotated[int, Field(ge=0, le=5000)]
    joint_eligible_count: Annotated[int, Field(ge=0, le=5000)]
    source_time_indices: tuple[Annotated[int, Field(ge=0)], ...] = Field(max_length=12)
    source_time_labels: tuple[datetime, ...] = Field(max_length=12)
    time_cells: tuple[ModelTimeCell, ...] = Field(default=(), max_length=12)
    time_support: SupportEvidence = Field(default_factory=SupportEvidence)
    vertical_reference: SupportEvidence = Field(default_factory=SupportEvidence)
    wet_mask: SupportEvidence = Field(default_factory=SupportEvidence)
    bottom_support: SupportEvidence = Field(default_factory=SupportEvidence)
    coastline_connectivity: SupportEvidence = Field(default_factory=SupportEvidence)
    adjusted_depth_alignment: SupportEvidence = Field(default_factory=SupportEvidence)

    @model_validator(mode="after")
    def aligned(self) -> "MatchingContext":
        if (
            max(self.strict_qc_eligible_count, self.quantity_eligible_count)
            > self.sample_count
        ):
            raise ValueError("Eligibility counts exceed sample count")
        if self.joint_eligible_count > min(
            self.strict_qc_eligible_count, self.quantity_eligible_count
        ):
            raise ValueError("Joint eligibility exceeds its marginal counts")
        if len(self.source_time_labels) != len(self.source_time_indices):
            raise ValueError("Model time indices and labels must align")
        if len(set(self.source_time_indices)) != len(self.source_time_indices):
            raise ValueError("Native time indices must be unique")
        if any(v.utcoffset() != timedelta(0) for v in self.source_time_labels):
            raise ValueError("Source time labels must be explicit UTC")
        if any(
            a >= b
            for a, b in zip(
                self.source_time_indices, self.source_time_indices[1:], strict=False
            )
        ) or any(
            a >= b
            for a, b in zip(
                self.source_time_labels, self.source_time_labels[1:], strict=False
            )
        ):
            raise ValueError("Native time indices and labels must strictly increase")
        if self.time_support.status == "verified_for_input_snapshot":
            if (
                not self.time_cells
                or tuple(c.source_time_index for c in self.time_cells)
                != self.source_time_indices
            ):
                raise ValueError(
                    "Verified intervals must cover every selected native time"
                )
            if tuple(c.label for c in self.time_cells) != self.source_time_labels:
                raise ValueError("Verified intervals cannot rewrite source labels")
            if any(
                a.end > b.start
                for a, b in zip(self.time_cells, self.time_cells[1:], strict=False)
            ):
                raise ValueError(
                    "Verified intervals must be ordered and non-overlapping"
                )
        elif self.time_cells:
            raise ValueError("Do not attach inferred intervals to unresolved evidence")
        return self


class MatchingPolicyAssessment(Contract):
    schema_version: Literal[1] = 1
    policy_id: Annotated[str, Field(pattern=r"^mp_[a-f0-9]{64}$")]
    policy: MatchingPolicy
    context: MatchingContext
    status: Literal["blocked", "policy_satisfied_not_matched"]
    blockers: tuple[Annotated[str, Field(max_length=128)], ...] = Field(max_length=32)
    overlap_status: Literal["not_evaluated"] = "not_evaluated"
    matched_pair_count: Literal[0] = 0
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> "MatchingPolicyAssessment":
        if self.policy_id != self.policy.policy_id():
            raise ValueError("Policy digest differs")
        if (self.status == "blocked") != bool(self.blockers):
            raise ValueError("Status must agree with blockers")
        return self
