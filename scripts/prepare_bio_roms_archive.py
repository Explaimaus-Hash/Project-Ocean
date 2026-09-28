"""Explicit, resumable SST/SSS archive preparation in four-source-time products.

No source fetching or HTTP/startup processing. Existing products and raw bytes
are immutable. Each batch keeps the original 8M-value/128MiB work/file ceilings.
"""

import json
import shutil
from datetime import date

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_bio_roms import (
    _axes,
    _verified_input,
    prepare_product,
)
from backend.app.schemas.products import PreparationRequest, Region
from backend.app.storage.product_common import ProductError, load_limits


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

    root = PROJECT_ROOT
    request = PreparationRequest(
        variables=["SST", "SSS"],
        region=Region(west=30, east=120, south=-30, north=30),
        start_date=date(2019, 1, 1),
        end_date=date(2019, 3, 31),
    )
    try:
        _, _, raw = _verified_input(request, root)
        with Dataset(raw, "r") as source:
            _, times, _, _ = _axes(source, load_limits(root), np)
        batches = batch_dates(times)
        # Conservative uncompressed two-field bound plus room for staging/previews.
        if shutil.disk_usage(root).free < 8 * 1024**3:
            raise ProductError("disk_space", "At least 8 GiB free space is required.")
        print(
            json.dumps(
                {
                    "status": "planning",
                    "times": len(times),
                    "batches": len(batches),
                    "first": times[0].isoformat(),
                    "last": times[-1].isoformat(),
                }
            ),
            flush=True,
        )
        for index, (start, end) in enumerate(batches):
            selection = PreparationRequest(
                variables=request.variables,
                region=request.region,
                start_date=start,
                end_date=end,
            )
            manifest = prepare_product(selection, root)
            print(
                json.dumps(
                    {
                        "status": "prepared",
                        "batch": index + 1,
                        "batches": len(batches),
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
