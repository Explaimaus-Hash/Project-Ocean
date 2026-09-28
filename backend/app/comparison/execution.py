"""Verified local input assembly and fail-closed engine invocation; no writes."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ..processing.quantity_audit import audit_quantities
from ..schemas.matching import ColumnSupport, NativeMatchingInput, ObservationSupport
from ..schemas.matching_execution import LocalMatchingExecution
from ..schemas.matching_local import LocalMatchingAudit
from ..schemas.matching_policy import MatchingPolicy
from ..schemas.model_reading import NativeFieldSnapshot
from ..schemas.spatial_support import SpatialDiagnostics, SpatialPosition
from ..schemas.static_support import StaticSupportSnapshot
from ..storage.observations import ObservationStore
from ..storage.product_common import ProductError
from .local import audit_local_matching, serialize_local_audit
from .matching import match_native
from .model_reader import read_native_field
from .policy import assess_policy
from .spatial_support import diagnose_positions
from .static_reader import read_static_support

MAX_EXECUTION_BYTES = 1048576


@dataclass(frozen=True)
class LoadedMatchingInputs:
    request: NativeMatchingInput
    spatial: SpatialDiagnostics
    static: StaticSupportSnapshot
    audit: LocalMatchingAudit
    field: NativeFieldSnapshot


def load_matching_inputs(
    root: Path, policy: MatchingPolicy, support_id: str
) -> LoadedMatchingInputs:
    """Authenticate inputs without interpreting unresolved scientific support."""
    policy = MatchingPolicy.model_validate_json(policy.model_dump_json())
    audit = audit_local_matching(root, policy)
    ctx = audit.assessment.context
    variable = "so" if policy.quantity == "practical_salinity" else "thetao"
    field = read_native_field(root, policy.model_id, variable)
    static = read_static_support(root, support_id, policy.model_id)
    collection = ObservationStore(root).collection(policy.collection_id)
    quantities = audit_quantities(
        root, policy.collection_id, policy.acquisition_id, policy.model_id
    )
    if (
        field.manifest_file.sha256 != ctx.model_manifest_sha256
        or field.manifest.scientific_file.sha256 != audit.field.scientific_file_sha256
        or field.manifest.source_metadata_file.sha256
        != audit.field.source_metadata_sha256
        or field.manifest_file != static.manifest.model_manifest
        or field.manifest.identity.axes != audit.field.axes
        or static.model_axes != audit.field.axes
        or static.manifest.data_mode != policy.data_mode
        or collection.data_mode != policy.data_mode
        or hashlib.sha256(collection.model_dump_json().encode()).hexdigest()
        != ctx.collection_canonical_sha256
    ):
        raise ProductError(
            "matching_execution_binding_mismatch", "Verified inputs differ."
        )
    spatial = diagnose_positions(
        static,
        tuple(
            SpatialPosition(
                sample_id=p.sample_id,
                source_sample_index=p.source_sample_index,
                latitude=p.latitude,
                longitude=p.longitude,
            )
            for p in collection.samples
        ),
    )
    axes = field.manifest.identity.axes
    # Diagnostic wet nodes/geoid depths are not observation/model support proof.
    # Keep the entire physical-support contract unknown rather than invent a datum.
    unknown = ColumnSupport(
        wet=None, shallowest_centre_m=None, deepest_centre_m=None, bottom_m=None
    )
    support = tuple(
        ObservationSupport(
            sample_id=row.position.sample_id,
            source_sample_index=row.position.source_sample_index,
            candidate_latitude_index=(
                row.candidate.model_latitude_index if row.candidate else None
            ),
            candidate_longitude_index=(
                row.candidate.model_longitude_index if row.candidate else None
            ),
            wet=None,
            connected=None,
        )
        for row in spatial.results
    )
    request = NativeMatchingInput(
        policy=policy,
        context=ctx,
        axes=axes,
        scientific_file_sha256=field.manifest.scientific_file.sha256,
        source_variable=variable,
        quantity_units="1 (PSS-78)" if variable == "so" else "degree_Celsius (ITS-90)",
        values=field.values,
        valid_mask=field.valid_mask,
        columns=(unknown,)
        * (len(axes.times) * len(axes.latitude) * len(axes.longitude)),
        collection=collection,
        quantities=quantities,
        depths=audit.adjusted_depth_report,
        observation_support=support,
    )
    return LoadedMatchingInputs(request, spatial, static, audit, field)


def verify_matching_inputs_unchanged(root: Path, loaded: LoadedMatchingInputs):
    policy = loaded.request.policy
    if (
        audit_local_matching(root, policy) != loaded.audit
        or read_native_field(root, policy.model_id, loaded.request.source_variable)
        != loaded.field
        or read_static_support(root, loaded.static.support_id, policy.model_id)
        != loaded.static
    ):
        raise ProductError(
            "matching_execution_inputs_changed", "Inputs changed during execution."
        )


def execute_local_matching(
    root: Path, policy: MatchingPolicy, support_id: str
) -> LocalMatchingExecution:
    """No caller evidence overrides. Unresolved science blocks before selection."""
    loaded = load_matching_inputs(root, policy, support_id)
    engine = match_native(loaded.request)
    verify_matching_inputs_unchanged(root, loaded)
    result = LocalMatchingExecution(
        engine=engine,
        spatial=loaded.spatial,
        static_manifest_sha256=loaded.static.manifest_file.sha256,
        static_subset_sha256=loaded.static.manifest.subset.sha256,
        local_audit_sha256=hashlib.sha256(
            serialize_local_audit(loaded.audit)
        ).hexdigest(),
    )
    serialize_local_execution(result)
    return result


def serialize_local_execution(report: LocalMatchingExecution) -> bytes:
    report = LocalMatchingExecution.model_validate_json(report.model_dump_json())
    expected = list(assess_policy(report.engine.policy, report.engine.context).blockers)
    if report.engine.data_mode == "real":
        expected.append("real_field_and_support_adapter_not_implemented")
    if tuple(expected) != report.engine.blockers:
        raise ValueError("Execution blockers differ from verified policy context")
    payload = (report.model_dump_json() + "\n").encode()
    if len(payload) > MAX_EXECUTION_BYTES:
        raise ProductError("matching_execution_output_limit", "Split the selection.")
    return payload
