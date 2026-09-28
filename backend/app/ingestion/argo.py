"""Official Argopy core expert mode with byte/sample limits before array loading."""

from pathlib import Path
from typing import Any

from ..schemas.acquisition import AcquisitionRequest
from ..schemas.datasets import DatasetDefinition
from .base import bound_dataset, bounded_http, fail, save_dataset, validate_raw


class BoundedArgoStore:
    """Argopy's documented ERDDAP fetcher store injection, one URI only.

    The original provider response is retained separately; Argopy's returned
    dataset is not claimed to be an untouched GDAC file. No global cache is used.
    """

    def __init__(self, destination: Path, request: AcquisitionRequest):
        self.destination = destination
        self.request = request
        self.calls = 0
        self.coordinate_units: dict[str, str] = {}

    def _fixed_text_widths(self) -> dict[str, int]:
        """Prove char widths before xarray decodes _Encoding into object arrays."""
        import netCDF4

        widths = {}
        with netCDF4.Dataset(self.destination, "r") as raw:
            for name, variable in raw.variables.items():
                if variable.dtype is str:
                    raise fail("unsupported_source")
                if variable.dtype.kind == "S":
                    if len(variable.dimensions) != 2 or variable.shape[-1] > 128:
                        raise fail("acquisition_limit")
                    widths[name] = variable.shape[-1]
        return widths

    def open_dataset(self, url: str, **kwargs: Any) -> Any:
        import xarray as xr

        self.calls += 1
        if self.calls != 1:
            raise fail("acquisition_limit")
        bounded_http(url, self.destination, self.request.max_bytes)
        validate_raw(self.destination, self.request)
        text_widths = self._fixed_text_widths()
        with xr.open_dataset(
            self.destination,
            engine="netcdf4",
            cache=False,
            create_default_indexes=False,
        ) as dataset:
            samples = dataset.sizes.get("row", dataset.sizes.get("N_POINTS", 0))
            if samples == 0:
                raise fail("no_data")
            if samples > self.request.max_samples:
                raise fail("acquisition_limit")
            bound_dataset(dataset, self.request, fixed_text_widths=text_widths)
            for name, accepted in (
                ("latitude", {"degrees_north", "degree_north"}),
                ("longitude", {"degrees_east", "degree_east"}),
            ):
                # Units must come from source metadata, never the dataset name.
                if name in dataset:
                    units = dataset[name].attrs.get("units")
                    if units not in accepted:
                        raise fail("unsupported_source")
                    self.coordinate_units[name.upper()] = units
            # The real rows/fields and decoded bytes were bounded before load.
            loaded = dataset.load()
            for name, variable in tuple(loaded.variables.items()):
                if variable.dtype.kind == "S":
                    # The expert client expects textual direction/QC values, not
                    # Python bytes. Width and Unicode expansion were preflighted.
                    loaded[name] = loaded[name].astype(f"U{variable.dtype.itemsize}")
                elif variable.dtype.kind == "O" and name in text_widths:
                    loaded[name] = loaded[name].astype(f"U{text_widths[name]}")
            loaded.attrs["Fetched_uri"] = url
            return loaded


def fetch(
    request: AcquisitionRequest, definition: DatasetDefinition, destination: Path
) -> dict[str, Any]:
    import argopy

    selected = request.selection
    assert selected is not None
    region = selected.region
    store = BoundedArgoStore(destination.parent / "provider_input.nc", request)
    fetcher = argopy.DataFetcher(
        src="erddap",
        ds="phy",
        mode="expert",
        server="https://erddap.ifremer.fr/erddap",
        fs=store,
        cache=False,
        cachedir=str(destination.parent),
        parallel=False,
        timeout=15,
    ).region(
        [
            region.west,
            region.east,
            region.south,
            region.north,
            selected.vertical_min,
            selected.vertical_max,
            selected.start_time.isoformat(),
            selected.end_time.isoformat(),
        ]
    )
    if len(fetcher.uri) != 1:
        raise fail("acquisition_limit")
    dataset = fetcher.to_xarray(errors="raise")
    try:
        if store.calls != 1:
            raise fail("unsupported_source")
        if dataset.sizes.get("N_POINTS", 0) > request.max_samples:
            raise fail("acquisition_limit")
        # Argopy records OS account names as metadata; they are not provenance
        # needed for science and must not be written into reusable products.
        dataset.attrs.pop("Fetched_by", None)
        if set(store.coordinate_units) != {"LATITUDE", "LONGITUDE"}:
            raise fail("unsupported_source")
        # Argopy1.4 replaces position attributes and drops units. Restore only
        # units actually read and validated in the original provider response.
        for name, units in store.coordinate_units.items():
            dataset[name].attrs["units"] = units
        save_dataset(dataset, destination, request)
    finally:
        dataset.close()
    return {
        "client": "argopy",
        "client_version": argopy.__version__,
        "client_processing": (
            "Argopy src=erddap, ds=phy, mode=expert, parallel=False, cache=False, "
            "errors=raise; service "
            "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats. "
            "ERDDAP applies requested raw PRES/time/position constraints "
            "and distinct/orderBy. Argopy renames row to N_POINTS and variables to "
            "uppercase, casts types and replaces variable/global attributes; no "
            "standard/research QC/data-mode filter. Original ERDDAP response is "
            "provider_input.nc. Fetched_by account metadata is removed. Raw GDAC "
            "JULD is represented as ERDDAP time then Argopy TIME; no pressure/depth "
            "conversion. Bounded byte strings are decoded before the client; "
            "fixed-width string output avoids unbounded VLEN strings. Latitude/"
            "longitude units dropped by Argopy are restored from provider headers."
        ),
        "transport": "https",
        "original_filename": "ArgoFloats.nc",
    }
