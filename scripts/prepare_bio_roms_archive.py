"""Explicit, resumable SST/SSS archive preparation in four-source-time products.

No source fetching or HTTP/startup processing. Existing products and raw bytes
are immutable. Each batch keeps the original 8M-value/128MiB work/file ceilings.
"""

import argparse
import json
import shutil
from datetime import date

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_bio_roms import (
    _axes,
    _existing,
    _verified_input,
    prepare_product,
)
from backend.app.schemas.products import PreparationRequest, Region
from backend.app.storage.product_common import ProductError, load_limits
from backend.app.storage.products import ProductStore

VARIABLE_GROUPS = (
    ("SST", "SSS"),
    ("MLD", "DIC"),
    ("CHL", "NO3"),
    ("pCO2_Original", "pCO2_Clim"),
    ("pCO2_Int", "Deviant_uncertainty"),
)


def batch_dates(timestamps: list) -> list[tuple[date, date]]:
    if not timestamps or len(timestamps) > 480:
        raise ProductError("archive_limit", "Expected at most 480 source times.")
    dates = [time.date() for time in timestamps]
    if any(a >= b for a, b in zip(dates, dates[1:], strict=False)):
        raise ProductError("archive_times", "Expected unique increasing source dates.")
    return [
        (dates[i], dates[min(i + 3, len(dates) - 1)]) for i in range(0, len(dates), 4)
    ]


def main() -> int:
    import numpy as np
    from netCDF4 import Dataset

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-variables",
        action="store_true",
        help="Prepare all ten inspected surface variables, in bounded pairs.",
    )
    args = parser.parse_args()
    groups = VARIABLE_GROUPS if args.all_variables else VARIABLE_GROUPS[:1]
    root = PROJECT_ROOT
    request = PreparationRequest(
        variables=["SST", "SSS"],
        region=Region(west=30, east=120, south=-30, north=30),
        start_date=date(2019, 1, 1),
        end_date=date(2019, 3, 31),
    )
    try:
        _, report, raw = _verified_input(request, root)
        limits = load_limits(root)
        with Dataset(raw, "r") as source:
            _, times, _, _ = _axes(source, load_limits(root), np)
        batches = batch_dates(times)
        # Reuse verified legacy products even when catalogue capacity changes.
        # Capacity participates in old IDs; never duplicate those native arrays.
        store = ProductStore(root)
        existing = {}
        for item in store.catalogue()["products"]:
            if item["status"] == "ready" and item["dataset_id"] == request.dataset_id:
                manifest = store.product(item["product_id"])
                if (
                    manifest.data_mode == "real"
                    and manifest.input_md5 == report.observed_md5
                ):
                    existing[manifest.selection.model_dump_json()] = manifest.product_id
        print(
            json.dumps(
                {
                    "status": "planning",
                    "times": len(times),
                    "batches": len(batches),
                    "variable_groups": groups,
                    "first": times[0].isoformat(),
                    "last": times[-1].isoformat(),
                }
            ),
            flush=True,
        )
        selections = [(start, end, group) for start, end in batches for group in groups]
        if args.all_variables:
            from backend.app.processing.archive_bio_roms import prepare_archive_group

            completed = 0
            for offset in range(0, len(batches), 20):
                for group in groups:
                    missing = []
                    for start, end in batches[offset : offset + 20]:
                        selection = PreparationRequest(
                            variables=list(group),
                            region=request.region,
                            start_date=start,
                            end_date=end,
                        )
                        prior_id = existing.get(selection.model_dump_json())
                        if prior_id:
                            _existing(root, prior_id, selection, report, limits, "real")
                            completed += 1
                        else:
                            missing.append(selection)
                    if missing:
                        prepared = prepare_archive_group(missing, root)
                        completed += len(prepared)
                    print(
                        json.dumps(
                            {
                                "status": "prepared_group",
                                "completed_products": completed,
                                "total_products": len(selections),
                                "variables": list(group),
                                "source_date_end": batches[
                                    min(offset + 19, len(batches) - 1)
                                ][1].isoformat(),
                                "free_gib": round(
                                    shutil.disk_usage(root).free / 1024**3, 2
                                ),
                            }
                        ),
                        flush=True,
                    )
            return 0
        for index, (start, end, group) in enumerate(selections):
            selection = PreparationRequest(
                variables=list(group),
                region=request.region,
                start_date=start,
                end_date=end,
            )
            prior_id = existing.get(selection.model_dump_json())
            manifest = (
                _existing(root, prior_id, selection, report, limits, "real")
                if prior_id
                else None
            )
            if manifest is None:
                # Keep a reserve plus worst-case bounded scientific/preview staging.
                # Stop before filling the disk; completed products remain reusable.
                if (
                    shutil.disk_usage(root).free
                    < 1024**3 + 2 * limits.max_product_file_bytes
                ):
                    raise ProductError(
                        "disk_space",
                        "Insufficient free space for a batch plus 1 GiB reserve.",
                    )
                manifest = prepare_product(selection, root)
            print(
                json.dumps(
                    {
                        "status": "prepared",
                        "batch": index + 1,
                        "batches": len(selections),
                        "variables": list(group),
                        "reused": prior_id is not None,
                        "product_id": manifest.product_id,
                        "times": manifest.times,
                    }
                ),
                flush=True,
            )
        return 0
    except ProductError as error:
        print(
            json.dumps({"error": {"code": error.code, "message": error.message}}),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
