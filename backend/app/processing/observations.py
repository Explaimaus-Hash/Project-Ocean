"""Operator-only, bounded Argo/EGO normalization of trusted local NetCDF files.

No provider access, scientific imports, or filesystem work occurs at import.
QC eligibility is deliberately separate from scientific quantity compatibility.
"""

import hashlib
import json
import math
from pathlib import Path

from ..schemas.observations import (
    MAX_OBSERVATION_JSON_BYTES,
    MAX_OBSERVATION_SAMPLES,
    OBSERVATION_PROCESSING_VERSION,
    ObservationCapabilities,
    ObservationCollection,
    ObservationCounts,
    ObservationRequest,
    ObservationSample,
    ObservationValue,
    ObservationVariableInfo,
)
from ..storage.product_common import ProductError, describe_file, stat_file

MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_INPUT_SAMPLES = 100000
MAX_EGO_SCAN_SAMPLES = 1000000
COORDINATE_SCAN_CHUNK = 4096
MAX_DECODED_BYTES = 64 * 1024 * 1024
MAX_CHUNK_BYTES = 16 * 1024 * 1024
ACCEPTED_QC = {"1", "2"}
CALENDARS = {"standard", "gregorian", "proleptic_gregorian"}


def _fail(code: str, message: str) -> None:
    raise ProductError(code, message)


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        result = value.decode("ascii", errors="strict").strip(" \x00")
    elif isinstance(value, str):
        result = value.strip(" \x00")
    elif isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None
        result = str(int(value)) if float(value).is_integer() else str(value)
    else:
        try:
            return _text(value.item())
        except (AttributeError, ValueError):
            _fail("unsupported_metadata", "Observation text layout is unsupported.")
    if len(result) > 128 or any(ord(char) < 32 for char in result):
        _fail("metadata_limit", "Observation metadata exceeds safe limits.")
    return result or None


def _number(value) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        _fail("unsupported_values", "Observation numeric values are unsupported.")
    return result if math.isfinite(result) else None


def _qc(value) -> str | None:
    result = _text(value)
    if result is not None and result not in set("0123456789"):
        _fail("unsupported_qc", "Observation QC flag encoding is unsupported.")
    return result


def _mode(value) -> str | None:
    result = _text(value)
    if result not in {None, "R", "A", "D"}:
        _fail("unsupported_data_mode", "Observation data mode is unsupported.")
    return result


def _identifier(prefix: str, value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()[:24]


def _preflight(path: Path) -> None:
    """Bound native input layout before xarray can decode/index any arrays."""
    import netCDF4
    import numpy as np

    with netCDF4.Dataset(path, "r") as source:
        chunked_ego = (
            getattr(source, "data_type", None) == "EGO glider time-series data"
            and str(getattr(source, "format_version", None)) == "1.2"
        )
        if source.groups or len(source.variables) > 256 or len(source.dimensions) > 32:
            _fail("unsupported_layout", "Observation NetCDF layout is unsupported.")
        if any(len(dim) > 1000000 for dim in source.dimensions.values()):
            _fail("observation_limit", "Source dimensions exceed observation limits.")
        if len(source.ncattrs()) > 128:
            _fail("metadata_limit", "Observation global attributes exceed limits.")
        metadata_bytes = 0
        for name in source.ncattrs():
            attribute_bytes = np.asarray(source.getncattr(name)).nbytes
            metadata_bytes += attribute_bytes
            if attribute_bytes > 8192:
                _fail("metadata_limit", "Observation global attributes exceed limits.")
        decoded_bytes = 0
        for variable in source.variables.values():
            dtype = np.dtype(variable.dtype)
            if dtype.kind not in "biufSU" or dtype.kind == "U":
                _fail("unsupported_layout", "Only primitive NetCDF data are supported.")
            count = math.prod(variable.shape)
            decoded_bytes += count * max(dtype.itemsize, 8)
            # EGO's engineering variables remain lazy: only 4096-coordinate chunks
            # and <=5000 selected samples are ever read. Unused variable shapes
            # do not represent a materialized array. File/metadata/chunk ceilings
            # are still checked independently before xarray opens the dataset.
            if decoded_bytes > MAX_DECODED_BYTES and not chunked_ego:
                _fail("observation_limit", "Decoded source exceeds observation limits.")
            chunks = variable.chunking()
            if (
                isinstance(chunks, list)
                and math.prod(chunks) * dtype.itemsize > MAX_CHUNK_BYTES
            ):
                _fail("observation_limit", "Observation source chunks exceed limits.")
            if len(variable.ncattrs()) > 64:
                _fail("metadata_limit", "Observation attributes exceed limits.")
            for name in variable.ncattrs():
                attribute = variable.getncattr(name)
                attribute_bytes = np.asarray(attribute).nbytes
                metadata_bytes += attribute_bytes
                if attribute_bytes > 8192 or metadata_bytes > 2 * 1024 * 1024:
                    _fail("metadata_limit", "Observation attributes exceed limits.")


class _Reader:
    def __init__(self, dataset, source_id: str):
        self.ds = dataset
        self.source_id = source_id
        self.range_masked_variables = set()
        if "PRES" not in dataset and "PRES_ADJUSTED" not in dataset:
            _fail("missing_pressure", "Observation pressure is required.")
        pressure = dataset.get("PRES", dataset.get("PRES_ADJUSTED"))
        if source_id == "argo" and pressure.dims == ("N_PROF", "N_LEVELS"):
            self.layout = "argo_profiles"
        elif source_id == "argo" and pressure.dims == ("N_POINTS",):
            self.layout = "argo_points"
        elif source_id == "ifremer_glider" and len(pressure.dims) == 1:
            if (
                dataset.attrs.get("data_type") != "EGO glider time-series data"
                or str(dataset.attrs.get("format_version")) != "1.2"
            ):
                _fail("unsupported_format", "This adapter requires EGO format 1.2.")
            self.layout = "ego_timeseries"
        else:
            _fail("unsupported_layout", "Observation sample layout is unsupported.")
        self.sample_dims = pressure.dims
        self.shape = pressure.shape
        self.count = math.prod(self.shape)
        maximum = (
            MAX_EGO_SCAN_SAMPLES
            if self.layout == "ego_timeseries"
            else MAX_INPUT_SAMPLES
        )
        if self.count > maximum:
            _fail("observation_limit", "Input sample count exceeds limits.")
        self.time_name = "JULD" if self.layout == "argo_profiles" else "TIME"
        if self.time_name not in dataset:
            _fail("missing_time", "Source sample time is missing.")
        self.time_units = _text(dataset[self.time_name].attrs.get("units"))
        self.calendar = _text(dataset[self.time_name].attrs.get("calendar", "standard"))
        if not self.time_units or " since " not in self.time_units:
            _fail("unsupported_time", "Source time units are unsupported.")
        if self.calendar not in CALENDARS:
            _fail("unsupported_calendar", "Source time calendar is unsupported.")

    def range_bounds(self, name):
        """Decode CF valid bounds in the same packed-value space as xarray."""
        import numpy as np

        if name not in self.ds:
            return None, None
        variable = self.ds[name]
        attributes = variable.attrs
        lower, upper = attributes.get("valid_min"), attributes.get("valid_max")
        if "valid_range" in attributes:
            if lower is not None or upper is not None:
                _fail("unsupported_range", "Conflicting declared valid bounds.")
            bounds = np.asarray(attributes["valid_range"])
            if bounds.shape != (2,):
                _fail("unsupported_range", "Declared valid range is unsupported.")
            lower, upper = bounds.tolist()
        if lower is None and upper is None:
            return None, None
        scale = _number(variable.encoding.get("scale_factor", 1))
        offset = _number(variable.encoding.get("add_offset", 0))
        if scale is None or scale == 0 or offset is None:
            _fail("unsupported_range", "Packed valid bounds are unsupported.")
        if str(variable.encoding.get("_Unsigned", "false")).lower() == "true":
            _fail("unsupported_range", "Unsigned packed valid bounds need inspection.")
        source_lower = _number(lower)
        source_upper = _number(upper)
        if (lower is not None and source_lower is None) or (
            upper is not None and source_upper is None
        ):
            _fail("unsupported_range", "Declared valid bounds must be finite.")
        if (
            source_lower is not None
            and source_upper is not None
            and source_lower > source_upper
        ):
            _fail("unsupported_range", "Declared valid bounds are inverted.")
        lower = source_lower * scale + offset if source_lower is not None else None
        upper = source_upper * scale + offset if source_upper is not None else None
        return (upper, lower) if scale < 0 else (lower, upper)

    def source_encoding(self, name):
        if name not in self.ds:
            return None
        variable = self.ds[name]
        bounds = variable.attrs.get("valid_range")
        return {
            "scale_factor": _number(variable.encoding.get("scale_factor")),
            "add_offset": _number(variable.encoding.get("add_offset")),
            "valid_min": _number(
                bounds[0] if bounds is not None else variable.attrs.get("valid_min")
            ),
            "valid_max": _number(
                bounds[1] if bounds is not None else variable.attrs.get("valid_max")
            ),
        }

    def values(self, name: str, rows=None, *, required=False):
        """Read aligned selected values; never align GPS fixes by row order."""
        import numpy as np
        import xarray as xr

        length = self.count if rows is None else len(rows)
        if length > max(COORDINATE_SCAN_CHUNK, MAX_OBSERVATION_SAMPLES):
            _fail("observation_limit", "One observation read exceeds array limits.")
        if length == 0:
            return []
        if name not in self.ds:
            if required:
                _fail("missing_coordinates", "Required sample coordinates are missing.")
            return [None] * length
        variable = self.ds[name]
        if rows is None:
            rows = np.arange(self.count)
        indices = np.unravel_index(rows, self.shape)
        if variable.dims == self.sample_dims:
            selected = variable.isel(
                {
                    dim: xr.DataArray(index, dims="selected")
                    for dim, index in zip(self.sample_dims, indices, strict=True)
                }
            )
        elif self.layout == "argo_profiles" and variable.dims == ("N_PROF",):
            selected = variable.isel(N_PROF=xr.DataArray(indices[0], dims="selected"))
        elif variable.dims == ():
            # Scalar deployment metadata are safe, scalar sensor coordinates are not.
            if required or name in {"LATITUDE", "LONGITUDE", self.time_name}:
                _fail("unsupported_alignment", "Sample coordinates are not aligned.")
            return [variable.values.item()] * length
        else:
            _fail(
                "unsupported_alignment", "Observation variables are not sample-aligned."
            )
        values = selected.values.reshape(-1).tolist()
        lower, upper = self.range_bounds(name)
        if lower is not None or upper is not None:
            for index, item in enumerate(values):
                value = _number(item)
                if value is not None and (
                    (lower is not None and value < lower)
                    or (upper is not None and value > upper)
                ):
                    if name in {self.time_name, "LATITUDE", "LONGITUDE"}:
                        _fail(
                            "invalid_coordinate_metadata",
                            "Coordinate values conflict with declared valid bounds.",
                        )
                    values[index] = None
                    self.range_masked_variables.add(name)
        return values

    def mode_values(self, name: str, rows):
        direct_name = f"{name}_DATA_MODE"
        if direct_name in self.ds:
            return self.values(direct_name, rows)
        if self.layout == "argo_profiles" and "PARAMETER_DATA_MODE" in self.ds:
            if "STATION_PARAMETERS" not in self.ds:
                _fail("unsupported_data_mode", "Parameter data-mode names are missing.")
            modes = self.ds.PARAMETER_DATA_MODE
            parameters = self.ds.STATION_PARAMETERS
            if modes.dims != ("N_PROF", "N_PARAM") or parameters.dims != modes.dims:
                _fail(
                    "unsupported_data_mode",
                    "Parameter data-mode layout is unsupported.",
                )
            # Header/sample limits already bound these small metadata arrays.
            mode_values = modes.values
            names = parameters.values
            result = []
            for row in rows:
                profile = int(row) // self.shape[1]
                matches = [
                    i for i, item in enumerate(names[profile]) if _text(item) == name
                ]
                if len(matches) > 1:
                    _fail(
                        "unsupported_data_mode", "Parameter data modes are ambiguous."
                    )
                result.append(mode_values[profile, matches[0]] if matches else None)
            return result
        if "DATA_MODE" in self.ds:
            return self.values("DATA_MODE", rows)
        return [self.ds.attrs.get("data_mode")] * len(rows)


def _variable_info(reader: _Reader, name: str) -> ObservationVariableInfo:
    raw_name = name if name in reader.ds else None
    adjusted_name = name + "_ADJUSTED" if name + "_ADJUSTED" in reader.ds else None
    if not raw_name and not adjusted_name:
        _fail("unsupported_variable", "A requested observation variable is absent.")
    variable = reader.ds[raw_name or adjusted_name]
    units = _text(variable.attrs.get("units"))
    if not units:
        _fail("unsupported_units", "Observation variable units are required.")
    known_units = {
        "PRES": {"dbar", "decibar", "decibars"},
        "TEMP": {
            "degree_Celsius",
            "degrees_Celsius",
            "degree_C",
            "degrees_C",
            "degC",
            "deg C",
            "Celsius",
        },
        "PSAL": {"psu", "PSU", "1", "1e-3", "PSS-78", "PSS_78"},
        "GLIDER_DEPTH": {"m", "meter", "meters", "metre", "metres"},
    }
    if name in known_units and units not in known_units[name]:
        _fail("unsupported_units", "Observation units need a verified conversion.")
    if name == "GLIDER_DEPTH" and variable.attrs.get("positive") != "down":
        _fail("unsupported_depth", "Glider depth must explicitly be positive down.")
    if (
        name in {"GLIDER_DEPTH", "FLUORESCENCE_CHLA"}
        and reader.source_id != "ifremer_glider"
    ):
        _fail(
            "unsupported_variable", "This optional variable requires the EGO adapter."
        )
    adjusted_units = None
    if adjusted_name:
        adjusted_units = _text(reader.ds[adjusted_name].attrs.get("units"))
        if adjusted_units != units:
            _fail("unsupported_units", "Raw and adjusted units do not match.")
    error_name = name + "_ADJUSTED_ERROR"
    if (
        error_name in reader.ds
        and _text(reader.ds[error_name].attrs.get("units")) != units
    ):
        _fail("unsupported_units", "Adjusted error units do not match the variable.")
    return ObservationVariableInfo(
        source_name=name,
        units=units,
        long_name=_text(variable.attrs.get("long_name")),
        standard_name=_text(variable.attrs.get("standard_name")),
        raw_name=raw_name,
        adjusted_name=adjusted_name,
        adjusted_error_name=error_name if error_name in reader.ds else None,
        adjusted_units=adjusted_units,
        valid_min=reader.range_bounds(raw_name)[0] if raw_name else None,
        valid_max=reader.range_bounds(raw_name)[1] if raw_name else None,
        adjusted_valid_min=reader.range_bounds(adjusted_name)[0]
        if adjusted_name
        else None,
        adjusted_valid_max=reader.range_bounds(adjusted_name)[1]
        if adjusted_name
        else None,
        raw_encoding=reader.source_encoding(raw_name) if raw_name else None,
        adjusted_encoding=reader.source_encoding(adjusted_name)
        if adjusted_name
        else None,
        qc_convention="argo_reference_table_2"
        if reader.source_id == "argo"
        else "ego_reference_table_2",
    )


def _time_values(reader: _Reader, rows):
    import cftime

    result = []
    for value in reader.values(reader.time_name, rows, required=True):
        numeric = _number(value)
        if numeric is None:
            result.append(None)
            continue
        try:
            decoded = cftime.num2date(
                numeric, reader.time_units, calendar=reader.calendar
            )
            if not 1 <= decoded.year <= 9999:
                _fail(
                    "unsupported_time", "Time requires unsupported precision or range."
                )
            time_text = (
                f"{decoded.year:04d}-{decoded.month:02d}-{decoded.day:02d}"
                f"T{decoded.hour:02d}:{decoded.minute:02d}:{decoded.second:02d}"
            )
            if decoded.microsecond:
                time_text += f".{decoded.microsecond:06d}"
            result.append(time_text + "Z")
        except (ValueError, OverflowError):
            _fail("unsupported_time", "Source times cannot be decoded safely.")
    return result


def _selected(reader: _Reader, request: ObservationRequest):
    for name, permitted in (
        ("LATITUDE", {"degrees_north", "degree_north"}),
        ("LONGITUDE", {"degrees_east", "degree_east"}),
    ):
        if name not in reader.ds or reader.ds[name].attrs.get("units") not in permitted:
            _fail("unsupported_coordinates", "Sample position units are unsupported.")
    pressure_name = "PRES" if request.value_mode == "raw" else "PRES_ADJUSTED"
    selected = []
    missing = outside = 0
    latitude, longitude, normalized, pressure, times = {}, {}, {}, {}, {}
    for start in range(0, reader.count, COORDINATE_SCAN_CHUNK):
        rows = range(start, min(start + COORDINATE_SCAN_CHUNK, reader.count))
        lat_chunk = reader.values("LATITUDE", rows, required=True)
        lon_chunk = reader.values("LONGITUDE", rows, required=True)
        pressure_chunk = reader.values(pressure_name, rows)
        time_chunk = _time_values(reader, rows)
        for row, lat, lon, pres, time in zip(
            rows, lat_chunk, lon_chunk, pressure_chunk, time_chunk, strict=True
        ):
            lat, lon, pres = _number(lat), _number(lon), _number(pres)
            if lat is None or lon is None or pres is None or time is None:
                missing += 1
                continue
            if not -90 <= lat <= 90 or not -180 <= lon <= 360:
                _fail(
                    "unsupported_coordinates",
                    "Sample positions are outside valid ranges.",
                )
            normalized_lon = (lon + 180) % 360 - 180
            region = request.region
            if not (
                region.west <= normalized_lon <= region.east
                and region.south <= lat <= region.north
                and request.pressure_min_dbar <= pres <= request.pressure_max_dbar
                and request.start_date.isoformat()
                <= time[:10]
                <= request.end_date.isoformat()
            ):
                outside += 1
                continue
            selected.append(row)
            if len(selected) > MAX_OBSERVATION_SAMPLES:
                _fail(
                    "observation_limit",
                    "Selected samples exceed scientific limits; narrow the selection.",
                )
            latitude[row], longitude[row], normalized[row] = lat, lon, normalized_lon
            pressure[row], times[row] = pres, time
    return selected, latitude, longitude, normalized, pressure, times, missing, outside


def _value_bundle(reader, info, request, rows):
    name = info.source_name
    result = {
        "raw": reader.values(name, rows),
        "raw_qc": reader.values(name + "_QC", rows),
        "adjusted": reader.values(name + "_ADJUSTED", rows),
        "adjusted_qc": reader.values(name + "_ADJUSTED_QC", rows),
        "adjusted_error": reader.values(name + "_ADJUSTED_ERROR", rows),
        "mode": reader.mode_values(name, rows),
    }
    return result


def _chosen_value(info, bundle, position, request, coordinates_ok):
    raw = _number(bundle["raw"][position])
    adjusted = _number(bundle["adjusted"][position])
    raw_qc = _qc(bundle["raw_qc"][position])
    adjusted_qc = _qc(bundle["adjusted_qc"][position])
    error = _number(bundle["adjusted_error"][position])
    if error is not None and error < 0:
        _fail("unsupported_error", "Adjusted uncertainty cannot be negative.")
    mode = _mode(bundle["mode"][position])
    kind = request.value_mode
    value, flag = (raw, raw_qc) if kind == "raw" else (adjusted, adjusted_qc)
    selected_name = info.raw_name if kind == "raw" else info.adjusted_name
    exclusions = []
    if value is None:
        exclusions.append("selected_value_missing")
    if flag not in ACCEPTED_QC:
        exclusions.append("variable_qc_missing_or_rejected")
    if not coordinates_ok:
        exclusions.append("coordinate_qc_missing_or_rejected")
    if mode is None:
        exclusions.append("data_mode_unknown")
    elif kind == "adjusted" and mode not in {"A", "D"}:
        exclusions.append("adjusted_data_mode_not_available")
    if info.source_name == "FLUORESCENCE_CHLA":
        exclusions.append("fluorescence_calibration_not_evaluated")
    return ObservationValue(
        raw=raw,
        raw_qc=raw_qc,
        adjusted=adjusted,
        adjusted_qc=adjusted_qc,
        adjusted_error=error,
        data_mode=mode,
        selected_kind=kind,
        selected_source_name=selected_name,
        selected_value=value,
        selected_qc=flag,
        qc_eligible=not exclusions,
        exclusions=exclusions,
    )


def _build_collection(
    path, request, source_id, dataset_id, data_mode, client_processing, identity, ds
):
    reader = _Reader(ds, source_id)
    infos = {name: _variable_info(reader, name) for name in request.variables}
    selected, latitudes, longitudes, normalized, pressures, times, missing, outside = (
        _selected(reader, request)
    )
    collection_id = _identifier(
        "o_",
        {
            "processing": OBSERVATION_PROCESSING_VERSION,
            "sha256": identity.sha256,
            "source": source_id,
            "dataset": dataset_id,
            "request": request.model_dump(mode="json"),
            "data_mode": data_mode,
            "client_processing": client_processing,
        },
    )
    time_qc = reader.values(reader.time_name + "_QC", selected)
    position_qc = reader.values("POSITION_QC", selected)
    platforms = (
        reader.values("PLATFORM_NUMBER", selected)
        if source_id == "argo"
        else [ds.attrs.get("platform_code")] * len(selected)
    )
    cycles = reader.values("CYCLE_NUMBER", selected)
    directions = reader.values("DIRECTION", selected)
    discriminator_name = next(
        (
            name
            for name in ("PROFILE_ID", "PROFILE_NUMBER", "CONFIG_MISSION_NUMBER")
            if name in ds
        ),
        None,
    )
    discriminators = (
        reader.values(discriminator_name, selected)
        if discriminator_name
        else [None] * len(selected)
    )
    bundles = {
        name: _value_bundle(reader, info, request, selected)
        for name, info in infos.items()
    }
    samples = []
    coordinate_rejected = 0
    variable_rejected = dict.fromkeys(infos, 0)
    for index, row in enumerate(selected):
        platform = _text(platforms[index])
        cycle_text = _text(cycles[index])
        cycle = int(cycle_text) if cycle_text and cycle_text.isdigit() else None
        direction = _text(directions[index])
        if direction not in {None, "A", "D"}:
            _fail(
                "unsupported_identity", "Observation profile direction is unsupported."
            )
        discriminator = _text(discriminators[index])
        source_profile = (
            row // reader.shape[1] if reader.layout == "argo_profiles" else None
        )
        source_level = (
            row % reader.shape[1] if reader.layout == "argo_profiles" else None
        )
        if reader.layout == "argo_profiles":
            has_profile = bool(platform and cycle is not None and direction)
        elif reader.layout == "argo_points":
            has_profile = bool(
                platform
                and cycle is not None
                and direction
                and discriminator
                and discriminator_name in {"PROFILE_ID", "PROFILE_NUMBER"}
            )
        else:
            # CONFIG_MISSION is not a glider profile identifier.
            has_profile = bool(
                discriminator and discriminator_name in {"PROFILE_ID", "PROFILE_NUMBER"}
            )
        profile_id = (
            _identifier(
                "r_",
                [
                    source_id,
                    identity.sha256,
                    platform,
                    cycle,
                    direction,
                    source_profile,
                    discriminator,
                ],
            )
            if has_profile
            else None
        )
        time_flag, position_flag = _qc(time_qc[index]), _qc(position_qc[index])
        coordinates_ok = time_flag in ACCEPTED_QC and position_flag in ACCEPTED_QC
        values = {
            name: _chosen_value(info, bundles[name], index, request, coordinates_ok)
            for name, info in infos.items()
        }
        # Pressure QC is required for all samples in this pressure selection.
        if not values["PRES"].qc_eligible:
            for name, value in list(values.items()):
                if name != "PRES":
                    values[name] = value.model_copy(
                        update={
                            "qc_eligible": False,
                            "exclusions": [
                                *value.exclusions,
                                "pressure_qc_missing_or_rejected",
                            ],
                        }
                    )
        coordinates_ok = values["PRES"].qc_eligible
        coordinate_rejected += int(not coordinates_ok)
        for name, value in values.items():
            variable_rejected[name] += int(not value.qc_eligible)
        depth = values.get("GLIDER_DEPTH")
        depth_m = depth.selected_value if depth and depth.qc_eligible else None
        if depth_m is not None and depth_m < 0:
            _fail("unsupported_depth", "Positive-down glider depth cannot be negative.")
        samples.append(
            ObservationSample(
                sample_id=_identifier("s_", [identity.sha256, source_id, row]),
                source_sample_index=row,
                source_profile_index=source_profile,
                source_level_index=source_level,
                profile_id=profile_id,
                profile_identity_status="source_profile"
                if has_profile
                else "ambiguous_points"
                if reader.layout == "argo_points"
                else "track_only",
                platform_id=platform,
                cycle_number=cycle,
                direction=direction,
                profile_discriminator=discriminator,
                time=times[row],
                longitude=normalized[row],
                source_longitude=longitudes[row],
                latitude=latitudes[row],
                pressure_dbar=pressures[row],
                depth_m=depth_m,
                time_qc=time_flag,
                position_qc=position_flag,
                coordinate_qc_eligible=coordinates_ok,
                values=values,
            )
        )
    warnings = [
        "quantities_not_harmonized_for_comparison",
        "qc_rejected_selected_samples_retained",
        "pressure_dbar_is_not_depth_m",
    ]
    if reader.layout == "argo_points":
        warnings.append("argopy_point_representation_is_not_untouched_gdac")
    if "TIME_GPS" in ds or "LATITUDE_GPS" in ds:
        warnings.append("separate_gps_fixes_not_zipped_to_sensor_samples")
    if any(sample.profile_id is None for sample in samples):
        warnings.append("some_samples_have_no_verified_profile_identity")
    if client_processing == "local_operator_input_client_processing_unknown":
        warnings.append("prior_client_filtering_unknown")
    if reader.range_masked_variables:
        warnings.append("declared_valid_range_masks_applied")
    return ObservationCollection(
        collection_id=collection_id,
        source_id=source_id,
        dataset_id=dataset_id,
        source_filename=path.name,
        input_file=identity,
        data_mode=data_mode,
        client_processing=client_processing,
        selection=request,
        layout=reader.layout,
        source_time_name=reader.time_name,
        source_time_units=reader.time_units,
        source_time_calendar=reader.calendar,
        variables=infos,
        samples=samples,
        counts=ObservationCounts(
            input_samples=reader.count,
            selected_samples=len(samples),
            outside_selection=outside,
            missing_filter_coordinates=missing,
            coordinate_qc_rejected=coordinate_rejected,
            variable_qc_rejected=variable_rejected,
        ),
        capabilities=ObservationCapabilities(
            profiles=any(sample.profile_id is not None for sample in samples)
        ),
        warnings=warnings,
    )


def normalize_observations(
    path: Path,
    request: ObservationRequest,
    *,
    source_id: str,
    dataset_id: str,
    data_mode: str = "real",
    client_processing: str = "local_operator_input_client_processing_unknown",
) -> ObservationCollection:
    """Return samples without writes; caller contains the trusted raw path."""
    if source_id not in {"argo", "ifremer_glider"}:
        _fail("unsupported_source", "Observation source is unsupported.")
    if path.suffix.lower() != ".nc":
        _fail("unsupported_file", "An explicit local NetCDF file is required.")
    try:
        identity = describe_file(path, MAX_INPUT_BYTES)
        _preflight(path)
        import xarray as xr

        with xr.open_dataset(
            path,
            engine="netcdf4",
            decode_times=False,
            cache=False,
            create_default_indexes=False,
        ) as dataset:
            result = _build_collection(
                path,
                request,
                source_id,
                dataset_id,
                data_mode,
                client_processing,
                identity,
                dataset,
            )
        if stat_file(path, MAX_INPUT_BYTES) != (
            identity.size_bytes,
            identity.modified_ns,
        ):
            _fail("input_changed", "Observation source changed during normalization.")
        if len(result.model_dump_json().encode()) > MAX_OBSERVATION_JSON_BYTES:
            _fail("observation_limit", "Normalized observation JSON exceeds limits.")
        return result
    except ProductError:
        raise
    except ImportError:
        _fail(
            "dependency_unavailable",
            "Observation scientific dependencies are unavailable.",
        )
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RuntimeError):
        raise ProductError(
            "invalid_observations", "Observation input could not be normalized safely."
        ) from None
