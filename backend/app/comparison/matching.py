"""Bounded deterministic synthetic matching kernel; no I/O, metrics or API.

Real input remains blocked until physical support and its integration are verified.
"""

import hashlib
import json
import math
from datetime import datetime

from ..schemas.matching import NativeMatchingInput, NativeMatchingReport
from ..schemas.matching_policy import MatchingContext
from .adjusted_depth import build_adjusted_depth
from .policy import assess_policy
from .preflight import strict_argo_issues

EARTH_RADIUS_M = 6371008.8
MAX_REPORT_BYTES = 1048576


def great_circle_m(lat1, lon1, lat2, lon2):
    """Mean-sphere metres; explicit project convention, not ellipsoid distance."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * (
        math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(max(0.0, min(1.0, h))))


def match_native(request: NativeMatchingInput) -> dict:
    """Return identified pairs/exclusions, never differences or readiness.

    Bounds are engineering limits. Caller allocations are not an OS sandbox.
    Results must be obtained from this function, not hand-constructed for metrics.
    """
    if len(request.values) > 250000 or len(request.collection.samples) > 5000:
        raise ValueError("Matching input budget exceeded")
    encoded = request.model_dump_json().encode()
    if len(encoded) > 16 * 1024 * 1024:
        raise ValueError("Matching snapshot exceeds byte budget")
    r = NativeMatchingInput.model_validate_json(encoded)
    p, c, q = r.policy, r.collection, r.quantities
    canonical = hashlib.sha256(c.model_dump_json().encode()).hexdigest()
    ctx = r.context
    if (
        c.source_id != "argo"
        or c.collection_id != ctx.collection_id
        or c.data_mode != ctx.data_mode
        or canonical != ctx.collection_canonical_sha256
        or q.source_collection_canonical_sha256 != canonical
        or q.source_collection_id != c.collection_id
        or q.data_mode != c.data_mode
        or q.evidence.model_identity != ctx.model_id
        or q.evidence.client_input_sha256 != ctx.client_input_sha256
        or c.input_file.sha256 != ctx.client_input_sha256
        or q.evidence.provider_input_sha256 != ctx.provider_input_sha256
    ):
        raise ValueError("Matching snapshot provenance differs")
    if not (len(c.samples) == len(q.results) == len(r.observation_support)):
        raise ValueError("Matching sample alignment differs")
    if len({s.source_sample_index for s in c.samples}) != len(c.samples):
        raise ValueError("Duplicate native observation indices")
    # Recompute the bridge, including endpoint calculations, not just central depth.
    if r.depths != build_adjusted_depth(c, q, ctx.collection_file_sha256):
        raise ValueError("Adjusted depth provenance/calculation differs")
    checks = []
    for sample, result, support in zip(
        c.samples, q.results, r.observation_support, strict=True
    ):
        key = (sample.sample_id, sample.source_sample_index)
        if key != (support.sample_id, support.source_sample_index):
            raise ValueError("Observation support identity differs")
        qc = strict_argo_issues(sample, result, p)
        issues = (
            result.salinity_exclusions
            if p.quantity == "practical_salinity"
            else result.temperature_exclusions + result.conversion_exclusions
        )
        value = getattr(result, p.quantity)
        checks.append((qc, issues, value))
    counts = {
        "sample_count": len(checks),
        "strict_qc_eligible_count": sum(not qc for qc, _, _ in checks),
        "quantity_eligible_count": sum(
            not bad and v is not None for _, bad, v in checks
        ),
        "joint_eligible_count": sum(
            not qc and not bad and v is not None for qc, bad, v in checks
        ),
    }
    if any(getattr(ctx, name) != count for name, count in counts.items()):
        raise ValueError("Claimed eligibility counts differ from actual samples")
    assessment = assess_policy(p, MatchingContext.model_validate(ctx.model_dump()))
    blockers = list(assessment.blockers)
    if p.data_mode == "real" or ctx.data_mode == "real":
        blockers.append("real_field_and_support_adapter_not_implemented")
    report = {
        "schema_version": 1,
        "processing_version": "matching_native_1",
        "input_sha256": hashlib.sha256(encoded).hexdigest(),
        "policy_id": p.policy_id(),
        "policy": p.model_dump(mode="json"),
        "context": ctx.model_dump(mode="json"),
        "scientific_file_sha256": r.scientific_file_sha256,
        "source_variable": r.source_variable,
        "data_mode": p.data_mode,
        "quantity_units": (
            "1 (PSS-78)"
            if p.quantity == "practical_salinity"
            else "degree_Celsius (ITS-90)"
        ),
        "distance_metric": "great_circle_mean_sphere_6371008.8_m",
        "comparison_ready": False,
        "blockers": blockers,
        "status": "blocked" if blockers else "evaluated",
        "overlap_status": "not_evaluated",
        "matched_pair_count": 0,
        "results": [],
    }
    if blockers:
        return _checked_report(report)
    a = r.axes
    ny, nx, nz = len(a.latitude), len(a.longitude), len(a.depth_m)
    # Track output budget incrementally: do not build an unbounded row list first.
    used = len(json.dumps(report, allow_nan=False).encode())
    for sample, depth, support, (qc, bad, value) in zip(
        c.samples, r.depths.results, r.observation_support, checks, strict=True
    ):
        row = {
            "sample_id": sample.sample_id,
            "source_sample_index": sample.source_sample_index,
            "observation_value": value,
            "observation_longitude": sample.longitude,
            "observation_latitude": sample.latitude,
            "observation_time": sample.time,
            "observation_depth_m": depth.depth_m,
            "pressure_error_endpoints": depth.pressure_sensitivity.model_dump(
                mode="json"
            ),
            "reported_adjusted_errors": {
                v.name: v.error for v in q.results[len(report["results"])].parameters
            },
            "exclusions": list(qc) + list(bad),
            "candidate": None,
            "matched": False,
        }
        reasons = row["exclusions"]
        if not reasons:
            _select(r, sample, depth, support, row, ny, nx, nz)
        row["matched"] = not reasons and row["candidate"] is not None
        size = len(json.dumps(row, allow_nan=False).encode()) + 2
        used += size
        if used > MAX_REPORT_BYTES - 128:
            raise ValueError("Matching report exceeds byte budget; split selection")
        report["results"].append(row)
    report["matched_pair_count"] = sum(row["matched"] for row in report["results"])
    report["overlap_status"] = (
        "matched" if report["matched_pair_count"] else "no_valid_pairs"
    )
    if any("support_unresolved" in row["exclusions"] for row in report["results"]):
        report["status"] = "partially_blocked"
        if not report["matched_pair_count"]:
            report["overlap_status"] = "not_evaluated"
    return _checked_report(report)


def _checked_report(report: dict) -> dict:
    NativeMatchingReport.model_validate(report)
    if len(json.dumps(report, allow_nan=False).encode()) + 1 > MAX_REPORT_BYTES:
        raise ValueError("Matching report exceeds byte budget")
    return report


def _select(r, sample, depth, support, row, ny, nx, nz):
    select_candidate(
        r, sample, depth, support, row, r.policy.tolerances, r.context.time_cells
    )


def select_candidate(r, sample, depth, support, row, limits, time_cells, column=None):
    """Shared numerical selection, not evidence approval or report construction.

    Exploratory callers supply explicitly assumed bounds/support separately;
    the immutable request and its strict evidence are never promoted.
    """
    a, reasons = r.axes, row["exclusions"]
    ny, nx, nz = len(a.latitude), len(a.longitude), len(a.depth_m)
    if not (
        a.latitude[0] <= sample.latitude <= a.latitude[-1]
        and a.longitude[0] <= sample.longitude <= a.longitude[-1]
    ):
        reasons.append("outside_horizontal_support")
        return
    distance, _, _, y, x = min(
        (
            great_circle_m(sample.latitude, sample.longitude, lat, lon),
            a.source_latitude_indices[y],
            a.source_longitude_indices[x],
            y,
            x,
        )
        for y, lat in enumerate(a.latitude)
        for x, lon in enumerate(a.longitude)
    )
    instant = datetime.fromisoformat(sample.time.replace("Z", "+00:00"))
    t = next(
        (i for i, cell in enumerate(time_cells) if cell.contains(instant)),
        None,
    )
    if t is None:
        reasons.append("outside_time_support")
        return
    cell = time_cells[t]
    offset = abs((instant - (cell.start + (cell.end - cell.start) / 2)).total_seconds())
    if depth.status != "converted":
        reasons.append("depth_conversion_rejected")
        return
    vertical, _, z = min(
        (abs(d - depth.depth_m), a.source_depth_indices[i], i)
        for i, d in enumerate(a.depth_m)
    )
    index = ((t * nz + z) * ny + y) * nx + x
    if column is None:
        column = r.columns[(t * ny + y) * nx + x]
    row["candidate"] = {
        "source_time_index": a.source_time_indices[t],
        "source_depth_index": a.source_depth_indices[z],
        "source_latitude_index": a.source_latitude_indices[y],
        "source_longitude_index": a.source_longitude_indices[x],
        "model_time_label": cell.label.isoformat(),
        "time_start": cell.start.isoformat(),
        "time_end": cell.end.isoformat(),
        "model_depth_m": a.depth_m[z],
        "model_latitude": a.latitude[y],
        "model_longitude": a.longitude[x],
        "model_value": r.values[index],
        "horizontal_offset_m": distance,
        "vertical_offset_m": vertical,
        "midpoint_offset_seconds": offset,
    }
    for name, measured, limit in (
        ("horizontal", distance, limits.horizontal_m),
        ("vertical", vertical, limits.vertical_m),
        ("time", offset, limits.time_seconds),
    ):
        if measured > limit:
            reasons.append(name + "_tolerance_exceeded")
    candidate_key = (a.source_latitude_indices[y], a.source_longitude_indices[x])
    if candidate_key != (
        support.candidate_latitude_index,
        support.candidate_longitude_index,
    ):
        reasons.append("support_unresolved")
    if any(
        v is None
        for v in (
            column.wet,
            support.wet,
            support.connected,
            r.valid_mask[index],
            column.shallowest_centre_m,
            column.deepest_centre_m,
            column.bottom_m,
        )
    ):
        reasons.append("support_unresolved")
    if column.wet is False or support.wet is False:
        reasons.append("dry_location")
    if support.connected is False:
        reasons.append("coastline_disconnected")
    if r.valid_mask[index] is False:
        reasons.append("nearest_cell_masked")
    if r.values[index] is None:
        reasons.append("nearest_value_missing")
    sensitivity = depth.pressure_sensitivity
    if sensitivity.status != "evaluated":
        reasons.append("pressure_endpoints_unavailable")
    elif all(
        v is not None
        for v in (column.shallowest_centre_m, column.deepest_centre_m, column.bottom_m)
    ):
        lower = max(a.depth_m[0], column.shallowest_centre_m)
        upper = min(a.depth_m[-1], column.deepest_centre_m, column.bottom_m)
        if not (lower <= a.depth_m[z] <= upper):
            reasons.append("selected_level_outside_local_support")
        if not (
            lower
            <= sensitivity.depth_lower_m
            <= depth.depth_m
            <= sensitivity.depth_upper_m
            <= upper
        ):
            reasons.append("pressure_endpoints_outside_local_support")


def serialize_matches(request: NativeMatchingInput) -> bytes:
    """Always recompute from validated input; no forged report serialization."""
    payload = (json.dumps(match_native(request), allow_nan=False) + "\n").encode()
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Matching report exceeds byte budget")
    return payload
