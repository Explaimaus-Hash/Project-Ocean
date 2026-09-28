"""Pure preflight rules; no nearest search, pair creation, data I/O or imports."""

from ..schemas.matching_policy import (
    MatchingContext,
    MatchingPolicy,
    MatchingPolicyAssessment,
)


def assess_policy(
    policy: MatchingPolicy, context: MatchingContext
) -> MatchingPolicyAssessment:
    policy = MatchingPolicy.model_validate_json(policy.model_dump_json())
    context = MatchingContext.model_validate_json(context.model_dump_json())
    blockers = []
    for name in (
        "model_id",
        "collection_id",
        "acquisition_id",
        "data_mode",
        "quantity",
    ):
        if getattr(policy, name) != getattr(context, name):
            blockers.append(name + "_mismatch")
    if policy.tolerances.review != "reviewed_for_selection":
        blockers.append("tolerances_unreviewed")
    for name in ("horizontal_m", "vertical_m", "time_seconds"):
        if getattr(policy.tolerances, name) is None:
            blockers.append(name + "_unresolved")
    for name in (
        "time_support",
        "vertical_reference",
        "wet_mask",
        "bottom_support",
        "coastline_connectivity",
        "adjusted_depth_alignment",
    ):
        if getattr(context, name).status != "verified_for_input_snapshot":
            blockers.append(name + "_unresolved")
    if not context.source_time_labels:
        blockers.append("model_time_selection_empty")
    if not context.sample_count:
        blockers.append("observation_selection_empty")
    elif not context.strict_qc_eligible_count:
        blockers.append("no_strict_qc_eligible_observations")
    if not context.quantity_eligible_count:
        blockers.append("quantity_incompatible_or_no_eligible_observations")
    if not context.joint_eligible_count:
        blockers.append("no_jointly_eligible_observations")
    if context.sample_count > policy.max_samples:
        blockers.append("sample_limit")
    return MatchingPolicyAssessment(
        policy_id=policy.policy_id(),
        policy=policy,
        context=context,
        status="blocked" if blockers else "policy_satisfied_not_matched",
        blockers=tuple(blockers),
    )


def serialize_policy_assessment(report: MatchingPolicyAssessment) -> bytes:
    report = MatchingPolicyAssessment.model_validate_json(report.model_dump_json())
    if report != assess_policy(report.policy, report.context):
        raise ValueError("Policy assessment differs from evaluated requirements")
    payload = (report.model_dump_json() + "\n").encode()
    if len(payload) > report.policy.maximum_report_bytes:
        raise ValueError("Policy report exceeds its byte limit")
    return payload
