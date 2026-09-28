"""Operator-only local policy preflight, not matching or a readiness endpoint."""

import hashlib
from pathlib import Path

from ..processing.prepare_model import private_path
from ..processing.quantity_audit import audit_quantities
from ..schemas.matching_policy import MatchingContext, MatchingPolicy
from ..schemas.models import ModelManifest
from ..schemas.observations import ObservationSample
from ..schemas.quantities import QuantityResult
from ..storage.observations import ObservationStore
from ..storage.product_common import ProductError, describe_file, read_json
from .policy import assess_policy


def strict_argo_issues(
    sample: ObservationSample, result: QuantityResult, policy: MatchingPolicy
) -> tuple[str, ...]:
    """Extra matching QC, without changing the earlier A/D flags-1/2 reports."""
    sample = ObservationSample.model_validate_json(sample.model_dump_json())
    result = QuantityResult.model_validate_json(result.model_dump_json())
    policy = MatchingPolicy.model_validate_json(policy.model_dump_json())
    if (sample.sample_id, sample.source_sample_index) != (
        result.sample_id,
        result.source_sample_index,
    ):
        return ("sample_identity_mismatch",)
    parameters = {p.name: p for p in result.parameters}
    names = (
        ("PRES", "PSAL")
        if policy.quantity == "practical_salinity"
        else ("PRES", "TEMP", "PSAL")
    )
    issues = []
    if sample.time_qc != "1" or sample.position_qc != "1":
        issues.append("time_or_position_not_qc1")
    for name in names:
        selected = parameters[name]
        if sample.values.get(name) != selected.original:
            issues.append(name + "_provenance_mismatch")
        if selected.original.data_mode != "D":
            issues.append(name + "_delayed_mode_required")
        if selected.original.adjusted_qc != "1":
            issues.append(name + "_adjusted_qc1_required")
        if (
            selected.value is None
            or selected.selected_name is None
            or selected.exclusions
        ):
            issues.append(name + "_adjusted_value_ineligible")
        if selected.error is None:
            issues.append(name + "_adjusted_error_missing")
    error = parameters["PRES"].error
    if error is not None and error > policy.maximum_pressure_error_dbar:
        issues.append("pressure_error_above_20_dbar")
    return tuple(issues)


def local_policy_preflight(root: Path, policy: MatchingPolicy):
    """Current metadata has no verified intervals/masks/datum; keep them unknown.

    This version has no switch to promote missing support evidence. Future
    evidence adapters must verify it against these exact snapshot identities.
    """
    policy = MatchingPolicy.model_validate_json(policy.model_dump_json())
    model_path = private_path(root, f"data/models/{policy.model_id}/manifest.json")
    collection_path = private_path(
        root, f"data/observations/{policy.collection_id}/collection.json"
    )
    model_file = describe_file(model_path, 1024 * 1024)
    collection_file = describe_file(collection_path, 16 * 1024 * 1024)
    model = ModelManifest.model_validate(read_json(model_path, 1024 * 1024))
    collection = ObservationStore(root).collection(policy.collection_id)
    if (
        model.identity.provenance.provider_dataset_id
        != "cmems_mod_glo_phy_my_0.083deg_P1D-m"
    ):
        raise ProductError(
            "unsupported_matching_model", "Daily model policy is required."
        )
    if model.identity.provenance.data_mode != collection.data_mode:
        raise ProductError(
            "matching_data_mode_mismatch", "Model and observation modes differ."
        )
    quantities = audit_quantities(
        root, policy.collection_id, policy.acquisition_id, policy.model_id
    )
    canonical_hash = hashlib.sha256(collection.model_dump_json().encode()).hexdigest()
    if (
        quantities.source_collection_canonical_sha256 != canonical_hash
        or quantities.evidence.client_input_sha256 != collection.input_file.sha256
        or quantities.data_mode != collection.data_mode
        or len(quantities.results) != len(collection.samples)
    ):
        raise ProductError(
            "matching_provenance_mismatch", "Quantity provenance differs."
        )
    strict_count = quantity_count = joint_count = 0
    for sample, result in zip(collection.samples, quantities.results, strict=True):
        strict = not strict_argo_issues(sample, result, policy)
        quantity = not (
            result.salinity_exclusions
            if policy.quantity == "practical_salinity"
            else result.temperature_exclusions
        )
        strict_count += strict
        quantity_count += quantity
        joint_count += strict and quantity
    context = MatchingContext(
        model_id=model.model_id,
        collection_id=collection.collection_id,
        acquisition_id=policy.acquisition_id,
        data_mode=collection.data_mode,
        model_manifest_sha256=model_file.sha256,
        collection_file_sha256=collection_file.sha256,
        collection_canonical_sha256=canonical_hash,
        client_input_sha256=quantities.evidence.client_input_sha256,
        provider_input_sha256=quantities.evidence.provider_input_sha256,
        quantity=policy.quantity,
        sample_count=len(collection.samples),
        strict_qc_eligible_count=strict_count,
        quantity_eligible_count=quantity_count,
        joint_eligible_count=joint_count,
        source_time_indices=model.identity.axes.source_time_indices,
        source_time_labels=model.identity.axes.times,
    )
    if (
        describe_file(model_path, 1024 * 1024) != model_file
        or describe_file(collection_path, 16 * 1024 * 1024) != collection_file
    ):
        raise ProductError(
            "matching_inputs_changed", "Policy inputs changed during preflight."
        )
    return assess_policy(policy, context)
