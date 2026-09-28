"""Verify existing native fields and adjusted Argo inputs, without matching."""

import hashlib
from pathlib import Path

from ..processing.prepare_model import private_path
from ..processing.quantity_audit import audit_quantities
from ..schemas.depth import serialize_depth_report
from ..schemas.matching_local import LocalMatchingAudit, NativeFieldVerification
from ..schemas.matching_policy import MatchingContext, MatchingPolicy
from ..schemas.model_reading import NativeFieldSnapshot
from ..storage.observations import ObservationStore
from ..storage.product_common import ProductError, describe_file
from .adjusted_depth import build_adjusted_depth
from .model_reader import read_native_field
from .policy import assess_policy, serialize_policy_assessment
from .preflight import local_policy_preflight


def audit_local_matching(root: Path, policy: MatchingPolicy) -> LocalMatchingAudit:
    """Operator-only read chain. Actual missing support is never guessed."""
    policy = MatchingPolicy.model_validate_json(policy.model_dump_json())
    cid, mid, aid = policy.collection_id, policy.model_id, policy.acquisition_id
    paths = {
        "collection": (f"data/observations/{cid}/collection.json", 16 * 1024 * 1024),
        "client": (f"data/raw/acquisitions/{aid}/input.nc", 16 * 1024 * 1024),
        "provider": (
            f"data/raw/acquisitions/{aid}/provider_input.nc",
            16 * 1024 * 1024,
        ),
        "acquisition": (f"data/raw/acquisitions/{aid}/manifest.json", 65536),
        "model": (f"data/models/{mid}/manifest.json", 1024 * 1024),
        "fields": (f"data/models/{mid}/fields.nc", 134217728),
        "metadata": (f"data/models/{mid}/source_metadata.json", 1024 * 1024),
    }
    before = {
        name: describe_file(private_path(root, path), size)
        for name, (path, size) in paths.items()
    }
    original = local_policy_preflight(root, policy)
    source_variable = "so" if policy.quantity == "practical_salinity" else "thetao"
    field = read_native_field(root, mid, source_variable)
    field = NativeFieldSnapshot.model_validate_json(field.model_dump_json())
    collection = ObservationStore(root).collection(cid)
    quantities = audit_quantities(root, cid, aid, mid)
    c = original.context
    if (
        original != assess_policy(policy, c)
        or field.source_variable != source_variable
        or field.manifest_file != before["model"]
        or field.manifest.scientific_file != before["fields"]
        or field.manifest.source_metadata_file != before["metadata"]
        or c.model_manifest_sha256 != before["model"].sha256
        or c.collection_file_sha256 != before["collection"].sha256
        or c.client_input_sha256 != before["client"].sha256
        or c.provider_input_sha256 != before["provider"].sha256
        or field.manifest.model_id != mid
        or field.manifest.identity.provenance.data_mode != collection.data_mode
        or c.data_mode != collection.data_mode
        or quantities.evidence.model_identity != mid
        or quantities.evidence.client_input_sha256 != c.client_input_sha256
        or quantities.evidence.provider_input_sha256 != c.provider_input_sha256
        or quantities.source_collection_canonical_sha256
        != c.collection_canonical_sha256
    ):
        raise ProductError(
            "matching_audit_identity_mismatch", "Verified inputs differ."
        )
    depths = build_adjusted_depth(collection, quantities, before["collection"].sha256)
    digest = hashlib.sha256(serialize_depth_report(depths)).hexdigest()
    context_data = c.model_dump()
    context_data["adjusted_depth_alignment"] = {
        "status": "verified_for_input_snapshot",
        "reference": "Verified adjusted sample/pressure alignment; depth report SHA256 "
        + digest,
    }
    assessment = assess_policy(policy, MatchingContext.model_validate(context_data))
    info = next(
        v for v in field.manifest.identity.variables if v.source_name == source_variable
    )
    finite = sum(v is not None for v in field.values)
    converted = sum(r.status == "converted" for r in depths.results)
    endpoints = sum(
        r.pressure_sensitivity.status == "evaluated" for r in depths.results
    )
    report = LocalMatchingAudit(
        assessment=assessment,
        field=NativeFieldVerification(
            source_variable=source_variable,
            manifest_sha256=field.manifest_file.sha256,
            scientific_file_sha256=field.manifest.scientific_file.sha256,
            source_metadata_sha256=field.manifest.source_metadata_file.sha256,
            axes=field.manifest.identity.axes,
            variable_metadata=info,
            value_count=len(field.values),
            finite_value_count=finite,
            missing_value_count=len(field.values) - finite,
        ),
        adjusted_depth_report=depths,
        adjusted_depth_report_sha256=digest,
        depth_converted_count=converted,
        depth_rejected_count=len(depths.results) - converted,
        pressure_endpoints_evaluated_count=endpoints,
        pressure_endpoints_unavailable_count=len(depths.results) - endpoints,
    )
    after = {
        name: describe_file(private_path(root, path), size)
        for name, (path, size) in paths.items()
    }
    if before != after:
        raise ProductError(
            "matching_inputs_changed", "Inputs changed during verification."
        )
    return report


def serialize_local_audit(report: LocalMatchingAudit) -> bytes:
    """Validated private operator report; no model value arrays or file writes."""
    report = LocalMatchingAudit.model_validate_json(report.model_dump_json())
    serialize_policy_assessment(report.assessment)
    payload = (report.model_dump_json() + "\n").encode()
    if len(payload) > 1048576:
        raise ProductError(
            "matching_audit_report_limit", "Split the observation selection."
        )
    return payload
