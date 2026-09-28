"""Read-only local product/API verification; requires development dependencies.

No products or source bytes are modified. Timings are in-process API timings,
not browser latency, cold-disk preparation measurements, or deployment SLAs.
"""

import argparse
import json
import math
import os
import platform
import time
from pathlib import Path

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.storage.product_common import ProductError
from backend.app.storage.products import ProductStore


def _peak_working_set_bytes() -> int | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class MemoryCounters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_working",
                "working",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ]

    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    function = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    function.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MemoryCounters),
        wintypes.DWORD,
    ]
    function.restype = wintypes.BOOL
    if not function(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return int(counters.peak_working)


def verify(product_id: str, root: Path, *, check_raw: bool = False) -> dict:
    from fastapi.testclient import TestClient

    store = ProductStore(root)
    manifest = store.product(product_id)
    longitude = manifest.longitude[len(manifest.longitude) // 2]
    latitude = manifest.latitude[len(manifest.latitude) // 2]
    prefix = f"/api/v1/products/{product_id}"
    series_by_variable = {}
    with TestClient(
        create_app(Settings(project_root=root, required_product_ids=[product_id]))
    ) as client:
        statuses = {}
        for url in ("/health", "/ready", "/api/v1/datasets", prefix):
            result = client.get(url)
            expected = (
                503 if url == "/ready" and manifest.data_mode == "synthetic" else 200
            )
            if result.status_code != expected:
                raise ProductError("verification_failed", "API contract check failed.")
            statuses[url] = result.status_code
        first_variable = next(iter(manifest.variables))
        frame_url = f"{prefix}/frame?variable={first_variable}&time_index=0"
        started = time.perf_counter()
        first = client.get(frame_url)
        first_seconds = time.perf_counter() - started
        if first.status_code != 200:
            raise ProductError("verification_failed", "Preview check failed.")
        durations = []
        for _ in range(30):
            started = time.perf_counter()
            response = client.get(frame_url)
            durations.append(time.perf_counter() - started)
            if response.status_code != 200 or response.content != first.content:
                raise ProductError(
                    "verification_failed", "Repeated frame check failed."
                )
        for variable in manifest.variables:
            result = client.get(
                f"{prefix}/timeseries",
                params={
                    "variable": variable,
                    "longitude": longitude,
                    "latitude": latitude,
                },
            )
            if result.status_code != 200:
                raise ProductError("verification_failed", "Time-series check failed.")
            series_by_variable[variable] = result.json()
        if len(manifest.latitude) * len(manifest.longitude) > 65536:
            oversized = client.get(frame_url + "&quality=scientific")
            if oversized.status_code != 413:
                raise ProductError(
                    "verification_failed", "Scientific limit check failed."
                )
            statuses["oversized_scientific_frame"] = 413
        if (
            client.get(prefix + "/frame?variable=UNKNOWN&time_index=0").status_code
            != 422
        ):
            raise ProductError(
                "verification_failed", "Unavailable-variable check failed."
            )

    raw_samples_checked = 0
    if check_raw:
        import netCDF4
        import numpy as np

        from backend.app.processing.prepare_bio_roms import _verified_input

        _, report, raw = _verified_input(manifest.selection, root)
        if report.observed_md5 != manifest.input_md5:
            raise ProductError("verification_failed", "Source identities differ.")
        with netCDF4.Dataset(raw, "r") as source:
            x = int(np.argmin(np.abs(source["LON"][:] - longitude)))
            y = int(np.argmin(np.abs(source["LAT"][:] - latitude)))
            t = source["TIME"]
            times = [
                d.isoformat() + "Z" for d in netCDF4.num2date(t[:], t.units, t.calendar)
            ]
            indices = [times.index(stamp) for stamp in manifest.times]
            for variable, series in series_by_variable.items():
                source[variable].set_var_chunk_cache(
                    size=16777216, nelems=1009, preemption=0.5
                )
                original = np.asarray(
                    np.ma.filled(source[variable][indices, y, x], np.nan), dtype=float
                )
                original_json = [
                    float(v) if math.isfinite(v) else None for v in original
                ]
                if original_json != series["values"]:
                    raise ProductError(
                        "verification_failed", "Raw and served samples differ."
                    )
                raw_samples_checked += len(indices)
    return {
        "schema_version": 1,
        "product_id": product_id,
        "data_mode": manifest.data_mode,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "measurement_scope": "local_in_process_api_not_browser_or_cold_disk",
        "first_preview_seconds": first_seconds,
        "warm_repetitions": len(durations),
        "warm_preview_p95_seconds": sorted(durations)[
            math.ceil(0.95 * len(durations)) - 1
        ],
        "preview_response_bytes": len(first.content),
        "preview_shape": first.json()["shape"],
        "scientific_file_bytes": manifest.scientific_file.size_bytes,
        "preview_file_bytes": manifest.preview_file.size_bytes,
        "raw_samples_checked": raw_samples_checked,
        "raw_samples_match": True if check_raw else None,
        "checked_point": {"longitude": longitude, "latitude": latitude},
        "served_finite_samples": sum(
            value is not None
            for series in series_by_variable.values()
            for value in series["values"]
        ),
        "verification_process_peak_working_set_bytes": _peak_working_set_bytes(),
        "checks": statuses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product_id")
    parser.add_argument(
        "--check-raw",
        action="store_true",
        help="Also compare a bounded raw-source point series",
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                verify(
                    args.product_id, Path(__file__).parents[1], check_raw=args.check_raw
                ),
                indent=2,
            )
        )
        return 0
    except ProductError as error:
        print(json.dumps({"error": {"code": error.code, "message": error.message}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
