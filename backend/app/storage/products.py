"""Read bounded prepared products only; never fetch or open raw inputs in HTTP."""

import json
import math
import re
import threading
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..schemas.products import PerformanceLimits, ProductManifest, Region
from .product_common import ProductError, contained, load_limits, read_json, stat_file

# netCDF/HDF5 access is serialized per process; overload is explicit, not queued.
_NETCDF_LOCK = threading.Lock()


@contextmanager
def _scientific_access():
    if not _NETCDF_LOCK.acquire(blocking=False):
        raise ProductError("busy", "A scientific read is active; retry shortly.", 503)
    try:
        yield
    finally:
        _NETCDF_LOCK.release()


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,95}", value):
        raise ProductError("invalid_product_id", "Invalid product identifier.", 422)
    return value


def _bounded(payload: dict, limits: PerformanceLimits) -> dict:
    try:
        size = len(json.dumps(payload, allow_nan=False, separators=(",", ":")).encode())
    except (ValueError, TypeError):
        raise ProductError("invalid_product", "Prepared values are invalid.") from None
    if size > limits.max_response_bytes:
        raise ProductError("response_limit", "Select a smaller bounded request.", 413)
    return payload


class ProductStore:
    """Construct without I/O; resolve/validate private paths only on explicit reads."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _paths(self, product_id: str) -> tuple[Path, Path, Path]:
        product_id = _identifier(product_id)
        return (
            contained(self.root, f"data/processed/{product_id}/manifest.json"),
            contained(self.root, f"data/processed/{product_id}/fields.nc"),
            contained(self.root, f"data/cache/{product_id}/preview.nc"),
        )

    def _files(
        self,
        manifest: ProductManifest,
        limits: PerformanceLimits,
        *,
        check_access: bool = False,
    ) -> None:
        _, scientific, preview = self._paths(manifest.product_id)
        for path, expected in (
            (scientific, manifest.scientific_file),
            (preview, manifest.preview_file),
        ):
            actual = stat_file(
                path, limits.max_product_file_bytes, check_access=check_access
            )
            if actual != (expected.size_bytes, expected.modified_ns):
                raise ProductError("product_changed", "Prepared product has changed.")

    def _load(
        self,
        product_id: str,
        limits: PerformanceLimits,
        *,
        check_access: bool = False,
    ) -> ProductManifest:
        manifest_path, _, _ = self._paths(product_id)
        if not manifest_path.exists():
            raise ProductError(
                "not_prepared", "Requested product is not prepared.", 404
            )
        try:
            result = ProductManifest.model_validate(
                read_json(manifest_path, limits.max_manifest_bytes)
            )
        except (ValidationError, ValueError, TypeError):
            raise ProductError(
                "invalid_product", "Prepared metadata is invalid."
            ) from None
        cells = len(result.latitude) * len(result.longitude)
        s = result.preview_stride
        preview_cells = math.ceil(len(result.latitude) / s) * math.ceil(
            len(result.longitude) / s
        )
        if (
            result.product_id != product_id
            or len(result.times) > limits.max_time_steps
            or max(len(result.latitude), len(result.longitude)) > limits.max_axis_values
            or cells * len(result.times) * len(result.variables)
            > limits.max_preparation_values
            or preview_cells > limits.max_preview_cells
        ):
            raise ProductError("invalid_product", "Prepared metadata exceeds limits.")
        self._files(result, limits, check_access=check_access)
        return result

    def product(self, product_id: str) -> ProductManifest:
        return self._load(product_id, load_limits(self.root))

    @staticmethod
    def _public(manifest: ProductManifest) -> dict:
        return manifest.model_dump(
            mode="json",
            exclude={"input_modified_ns", "scientific_file", "preview_file"},
        ) | {"status": "ready", "ready_scope": "prepared_surface_selection"}

    def metadata(self, product_id: str) -> dict:
        limits = load_limits(self.root)
        return _bounded(self._public(self._load(product_id, limits)), limits)

    def catalogue(self) -> dict:
        from ..ingestion.registry import RegistryError, load_registry

        limits = load_limits(self.root)
        try:
            registry = load_registry(self.root / "config" / "data_sources.yaml")
        except RegistryError:
            raise ProductError(
                "configuration_unavailable", "Source registry is invalid.", 503
            ) from None
        directory = contained(self.root, "data/processed")
        products: list[dict] = []
        try:
            entries = (
                list(islice(directory.iterdir(), limits.max_products + 1))
                if directory.exists()
                else []
            )
        except OSError:
            raise ProductError(
                "product_unavailable", "Product catalogue is unavailable.", 503
            ) from None
        if len(entries) > limits.max_products:
            raise ProductError(
                "catalogue_limit", "Product catalogue exceeds limits.", 503
            )
        known = {entry.dataset_id for entry in registry.datasets}
        for entry in sorted(entries):
            if entry.name.startswith("."):
                continue
            try:
                manifest = self._load(entry.name, limits)
                if manifest.dataset_id not in known:
                    continue
                products.append(
                    {
                        "product_id": manifest.product_id,
                        "dataset_id": manifest.dataset_id,
                        "status": "ready",
                        "data_mode": manifest.data_mode,
                        "variables": list(manifest.variables),
                        "times": manifest.times,
                        "capabilities": manifest.capabilities.model_dump(),
                        "region": manifest.selection.region.model_dump(),
                    }
                )
            except ProductError as error:
                if re.fullmatch(r"[a-z][a-z0-9_]{0,95}", entry.name):
                    products.append(
                        {
                            "product_id": entry.name,
                            "status": "not_prepared",
                            "reason_code": error.code,
                        }
                    )
        datasets = []
        for entry in registry.datasets:
            ready_ids = [
                p["product_id"]
                for p in products
                if p.get("dataset_id") == entry.dataset_id and p["status"] == "ready"
            ]
            datasets.append(
                {
                    "source_id": entry.source_id,
                    "dataset_id": entry.dataset_id,
                    "title": entry.title,
                    "role": entry.role,
                    "origin_url": entry.origin_url,
                    "status": "ready" if ready_ids else "not_prepared",
                    "reason_code": "prepared_selection_available"
                    if ready_ids
                    else "no_prepared_product",
                    "product_ids": ready_ids,
                }
            )
        return _bounded(
            {"schema_version": 1, "datasets": datasets, "products": products}, limits
        )

    def readiness(self, required_product_ids: list[str]) -> dict:
        if not required_product_ids:
            return {
                "status": "not_ready",
                "reason_code": "required_products_not_configured",
                "checks": [],
            }
        checks = []
        try:
            limits = load_limits(self.root)
        except ProductError as error:
            return {"status": "not_ready", "reason_code": error.code, "checks": []}
        for product_id in required_product_ids[:16]:
            try:
                manifest = self._load(product_id, limits, check_access=True)
                if manifest.data_mode != "real":
                    raise ProductError(
                        "synthetic_product",
                        "Synthetic data cannot satisfy real-data readiness.",
                    )
                checks.append(
                    {
                        "product_id": product_id,
                        "status": "ready",
                        "reason_code": "local_product_present",
                    }
                )
            except ProductError as error:
                checks.append(
                    {
                        "product_id": product_id,
                        "status": "not_ready",
                        "reason_code": error.code,
                    }
                )
        ready = len(required_product_ids) <= 16 and all(
            c["status"] == "ready" for c in checks
        )
        return {"status": "ready" if ready else "not_ready", "checks": checks}

    @staticmethod
    def _variable(manifest: ProductManifest, variable: str) -> None:
        if variable not in manifest.variables:
            raise ProductError(
                "unsupported_variable", "Variable is not prepared in this product.", 422
            )

    @staticmethod
    def _validate_netcdf(
        dataset: Any,
        manifest: ProductManifest,
        stride: int,
        variable: str,
        limits: PerformanceLimits,
    ) -> None:
        import numpy as np

        axes = {"LAT": manifest.latitude[::stride], "LON": manifest.longitude[::stride]}
        shape = (len(manifest.times), len(axes["LAT"]), len(axes["LON"]))
        if dataset.groups or variable not in dataset.variables:
            raise ProductError("invalid_product", "Prepared structure is invalid.")
        field = dataset[variable]
        if (
            field.dimensions != ("TIME", "LAT", "LON")
            or field.shape != shape
            or field.dtype != np.dtype("float64")
        ):
            raise ProductError(
                "invalid_product", "Prepared field shape/type is invalid."
            )
        if any(
            name in field.ncattrs()
            for name in ("scale_factor", "add_offset", "_Unsigned")
        ):
            raise ProductError(
                "invalid_product", "Prepared values cannot be packed twice."
            )
        if getattr(field, "units", None) != manifest.variables[variable].units:
            raise ProductError(
                "invalid_product", "Prepared field units are inconsistent."
            )
        for name, expected in axes.items():
            if name not in dataset.variables or dataset[name].shape != (len(expected),):
                raise ProductError(
                    "invalid_product", "Prepared coordinates are inconsistent."
                )
            actual = dataset[name][:]
            if np.ma.getmaskarray(actual).any() or not np.array_equal(actual, expected):
                raise ProductError(
                    "invalid_product", "Prepared coordinates are inconsistent."
                )
        if "TIME" not in dataset.variables or dataset["TIME"].shape != (
            len(manifest.times),
        ):
            raise ProductError(
                "invalid_product", "Prepared time coordinate is inconsistent."
            )
        import netCDF4

        times = dataset["TIME"]
        decoded = netCDF4.num2date(times[:], times.units, times.calendar)
        actual_times = [t.isoformat() + "Z" for t in decoded]
        if actual_times != manifest.times:
            raise ProductError(
                "invalid_product", "Prepared timestamps are inconsistent."
            )
        chunks = field.chunking()
        if (
            isinstance(chunks, list)
            and math.prod(chunks) * field.dtype.itemsize > limits.max_source_chunk_bytes
        ):
            raise ProductError("invalid_product", "Prepared chunks exceed limits.")
        field.set_var_chunk_cache(
            size=limits.netcdf_cache_bytes, nelems=1009, preemption=0.5
        )

    @staticmethod
    def _base(manifest: ProductManifest, variable: str) -> dict:
        return {
            "schema_version": 1,
            "product_id": manifest.product_id,
            "dataset_id": manifest.dataset_id,
            "source_id": manifest.source_id,
            "source_version": manifest.source_version,
            "input_md5": manifest.input_md5,
            "processing_version": manifest.processing_version,
            "data_mode": manifest.data_mode,
            "variable": variable,
            "units": manifest.variables[variable].units,
            "variable_metadata": manifest.variables[variable].model_dump(),
            "qc_policy": manifest.qc_policy,
            "temporal_support": manifest.temporal_support,
            "vertical_reference": "source_surface_product_no_numeric_depth_assigned",
            "missing_value": None,
        }

    def frame(
        self,
        product_id: str,
        variable: str,
        time_index: int,
        quality: str = "preview",
        region: Region | None = None,
    ) -> dict:
        limits = load_limits(self.root)
        manifest = self._load(product_id, limits)
        self._variable(manifest, variable)
        if quality not in ("preview", "scientific") or not 0 <= time_index < len(
            manifest.times
        ):
            raise ProductError(
                "invalid_selection", "Quality or time index is unavailable.", 422
            )
        stride = manifest.preview_stride if quality == "preview" else 1
        lat = manifest.latitude[::stride]
        lon = manifest.longitude[::stride]
        lat_ids = [
            i
            for i, v in enumerate(lat)
            if region is None or region.south <= v <= region.north
        ]
        lon_ids = [
            i
            for i, v in enumerate(lon)
            if region is None or region.west <= v <= region.east
        ]
        if not lat_ids or not lon_ids:
            raise ProductError(
                "no_overlap", "No prepared cells fall within this region.", 422
            )
        cells = len(lat_ids) * len(lon_ids)
        maximum = (
            limits.max_preview_cells
            if quality == "preview"
            else limits.max_scientific_frame_cells
        )
        if cells > maximum:
            raise ProductError(
                "cell_limit", "Use preview quality or a smaller region.", 413
            )
        _, scientific, preview = self._paths(product_id)
        with _scientific_access():
            import netCDF4
            import numpy as np

            try:
                with netCDF4.Dataset(
                    str(preview if quality == "preview" else scientific), "r"
                ) as dataset:
                    self._validate_netcdf(dataset, manifest, stride, variable, limits)
                    selected = dataset[variable][
                        time_index,
                        slice(lat_ids[0], lat_ids[-1] + 1),
                        slice(lon_ids[0], lon_ids[-1] + 1),
                    ]
                    values = np.asarray(np.ma.filled(selected, np.nan), dtype=float)
                    finite = np.isfinite(values)
                    output = np.where(finite, values, None).tolist()
            except (
                OSError,
                RuntimeError,
                ValueError,
                AttributeError,
                KeyError,
                TypeError,
            ):
                raise ProductError(
                    "invalid_product", "Prepared field could not be read."
                ) from None
        self._files(manifest, limits)
        return _bounded(
            self._base(manifest, variable)
            | {
                "quality": quality,
                "display_only": quality == "preview",
                "sampling": "strided_source_cells_no_interpolation"
                if quality == "preview"
                else "scientific_source_cells",
                "stride": stride,
                "dimensions": ["latitude", "longitude"],
                "shape": [len(lat_ids), len(lon_ids)],
                "time_index": time_index,
                "time": manifest.times[time_index],
                "latitude": [lat[i] for i in lat_ids],
                "longitude": [lon[i] for i in lon_ids],
                "values": output,
                "valid_count": int(finite.sum()),
                "missing_count": cells - int(finite.sum()),
                "requested_region": region.model_dump() if region else None,
            },
            limits,
        )

    def timeseries(
        self, product_id: str, variable: str, longitude: float, latitude: float
    ) -> dict:
        limits = load_limits(self.root)
        manifest = self._load(product_id, limits)
        self._variable(manifest, variable)
        if not (
            math.isfinite(longitude)
            and math.isfinite(latitude)
            and manifest.longitude[0] <= longitude <= manifest.longitude[-1]
            and manifest.latitude[0] <= latitude <= manifest.latitude[-1]
        ):
            raise ProductError(
                "no_overlap", "Point is outside prepared coordinate support.", 422
            )
        y = min(
            range(len(manifest.latitude)),
            key=lambda i: abs(manifest.latitude[i] - latitude),
        )
        x = min(
            range(len(manifest.longitude)),
            key=lambda i: abs(manifest.longitude[i] - longitude),
        )
        _, path, _ = self._paths(product_id)
        with _scientific_access():
            import netCDF4
            import numpy as np

            try:
                with netCDF4.Dataset(str(path), "r") as dataset:
                    self._validate_netcdf(dataset, manifest, 1, variable, limits)
                    values = np.asarray(
                        np.ma.filled(dataset[variable][:, y, x], np.nan), dtype=float
                    )
                    output = np.where(np.isfinite(values), values, None).tolist()
            except (
                OSError,
                RuntimeError,
                ValueError,
                AttributeError,
                KeyError,
                TypeError,
            ):
                raise ProductError(
                    "invalid_product", "Prepared time series could not be read."
                ) from None
        self._files(manifest, limits)
        dy = math.radians(manifest.latitude[y] - latitude)
        dx = math.radians(manifest.longitude[x] - longitude)
        hav = (
            math.sin(dy / 2) ** 2
            + math.cos(math.radians(latitude))
            * math.cos(math.radians(manifest.latitude[y]))
            * math.sin(dx / 2) ** 2
        )
        distance = 6371008.8 * 2 * math.asin(min(1.0, math.sqrt(max(0.0, hav))))
        return _bounded(
            self._base(manifest, variable)
            | {
                "times": manifest.times,
                "values": output,
                "requested_point": {"longitude": longitude, "latitude": latitude},
                "sample_point": {
                    "longitude": manifest.longitude[x],
                    "latitude": manifest.latitude[y],
                },
                "sample_indices": {"latitude": y, "longitude": x},
                "distance_m": distance,
                "sampling": "nearest_axis_grid_cell_no_wet_cell_search",
                "display_only": False,
                "comparison_result": False,
            },
            limits,
        )
