"""Operator-only chunk reuse across up to twenty immutable surface products.

Every output keeps the ordinary preparation limits. Decoded source tiles are
separately capped at 16 MiB; output variable caches use only 256 KiB each.
"""

import math
import os
import shutil
import tempfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from ..schemas.products import PreparationRequest, ProductManifest
from ..storage.product_common import ProductError, contained, describe_file, load_limits
from .prepare_bio_roms import (
    _axes,
    _check_unchanged,
    _cleanup_private,
    _existing,
    _product_id,
    _publish_directory,
    _selection,
    _variables,
    _verified_input,
    _write_dataset,
)


def prepare_archive_group(
    requests: list[PreparationRequest], root: Path, *, data_mode: str = "real"
) -> list[ProductManifest]:
    """Read each spatial tile once for an at-most-80-source-time window."""
    import numpy as np
    from netCDF4 import Dataset

    if not 1 <= len(requests) <= 20 or data_mode not in {"real", "synthetic"}:
        raise ProductError("archive_limit", "Invalid bounded archive group.")
    first = requests[0]
    if any(
        (r.dataset_id, r.variables, r.region)
        != (first.dataset_id, first.variables, first.region)
        for r in requests
    ):
        raise ProductError("archive_selection", "Group variables/region must match.")
    root = root.resolve()
    limits = load_limits(root)
    definition, report, raw = _verified_input(first, root)
    processed = contained(root, "data/processed")
    cached = contained(root, "data/cache")
    pending = []
    results = []
    try:
        with Dataset(raw) as source, ExitStack() as outputs:
            if source.groups or source.cmptypes or source.vltypes or source.enumtypes:
                raise ProductError("unsupported_grid", "Unsupported source structure.")
            variables = _variables(source, first, limits)
            axes, timestamps, time_units, calendar = _axes(source, limits, np)
            plans = []
            seen = set()
            for request in requests:
                indices, ys, xs, stride = _selection(
                    request, axes, timestamps, limits, np
                )
                if seen.intersection(indices):
                    raise ProductError("archive_selection", "Group times overlap.")
                seen.update(indices)
                plans.append((request, indices, ys, xs, stride))
            lo, hi = min(seen), max(seen) + 1
            if hi - lo > 80:
                raise ProductError("archive_limit", "Group exceeds 80 source times.")
            for request, indices, ys, xs, stride in plans:
                product_id = _product_id(request, report, limits, data_mode)
                existing = _existing(
                    root, product_id, request, report, limits, data_mode
                )
                if existing is not None:
                    results.append(existing)
                    continue
                for parent in (processed, cached):
                    parent.mkdir(parents=True, exist_ok=True)
                    # Bounded scan counts private staging as capacity, too.
                    for count, _ in enumerate(parent.iterdir(), 1):
                        if count >= limits.max_products:
                            raise ProductError(
                                "product_count_limit", "Capacity reached."
                            )
                if (
                    shutil.disk_usage(root).free
                    < 1024**3 + 2 * limits.max_product_file_bytes
                ):
                    raise ProductError(
                        "disk_space", "Keep 1 GiB free plus staging room."
                    )
                item = {"scientific_temp": None, "preview_temp": None}
                pending.append(item)
                item["scientific_temp"] = Path(
                    tempfile.mkdtemp(prefix=".prepare_", dir=processed)
                )
                item["preview_temp"] = Path(
                    tempfile.mkdtemp(prefix=".prepare_", dir=cached)
                )
                scientific_path = item["scientific_temp"] / "fields.nc"
                preview_path = item["preview_temp"] / "preview.nc"
                scientific = outputs.enter_context(
                    Dataset(scientific_path, "w", format="NETCDF4")
                )
                preview = outputs.enter_context(
                    Dataset(preview_path, "w", format="NETCDF4")
                )
                for output, step in ((scientific, 1), (preview, stride)):
                    _write_dataset(
                        output,
                        source,
                        axes,
                        indices,
                        ys,
                        xs,
                        step,
                        request,
                        report,
                        product_id,
                        data_mode,
                        limits,
                    )
                    for name in request.variables:
                        output[name].set_var_chunk_cache(
                            size=262144, nelems=101, preemption=0.75
                        )
                item.update(
                    request=request,
                    indices=indices,
                    ys=ys,
                    xs=xs,
                    stride=stride,
                    product_id=product_id,
                    scientific=scientific,
                    preview=preview,
                    scientific_path=scientific_path,
                    preview_path=preview_path,
                )
            if pending:
                ys, xs = pending[0]["ys"], pending[0]["xs"]
                height, width = ys.stop - ys.start, xs.stop - xs.start
                for name in first.variables:
                    original = source[name]
                    chunks = original.chunking()
                    tile_y = min(256, chunks[1]) if isinstance(chunks, list) else 128
                    tile_x = min(256, chunks[2]) if isinstance(chunks, list) else 128
                    if (hi - lo) * tile_y * tile_x * 8 > 16 * 1024**2:
                        tile_y = tile_x = min(
                            128, math.isqrt(16 * 1024**2 // ((hi - lo) * 8))
                        )
                    for y in range(0, height, tile_y):
                        y1 = min(height, y + tile_y)
                        for x in range(0, width, tile_x):
                            x1 = min(width, x + tile_x)
                            values = np.ma.asarray(
                                original[
                                    lo:hi,
                                    ys.start + y : ys.start + y1,
                                    xs.start + x : xs.start + x1,
                                ],
                                dtype="float64",
                            ).filled(np.nan)
                            values[~np.isfinite(values)] = np.nan
                            for item in pending:
                                selected = np.asarray(item["indices"]) - lo
                                block = values[selected]
                                item["scientific"][name][:, y:y1, x:x1] = block
                                stride = item["stride"]
                                fy, fx = (
                                    ((y + stride - 1) // stride) * stride,
                                    ((x + stride - 1) // stride) * stride,
                                )
                                if fy < y1 and fx < x1:
                                    item["preview"][name][
                                        :,
                                        fy // stride : (y1 + stride - 1) // stride,
                                        fx // stride : (x1 + stride - 1) // stride,
                                    ] = block[:, fy - y :: stride, fx - x :: stride]
                                del block
                            del values
                _check_unchanged(definition, report, root)
        # Files must be closed before hashing/publication on Windows.
        for item in pending:
            manifest = ProductManifest(
                product_id=item["product_id"],
                source_id=definition.source_id,
                dataset_id=definition.dataset_id,
                source_version=definition.version,
                origin_url=definition.origin_url,
                input_md5=report.observed_md5,
                input_size_bytes=report.file_identity.size_bytes,
                input_modified_ns=report.file_identity.modified_ns,
                created_at=datetime.now(UTC),
                selection=item["request"],
                data_mode=data_mode,
                variables=variables,
                latitude=axes["LAT"][item["ys"]].tolist(),
                longitude=axes["LON"][item["xs"]].tolist(),
                times=[
                    timestamps[i].isoformat().replace("+00:00", "Z")
                    for i in item["indices"]
                ],
                time_units=time_units,
                calendar=calendar,
                preview_stride=item["stride"],
                scientific_file=describe_file(
                    item["scientific_path"], limits.max_product_file_bytes
                ),
                preview_file=describe_file(
                    item["preview_path"], limits.max_product_file_bytes
                ),
            )
            payload = manifest.model_dump_json(indent=2).encode() + b"\n"
            if len(payload) > limits.max_manifest_bytes:
                raise ProductError("metadata_limit", "Manifest exceeds limit.")
            with (item["scientific_temp"] / "manifest.json").open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _check_unchanged(definition, report, root)
            final_cache = contained(root, f"data/cache/{manifest.product_id}")
            final_scientific = contained(root, f"data/processed/{manifest.product_id}")
            if final_cache.exists() or final_scientific.exists():
                raise ProductError(
                    "product_conflict", "Another operator published this product."
                )
            _publish_directory(item["preview_temp"], final_cache)
            item["preview_temp"] = None
            _publish_directory(item["scientific_temp"], final_scientific)
            item["scientific_temp"] = None
            results.append(manifest)
        return results
    finally:
        for item in pending:
            _cleanup_private(item["scientific_temp"], processed)
            _cleanup_private(item["preview_temp"], cached)
