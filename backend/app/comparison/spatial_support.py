"""Candidate-bound grid diagnostics; never certify off-grid ocean support."""

import hashlib
import json
from bisect import bisect_left
from pathlib import Path

from ..schemas.matching_policy import MatchingPolicy
from ..schemas.spatial_support import (
    GridColumnDiagnostic,
    SpatialDiagnosticRow,
    SpatialDiagnostics,
    SpatialPosition,
)
from ..schemas.static_support import StaticSupportSnapshot
from ..storage.observations import ObservationStore
from ..storage.product_common import ProductError
from .local import audit_local_matching
from .matching import great_circle_m
from .static_reader import read_static_support

MAX_CHECKS = 1000000
MAX_OUTPUT = 1048576


def brackets(axis, value):
    """Inclusive centre envelope; exact centres use one index, not extrapolation."""
    if value < axis[0] or value > axis[-1]:
        return ()
    i = bisect_left(axis, value)
    return (i,) if axis[i] == value else (i - 1, i)


def diagnose_positions(
    snapshot: StaticSupportSnapshot, positions: tuple[SpatialPosition, ...]
) -> SpatialDiagnostics:
    """Pure internal calculation; callers must verify files, not just supply hashes."""
    if len(positions) > 5000:
        raise ValueError("Spatial sample limit")
    s = StaticSupportSnapshot.model_validate_json(snapshot.model_dump_json())
    a = s.model_axes
    ny, nx = len(a.latitude), len(a.longitude)
    if ny * nx * len(positions) > MAX_CHECKS:
        raise ValueError("Spatial work limit; split selection")
    points = tuple(SpatialPosition.model_validate(p.model_dump()) for p in positions)
    if len({p.sample_id for p in points}) != len(points) or len(
        {p.source_sample_index for p in points}
    ) != len(points):
        raise ValueError("Duplicate observation identity")

    columns = {}

    def column(y, x):
        if (y, x) not in columns:
            cell, count = y * nx + x, ny * nx
            wet = tuple(bool(s.mask[z * count + cell]) for z in range(50))
            if any(
                first and not second
                for first, second in zip(wet, wet[1:], strict=False)
            ):
                raise ValueError("Noncontiguous wet column")
            depths = [-s.source_elevation_m[z] for z in range(50) if wet[z]]
            columns[y, x] = GridColumnDiagnostic(
                model_latitude_index=a.source_latitude_indices[y],
                model_longitude_index=a.source_longitude_indices[x],
                static_latitude_index=s.manifest.source_latitude_indices[y],
                static_longitude_index=s.manifest.source_longitude_indices[x],
                surface_wet=wet[-1],
                prepared_level_wet=tuple(
                    wet[z] for z in s.model_depth_to_source_elevation_index
                ),
                full_mask_shallowest_depth_coordinate_m=min(depths) if depths else None,
                full_mask_deepest_depth_coordinate_m=max(depths) if depths else None,
                deptho_below_geoid_m=s.deptho_m[cell],
                deptho_lev_uninterpreted=s.deptho_lev[cell],
            )
        return columns[y, x]

    rows, used = [], 2048  # Reserved envelope; final serializer checks exact bytes.
    for p in points:
        ys, xs = brackets(a.latitude, p.latitude), brackets(a.longitude, p.longitude)
        candidate, offset, stencil, state, member = (
            None,
            None,
            (),
            "not_evaluated",
            None,
        )
        if ys and xs:
            offset, _, _, y, x = min(
                (
                    great_circle_m(p.latitude, p.longitude, lat, lon),
                    a.source_latitude_indices[y],
                    a.source_longitude_indices[x],
                    y,
                    x,
                )
                for y, lat in enumerate(a.latitude)
                for x, lon in enumerate(a.longitude)
            )
            candidate = column(y, x)
            stencil = tuple(column(y, x) for y in ys for x in xs)
            wet = sum(c.surface_wet for c in stencil)
            state = (
                "all_wet" if wet == len(stencil) else "all_dry" if wet == 0 else "mixed"
            )
            member = candidate in stencil
        row = SpatialDiagnosticRow(
            position=p,
            status="grid_diagnostic_only" if candidate else "outside_centre_envelope",
            candidate=candidate,
            horizontal_offset_m=offset,
            stencil=stencil,
            stencil_surface=state,
            candidate_in_stencil=member,
        )
        used += len(row.model_dump_json().encode()) + 2
        if used > MAX_OUTPUT:
            raise ValueError("Spatial output limit; split selection")
        rows.append(row)
    return SpatialDiagnostics(
        support_id=s.support_id,
        model_id=s.manifest.model_id,
        data_mode=s.manifest.data_mode,
        static_snapshot_sha256=hashlib.sha256(s.model_dump_json().encode()).hexdigest(),
        results=tuple(rows),
    )


def audit_spatial_support(root: Path, policy: MatchingPolicy, support_id: str) -> dict:
    """Verify real local input chain before/after diagnostics; no kernel invocation."""
    audit = audit_local_matching(root, policy)
    s = read_static_support(root, support_id, policy.model_id)
    collection = ObservationStore(root).collection(policy.collection_id)
    ctx = audit.assessment.context
    canonical = hashlib.sha256(collection.model_dump_json().encode()).hexdigest()
    if (
        s.manifest.model_manifest.sha256 != ctx.model_manifest_sha256
        or s.model_axes != audit.field.axes
        or s.manifest.data_mode != ctx.data_mode
        or collection.data_mode != ctx.data_mode
        or collection.source_id != "argo"
        or collection.collection_id != ctx.collection_id
        or canonical != ctx.collection_canonical_sha256
    ):
        raise ProductError("spatial_input_binding_mismatch", "Spatial inputs differ.")
    report = diagnose_positions(
        s,
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
    if (
        audit_local_matching(root, policy) != audit
        or read_static_support(root, support_id, policy.model_id) != s
    ):
        raise ProductError("spatial_inputs_changed", "Inputs changed during audit.")
    result = report.model_dump(mode="json")
    result.update(
        policy_id=policy.policy_id(),
        collection_id=collection.collection_id,
        collection_file_sha256=ctx.collection_file_sha256,
        collection_canonical_sha256=canonical,
        model_manifest_sha256=ctx.model_manifest_sha256,
        static_manifest_sha256=s.manifest_file.sha256,
        static_subset_sha256=s.manifest.subset.sha256,
        remaining_matching_blockers=list(audit.assessment.blockers),
        matched_pair_count=0,
        overlap_status="not_evaluated",
        sample_scope="all_collection_positions_not_qc_accepted_pairs",
    )
    if len(json.dumps(result, allow_nan=False).encode()) + 1 > MAX_OUTPUT:
        raise ValueError("Spatial output limit; split selection")
    return result
