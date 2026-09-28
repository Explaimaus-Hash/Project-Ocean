"""Explicit opt-in shallow salinity exploration; never promotes strict evidence."""

import json
from datetime import timedelta
from pathlib import Path

from ..schemas.exploratory_matching import (
    ExploratoryAssumptions,
    ExploratoryMatchingReport,
)
from ..schemas.matching import ColumnSupport, NativeMatchingInput, ObservationSupport
from ..schemas.matching_policy import MatchingPolicy, ModelTimeCell
from ..schemas.spatial_support import SpatialPosition
from ..schemas.static_support import StaticSupportSnapshot
from .execution import load_matching_inputs, verify_matching_inputs_unchanged
from .matching import match_native, select_candidate
from .policy import assess_policy
from .preflight import strict_argo_issues
from .spatial_support import diagnose_positions

MAX_REPORT_BYTES = 1048576
ASSUMABLE_BLOCKERS = frozenset(
    {
        "tolerances_unreviewed",
        "horizontal_m_unresolved",
        "vertical_m_unresolved",
        "time_seconds_unresolved",
        "time_support_unresolved",
        "vertical_reference_unresolved",
        "wet_mask_unresolved",
        "bottom_support_unresolved",
        "coastline_connectivity_unresolved",
        "real_field_and_support_adapter_not_implemented",
    }
)


def _support(diagnostic):
    """Resolution-limited proxy, NOT observed wetness or datum verification."""
    unknown = ColumnSupport(
        wet=None, shallowest_centre_m=None, deepest_centre_m=None, bottom_m=None
    )
    c = diagnostic.candidate
    support = ObservationSupport(
        sample_id=diagnostic.position.sample_id,
        source_sample_index=diagnostic.position.source_sample_index,
        candidate_latitude_index=c.model_latitude_index if c else None,
        candidate_longitude_index=c.model_longitude_index if c else None,
        wet=None,
        connected=None,
    )
    if c is None:
        return unknown, support, None
    if diagnostic.stencil_surface != "all_wet" or not diagnostic.candidate_in_stencil:
        return unknown, support, "exploratory_grid_support_rejected"
    columns = (c,) + diagnostic.stencil
    if any(
        v is None
        for col in columns
        for v in (
            col.full_mask_shallowest_depth_coordinate_m,
            col.full_mask_deepest_depth_coordinate_m,
            col.deptho_below_geoid_m,
        )
    ):
        return unknown, support, "support_unresolved"
    if any(
        col.full_mask_deepest_depth_coordinate_m > col.deptho_below_geoid_m
        for col in columns
    ):
        return unknown, support, "support_unresolved"
    lower = max(col.full_mask_shallowest_depth_coordinate_m for col in columns)
    upper = min(col.full_mask_deepest_depth_coordinate_m for col in columns)
    bottom = min(col.deptho_below_geoid_m for col in columns)
    if lower > min(upper, bottom):
        return unknown, support, "support_unresolved"
    return (
        ColumnSupport(
            wet=True,
            shallowest_centre_m=lower,
            deepest_centre_m=min(upper, bottom),
            bottom_m=bottom,
        ),
        ObservationSupport.model_validate(
            {**support.model_dump(), "wet": True, "connected": True}
        ),
        None,
    )


def match_exploratory(request: NativeMatchingInput, static: StaticSupportSnapshot):
    """Internal authenticated-reader boundary. Recompute diagnostics and QC.

    No caller-defined assumptions, verified-context overrides or synthetic relabels.
    Source-specific daily/version checks also occur in the local adapter.
    """
    # Strict engine revalidates identities, limits, depth calculations and QC counts.
    strict = match_native(request)
    r = NativeMatchingInput.model_validate_json(request.model_dump_json())
    static = StaticSupportSnapshot.model_validate_json(static.model_dump_json())
    if (
        static.model_axes != r.axes
        or static.manifest.model_id != r.policy.model_id
        or static.manifest.data_mode != r.policy.data_mode
        or static.manifest.model_manifest.sha256 != r.context.model_manifest_sha256
    ):
        raise ValueError("Exploratory static binding differs")
    spatial = diagnose_positions(
        static,
        tuple(
            SpatialPosition(
                sample_id=s.sample_id,
                source_sample_index=s.source_sample_index,
                latitude=s.latitude,
                longitude=s.longitude,
            )
            for s in r.collection.samples
        ),
    )
    assumptions = ExploratoryAssumptions()
    blockers = [b for b in strict["blockers"] if b not in ASSUMABLE_BLOCKERS]
    if r.source_variable != "so":
        blockers.append("exploratory_temperature_not_supported")
    if r.axes.depth_m[-1] > assumptions.maximum_model_depth_m:
        blockers.append("exploratory_shallow_selection_required")
    if any(t.hour or t.minute or t.second or t.microsecond for t in r.axes.times):
        blockers.append("exploratory_midnight_labels_required")
    cells = (
        ()
        if blockers
        else tuple(
            ModelTimeCell(
                source_time_index=i, label=t, start=t, end=t + timedelta(days=1)
            )
            for i, t in zip(r.axes.source_time_indices, r.axes.times, strict=True)
        )
    )
    if r.context.time_cells and cells and r.context.time_cells != cells:
        blockers.append("exploratory_time_assumption_conflicts_with_verified_bounds")
        cells = ()
    report = dict(
        data_mode=r.policy.data_mode,
        assumptions=assumptions.model_dump(mode="json"),
        assumption_id=assumptions.assumption_id(),
        strict_assessment=strict,
        spatial_diagnostics=spatial.model_dump(mode="json"),
        static_manifest_sha256=static.manifest_file.sha256,
        static_subset_sha256=static.manifest.subset.sha256,
        time_cells=[c.model_dump(mode="json") for c in cells],
        blockers=blockers,
        status="blocked" if blockers else "evaluated",
        overlap_status="not_evaluated",
        matched_pair_count=0,
        results=[],
    )
    if blockers:
        return _checked(report)
    used = len(json.dumps(report, allow_nan=False).encode())
    for sample, quantity, depth, diagnostic in zip(
        r.collection.samples,
        r.quantities.results,
        r.depths.results,
        spatial.results,
        strict=True,
    ):
        reasons = list(strict_argo_issues(sample, quantity, r.policy))
        reasons.extend(quantity.salinity_exclusions)
        if quantity.practical_salinity is None and not reasons:
            reasons.append("quantity_value_missing")
        row = dict(
            assurance="exploratory_assumptions",
            sample_id=sample.sample_id,
            source_sample_index=sample.source_sample_index,
            observation_value=quantity.practical_salinity,
            observation_longitude=sample.longitude,
            observation_latitude=sample.latitude,
            observation_time=sample.time,
            observation_depth_m=depth.depth_m,
            pressure_error_endpoints=depth.pressure_sensitivity.model_dump(mode="json"),
            reported_adjusted_errors={v.name: v.error for v in quantity.parameters},
            exclusions=reasons,
            candidate=None,
            matched=False,
        )
        if not reasons:
            column, support, failure = _support(diagnostic)
            if failure:
                reasons.append(failure)
            else:
                select_candidate(
                    r, sample, depth, support, row, assumptions, cells, column
                )
        row["matched"] = not reasons and row["candidate"] is not None
        used += len(json.dumps(row, allow_nan=False).encode()) + 2
        if used > MAX_REPORT_BYTES - 1024:
            raise ValueError("Exploratory report budget exceeded; split selection")
        report["results"].append(row)
    report["matched_pair_count"] = sum(row["matched"] for row in report["results"])
    unresolved = any(
        "support_unresolved" in row["exclusions"] for row in report["results"]
    )
    report["status"] = "partially_blocked" if unresolved else "evaluated"
    report["overlap_status"] = (
        "matched"
        if report["matched_pair_count"]
        else "not_evaluated"
        if unresolved
        else "no_valid_pairs"
    )
    return _checked(report)


def _checked(report):
    result = ExploratoryMatchingReport.model_validate(report)
    serialize_exploratory(result)
    return result


def serialize_exploratory(report: ExploratoryMatchingReport) -> bytes:
    report = ExploratoryMatchingReport.model_validate_json(report.model_dump_json())
    strict = report.strict_assessment
    expected = list(assess_policy(strict.policy, strict.context).blockers)
    if strict.data_mode == "real":
        expected.append("real_field_and_support_adapter_not_implemented")
    if tuple(expected) != strict.blockers:
        raise ValueError("Strict assessment blockers differ")
    retained = set(expected) - ASSUMABLE_BLOCKERS
    if not retained.issubset(report.blockers):
        raise ValueError("Exploration cannot bypass non-assumable blockers")
    payload = (report.model_dump_json() + "\n").encode()
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Exploratory report exceeds byte budget")
    return payload


def execute_exploratory(root: Path, policy: MatchingPolicy, support_id: str):
    loaded = load_matching_inputs(root, policy, support_id)
    provenance = loaded.field.manifest.identity.provenance
    if (
        provenance.provider_dataset_id != "cmems_mod_glo_phy_my_0.083deg_P1D-m"
        or provenance.source_version != "202311"
    ):
        raise ValueError("Exploration requires the supported daily 202311 source")
    report = match_exploratory(loaded.request, loaded.static)
    verify_matching_inputs_unchanged(root, loaded)
    return report
