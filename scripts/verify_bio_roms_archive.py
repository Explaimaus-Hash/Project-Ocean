"""Read-only real archive HTTP/point checks against original source timestamps."""

import argparse
import json
from datetime import date
from time import perf_counter, sleep
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np
from netCDF4 import Dataset

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.prepare_bio_roms import _axes, _verified_input
from backend.app.schemas.products import PreparationRequest, Region
from backend.app.storage.product_common import load_limits
from scripts.prepare_bio_roms_archive import VARIABLE_GROUPS

BUSY_RETRIES = 0


def get(path):
    global BUSY_RETRIES
    for attempt in range(5):
        try:
            with urlopen("http://127.0.0.1:8000" + path, timeout=20) as response:
                assert response.status == 200
                body = response.read(2097153)
                assert len(body) <= 2097152
                return json.loads(body)
        except HTTPError as error:
            # A concurrent browser read can occupy the single scientific reader.
            # Retry only its documented busy response, never other failures.
            if error.code != 503 or attempt == 4:
                raise
            payload = json.loads(error.read(4096))
            if payload.get("error", {}).get("code") != "busy":
                raise
            BUSY_RETRIES += 1
            sleep(0.1 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-variables", action="store_true")
    args = parser.parse_args()
    names = (
        [name for group in VARIABLE_GROUPS for name in group]
        if args.all_variables
        else ["SST", "SSS"]
    )
    started = perf_counter()
    root = PROJECT_ROOT
    request = PreparationRequest(
        variables=["SST", "SSS"],
        region=Region(west=30, east=120, south=-30, north=30),
        start_date=date(2019, 1, 1),
        end_date=date(2019, 3, 31),
    )
    _, report, raw = _verified_input(request, root)
    before = (raw.stat().st_size, raw.stat().st_mtime_ns)
    catalogue = get("/api/v1/datasets")
    timelines = {name: {} for name in names}
    for product in catalogue["products"]:
        if (
            product["status"] == "ready"
            and product["dataset_id"] == request.dataset_id
            and product["data_mode"] == "real"
            and product.get("input_md5") == report.observed_md5
            and product.get("source_version") == "v2"
            and product.get("region") == request.region.model_dump()
        ):
            for name in names:
                if name in product["variables"]:
                    for index, timestamp in enumerate(product["times"]):
                        timelines[name].setdefault(
                            timestamp, (product["product_id"], index)
                        )
    with Dataset(raw) as source:
        axes, times, _, _ = _axes(source, load_limits(root), np)
        labels = [time.isoformat().replace("+00:00", "Z") for time in times]
        assert len(labels) == 480
        assert all(sorted(axis) == labels for axis in timelines.values())
        first_id = timelines[names[0]][labels[0]][0]
        meta = get(f"/api/v1/products/{first_id}")
        stride = meta["preview_stride"]
        ys = list(range(0, len(meta["latitude"]), stride))
        xs = list(range(0, len(meta["longitude"]), stride))
        py = min(range(len(ys)), key=lambda i: abs(meta["latitude"][ys[i]]))
        px = min(range(len(xs)), key=lambda i: abs(meta["longitude"][xs[i]] - 75))
        y, x = ys[py], xs[px]
        source_y = int(np.argmin(abs(axes["LAT"] - meta["latitude"][y])))
        source_x = int(np.argmin(abs(axes["LON"] - meta["longitude"][x])))
        native_y = int(np.argmin(abs(axes["LAT"])))
        native_x = int(np.argmin(abs(axes["LON"] - 75)))
        expected = {}
        native = {}
        for name in names:
            source[name].set_var_chunk_cache(
                size=16777216, nelems=1009, preemption=0.75
            )
            expected[name] = source[name][:, source_y, source_x].filled(np.nan)
            native[name] = source[name][:, native_y, native_x].filled(np.nan)
        series = {}
        for source_index, timestamp in enumerate(labels):
            for name in names:
                product_id, index = timelines[name][timestamp]
                frame = get(
                    f"/api/v1/products/{product_id}/frame?variable={name}&time_index={index}"
                )
                assert frame["time"] == timestamp and frame["product_id"] == product_id
                assert (
                    frame["variable"] == name and frame["units"] == source[name].units
                )
                assert frame["longitude"][px] == meta["longitude"][x]
                assert frame["variable_metadata"]["long_name"] == source[name].long_name
                assert frame["latitude"][py] == meta["latitude"][y]
                value = frame["values"][py][px]
                np.testing.assert_equal(
                    np.nan if value is None else value, expected[name][source_index]
                )
                key = (product_id, name)
                if key not in series:
                    series[key] = get(
                        f"/api/v1/products/{product_id}/timeseries?variable={name}&longitude=75&latitude=0"
                    )
                result = series[key]
                assert result["units"] == source[name].units
                assert result["times"][index] == timestamp
                value = result["values"][index]
                np.testing.assert_equal(
                    np.nan if value is None else value, native[name][source_index]
                )
            if (source_index + 1) % 80 == 0:
                print(json.dumps({"checked_dates": source_index + 1}), flush=True)
    assert before == (raw.stat().st_size, raw.stat().st_mtime_ns)
    print(
        json.dumps(
            {
                "status": "verified",
                "dates": len(labels),
                "variables": names,
                "preview_frames": len(labels) * len(names),
                "exact_preview_point_values": len(labels) * len(names),
                "exact_native_point_values": len(labels) * len(names),
                "unique_products": len(
                    {p for axis in timelines.values() for p, _ in axis.values()}
                ),
                "first": labels[0],
                "last": labels[-1],
                "elapsed_seconds": round(perf_counter() - started, 2),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
