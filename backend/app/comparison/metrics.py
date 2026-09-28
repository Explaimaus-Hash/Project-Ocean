"""Bounded descriptive summaries of explicitly exploratory salinity matches."""

import hashlib
from collections import Counter
from pathlib import Path

from ..schemas.comparison_metrics import (
    ExploratoryMetricsReport,
    ExploratoryResidual,
    MetricsSummary,
    summarize_residuals,
)
from ..schemas.exploratory_matching import ExploratoryMatchingReport
from ..schemas.matching_policy import MatchingPolicy
from .exploratory import execute_exploratory, serialize_exploratory

MAX_METRICS_BYTES = 1048576


def summarize_exploratory(
    matching: ExploratoryMatchingReport,
) -> ExploratoryMetricsReport:
    """Internal pure boundary, not an authenticator for caller-uploaded JSON.

    Production callers must use execute_exploratory_metrics, which reruns matching
    from verified local inputs. No filtering, tolerance change or profile weighting.
    """
    payload = serialize_exploratory(matching)
    m = ExploratoryMatchingReport.model_validate_json(payload)
    if m.strict_assessment.source_variable != "so":
        raise ValueError("Metrics support practical salinity only")
    residuals = []
    used = len(payload) + 2048
    for row in m.results:
        if not row.matched:
            continue
        residual = ExploratoryResidual(
            sample_id=row.sample_id,
            source_sample_index=row.source_sample_index,
            model_minus_observation=row.candidate.model_value - row.observation_value,
        )
        used += len(residual.model_dump_json().encode()) + 1
        if used > MAX_METRICS_BYTES:
            raise ValueError("Metrics report exceeds byte budget; split selection")
        residuals.append(residual)
    bias, rmse = summarize_residuals(
        tuple(r.model_minus_observation for r in residuals)
    )
    total = m.strict_assessment.context.sample_count
    result = ExploratoryMetricsReport(
        data_mode=m.data_mode,
        status=m.status,
        matching_sha256=hashlib.sha256(m.model_dump_json().encode()).hexdigest(),
        matching=m,
        summary=MetricsSummary(
            total_sample_count=total,
            evaluated_sample_count=len(m.results),
            matched_pair_count=len(residuals),
            excluded_sample_count=len(m.results) - len(residuals),
            unevaluated_sample_count=total - len(m.results),
            metrics_available=bool(residuals),
            bias=bias,
            rmse=rmse,
            exclusion_counts=dict(
                sorted(
                    Counter(
                        reason for row in m.results for reason in set(row.exclusions)
                    ).items()
                )
            ),
        ),
        residuals=tuple(residuals),
    )
    serialize_metrics(result)
    return result


def serialize_metrics(report: ExploratoryMetricsReport) -> bytes:
    """Revalidate derived values/identities and bound the complete private report."""
    # Never trust unchecked Pydantic model copies supplied by an internal caller.
    report = ExploratoryMetricsReport.model_validate_json(report.model_dump_json())
    serialize_exploratory(report.matching)
    payload = (report.model_dump_json() + "\n").encode()
    if len(payload) > MAX_METRICS_BYTES:
        raise ValueError("Metrics report exceeds byte budget; split selection")
    return payload


def execute_exploratory_metrics(
    root: Path, policy: MatchingPolicy, support_id: str
) -> ExploratoryMetricsReport:
    """Rerun authenticated matching; no saved-report input or writes."""
    return summarize_exploratory(execute_exploratory(root, policy, support_id))
