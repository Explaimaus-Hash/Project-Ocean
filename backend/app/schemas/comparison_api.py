"""Public prepared-comparison contracts; no private file/evidence records."""

import hashlib
from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, field_validator, model_validator

from .comparison_metrics import MetricsSummary, summarize_residuals
from .exploratory_matching import ExploratoryAssumptions, ExploratoryMatchResult
from .products import Contract, ProductFile

ComparisonId = Annotated[str, Field(pattern=r"^c_[a-f0-9]{24}$")]
Code = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,127}$")]


def comparison_id(report_bytes: bytes) -> str:
    return (
        "c_"
        + hashlib.sha256(b"comparison_snapshot_1\n" + report_bytes).hexdigest()[:24]
    )


class ComparisonMetadata(Contract):
    schema_version: Literal[1] = 1
    comparison_id: ComparisonId
    prepared_at: datetime
    snapshot_semantics: Literal["immutable_result_not_live_source_status"] = (
        "immutable_result_not_live_source_status"
    )
    model_id: str = Field(pattern=r"^m_[a-f0-9]{24}$")
    collection_id: str = Field(pattern=r"^o_[a-f0-9]{24}$")
    observation_acquisition_id: str = Field(pattern=r"^a_[a-f0-9]{24}$")
    model_source: Literal["copernicus"] = "copernicus"
    model_dataset_id: Literal["cmems_mod_glo_phy_my_0.083deg_P1D-m"] = (
        "cmems_mod_glo_phy_my_0.083deg_P1D-m"
    )
    model_dataset_version: Literal["202311"] = "202311"
    observation_source: Literal["argo"] = "argo"
    data_mode: Literal["real", "synthetic"]
    status: Literal["blocked", "evaluated", "partially_blocked"]
    overlap_status: Literal["not_evaluated", "matched", "no_valid_pairs"]
    assurance: Literal["exploratory_assumptions"] = "exploratory_assumptions"
    comparison_ready: Literal[False] = False
    independent_validation: Literal[False] = False
    quantity: Literal["practical_salinity"] = "practical_salinity"
    quantity_units: Literal["1 (PSS-78)"] = "1 (PSS-78)"
    difference_convention: Literal["model_minus_observation"] = (
        "model_minus_observation"
    )
    weighting: Literal["equal_weight_per_matched_sample"] = (
        "equal_weight_per_matched_sample"
    )
    uncertainty: Literal["not_propagated"] = "not_propagated"
    sample_dependence: Literal["unknown_do_not_infer_independent_profiles"] = (
        "unknown_do_not_infer_independent_profiles"
    )
    unresolved_systematic_uncertainty: Literal["time_label_and_vertical_datum"] = (
        "time_label_and_vertical_datum"
    )
    spatial_proxy_limitation: Literal[
        "no_subgrid_coastline_or_observed_bottom_proof"
    ] = "no_subgrid_coastline_or_observed_bottom_proof"
    qc_policy: Literal["argo_D_adjusted_flags_1"] = "argo_D_adjusted_flags_1"
    match_method: Literal["nearest_native_no_fallback"] = "nearest_native_no_fallback"
    assumptions: ExploratoryAssumptions
    assumption_id: str = Field(pattern=r"^ea_[a-f0-9]{64}$")
    blockers: tuple[Code, ...] = Field(max_length=64)
    strict_blockers: tuple[Code, ...] = Field(max_length=64)
    summary: MetricsSummary

    @field_validator("prepared_at")
    @classmethod
    def utc(cls, value):
        if value.utcoffset() != timedelta(0):
            raise ValueError("Explicit UTC preparation time required")
        return value

    @model_validator(mode="after")
    def consistent(self):
        if self.assumption_id != self.assumptions.assumption_id():
            raise ValueError("Assumption identity differs")
        s = self.summary
        if (
            s.total_sample_count
            != s.evaluated_sample_count + s.unevaluated_sample_count
            or s.evaluated_sample_count
            != s.matched_pair_count + s.excluded_sample_count
            or s.metrics_available != bool(s.matched_pair_count)
        ):
            raise ValueError("Comparison counts differ")
        if bool(s.matched_pair_count) != (s.bias is not None and s.rmse is not None):
            raise ValueError("Metric availability differs")
        if not s.matched_pair_count and (s.bias is not None or s.rmse is not None):
            raise ValueError("Empty metrics must be null")
        if self.status == "blocked":
            if (
                not self.blockers
                or s.evaluated_sample_count
                or self.overlap_status != "not_evaluated"
            ):
                raise ValueError("Blocked comparison cannot claim evaluated samples")
        elif self.blockers or s.unevaluated_sample_count:
            raise ValueError("Evaluated comparison must retain every result")
        expected_overlap = (
            "matched"
            if s.matched_pair_count
            else "not_evaluated"
            if self.status != "evaluated"
            else "no_valid_pairs"
        )
        if self.overlap_status != expected_overlap:
            raise ValueError("Comparison overlap differs")
        return self


class ComparisonSample(ExploratoryMatchResult):
    model_minus_observation: FiniteFloat | None
    quantity_units: Literal["1 (PSS-78)"] = "1 (PSS-78)"
    exclusions: tuple[Code, ...] = Field(max_length=64)

    @model_validator(mode="after")
    def residual(self):
        expected = (
            self.candidate.model_value - self.observation_value
            if self.matched
            else None
        )
        if self.model_minus_observation != expected:
            raise ValueError("Residual differs from accepted pair")
        return self


class ComparisonSnapshot(Contract):
    """Bounded prepared public projection; never returned as one full HTTP page."""

    metadata: ComparisonMetadata
    samples: tuple[ComparisonSample, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def consistent(self):
        s = self.metadata.summary
        if len(self.samples) != s.evaluated_sample_count:
            raise ValueError("Prepared sample count differs")
        if len({r.sample_id for r in self.samples}) != len(self.samples) or len(
            {r.source_sample_index for r in self.samples}
        ) != len(self.samples):
            raise ValueError("Duplicate comparison samples")
        residuals = tuple(r.model_minus_observation for r in self.samples if r.matched)
        if len(residuals) != s.matched_pair_count or summarize_residuals(residuals) != (
            s.bias,
            s.rmse,
        ):
            raise ValueError("Prepared metrics differ from samples")
        counts = dict(
            Counter(reason for r in self.samples for reason in set(r.exclusions))
        )
        if counts != s.exclusion_counts:
            raise ValueError("Prepared exclusions differ")
        if (self.metadata.status == "partially_blocked") != any(
            "support_unresolved" in r.exclusions for r in self.samples
        ):
            raise ValueError("Partial support state differs")
        return self


class ComparisonManifest(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["comparison_snapshot_1"] = "comparison_snapshot_1"
    metadata: ComparisonMetadata
    report_file: ProductFile
    result_file: ProductFile


class ComparisonCatalogueEntry(Contract):
    comparison_id: ComparisonId
    availability: Literal["prepared_snapshot", "unavailable"]
    metadata: ComparisonMetadata | None = None
    reason_code: Code | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.availability == "prepared_snapshot":
            if (
                self.metadata is None
                or self.metadata.comparison_id != self.comparison_id
                or self.reason_code is not None
            ):
                raise ValueError("Catalogue metadata differs")
        elif self.metadata is not None or self.reason_code is None:
            raise ValueError("Unavailable entries require reason only")
        return self


class ComparisonCatalogue(Contract):
    schema_version: Literal[1] = 1
    comparisons: tuple[ComparisonCatalogueEntry, ...] = Field(max_length=32)


class ComparisonPage(Contract):
    schema_version: Literal[1] = 1
    metadata: ComparisonMetadata
    offset: int = Field(ge=0, le=5000)
    limit: int = Field(ge=1, le=500)
    matched: bool | None
    total: int = Field(ge=0, le=5000)
    next_offset: Annotated[int, Field(ge=0, le=5000)] | None
    samples: tuple[ComparisonSample, ...] = Field(max_length=500)

    @model_validator(mode="after")
    def pagination(self):
        s = self.metadata.summary
        expected_total = (
            s.evaluated_sample_count
            if self.matched is None
            else s.matched_pair_count
            if self.matched
            else s.excluded_sample_count
        )
        expected_count = min(self.limit, max(0, self.total - self.offset))
        next_offset = (
            self.offset + expected_count
            if self.offset + expected_count < self.total
            else None
        )
        if (
            self.total != expected_total
            or len(self.samples) != expected_count
            or self.next_offset != next_offset
        ):
            raise ValueError("Comparison pagination differs")
        if self.matched is not None and any(
            r.matched != self.matched for r in self.samples
        ):
            raise ValueError("Comparison filter differs")
        return self
