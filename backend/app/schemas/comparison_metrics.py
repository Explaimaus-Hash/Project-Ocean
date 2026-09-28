"""Private descriptive metrics; assumptions are not scientific verification."""

import hashlib
import math
from collections import Counter
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, StrictBool, model_validator

from .exploratory_matching import ExploratoryMatchingReport
from .matching_policy import Digest
from .products import Contract

Count = Annotated[int, Field(strict=True, ge=0, le=5000)]
Reason = Annotated[str, Field(min_length=1, max_length=128)]


def summarize_residuals(values: tuple[float, ...]) -> tuple[float | None, float | None]:
    """Equal-sample mean and RMS; scaled arithmetic avoids square/sum overflow."""
    if len(values) > 5000 or any(not math.isfinite(v) for v in values):
        raise ValueError("Residuals exceed finite/count limits")
    if not values:
        return None, None
    scale = max(abs(v) for v in values)
    if scale == 0:
        return 0.0, 0.0
    normalized = tuple(v / scale for v in values)
    # Dividing the bounded sum, then rescaling, also preserves subnormal means.
    bias = (math.fsum(normalized) / len(values)) * scale
    rmse = math.sqrt(math.fsum(v * v for v in normalized) / len(values)) * scale
    if not math.isfinite(bias) or not math.isfinite(rmse):
        raise ValueError("Metrics cannot be represented as finite numbers")
    return bias, rmse


class ExploratoryResidual(Contract):
    sample_id: str = Field(pattern=r"^s_[a-f0-9]{24}$")
    source_sample_index: int = Field(strict=True, ge=0)
    model_minus_observation: FiniteFloat
    quantity_units: Literal["1 (PSS-78)"] = "1 (PSS-78)"
    assurance: Literal["exploratory_assumptions"] = "exploratory_assumptions"


class MetricsSummary(Contract):
    total_sample_count: Count
    evaluated_sample_count: Count
    matched_pair_count: Count
    excluded_sample_count: Count
    unevaluated_sample_count: Count
    metrics_available: StrictBool
    bias: FiniteFloat | None
    rmse: Annotated[FiniteFloat, Field(ge=0)] | None
    exclusion_counts: dict[Reason, Count] = Field(max_length=128)


class ExploratoryMetricsReport(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["exploratory_metrics_1"] = "exploratory_metrics_1"
    assurance: Literal["exploratory_assumptions"] = "exploratory_assumptions"
    comparison_ready: Literal[False] = False
    independent_validation: Literal[False] = False
    interpretation: Literal["descriptive_only_not_independent_validation"] = (
        "descriptive_only_not_independent_validation"
    )
    weighting: Literal["equal_weight_per_matched_sample"] = (
        "equal_weight_per_matched_sample"
    )
    sample_dependence: Literal["unknown_do_not_infer_independent_profiles"] = (
        "unknown_do_not_infer_independent_profiles"
    )
    uncertainty: Literal["not_propagated"] = "not_propagated"
    difference_convention: Literal["model_minus_observation"] = (
        "model_minus_observation"
    )
    quantity: Literal["practical_salinity"] = "practical_salinity"
    quantity_units: Literal["1 (PSS-78)"] = "1 (PSS-78)"
    data_mode: Literal["real", "synthetic"]
    status: Literal["blocked", "evaluated", "partially_blocked"]
    matching_sha256: Digest
    matching: ExploratoryMatchingReport
    summary: MetricsSummary
    residuals: tuple[ExploratoryResidual, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def recompute(self):
        m = self.matching
        if m.strict_assessment.source_variable != "so":
            raise ValueError("Metrics support practical salinity only")
        if (self.data_mode, self.status) != (m.data_mode, m.status):
            raise ValueError("Metrics cannot change matching mode/status")
        if (
            self.matching_sha256
            != hashlib.sha256(m.model_dump_json().encode()).hexdigest()
        ):
            raise ValueError("Metrics matching identity differs")
        pairs = tuple(row for row in m.results if row.matched)
        expected = tuple(
            (
                r.sample_id,
                r.source_sample_index,
                r.candidate.model_value - r.observation_value,
            )
            for r in pairs
        )
        if (
            tuple(
                (r.sample_id, r.source_sample_index, r.model_minus_observation)
                for r in self.residuals
            )
            != expected
        ):
            raise ValueError("Residuals differ from accepted native pairs")
        bias, rmse = summarize_residuals(tuple(row[2] for row in expected))
        counts = dict(
            sorted(
                Counter(
                    reason for row in m.results for reason in set(row.exclusions)
                ).items()
            )
        )
        total = m.strict_assessment.context.sample_count
        expected_summary = MetricsSummary(
            total_sample_count=total,
            evaluated_sample_count=len(m.results),
            matched_pair_count=len(pairs),
            excluded_sample_count=len(m.results) - len(pairs),
            unevaluated_sample_count=total - len(m.results),
            metrics_available=bool(pairs),
            bias=bias,
            rmse=rmse,
            exclusion_counts=counts,
        )
        if self.summary != expected_summary:
            raise ValueError("Metrics summary differs from actual matching outcomes")
        return self
