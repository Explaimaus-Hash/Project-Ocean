"""Bounded, header-only NetCDF inspection for explicit local operator tasks.

No variable values, coordinate extents, or scientific capabilities are evaluated.
Limits bound the serialized report, not allocation performed internally by the
NetCDF library while opening headers or obtaining an individual attribute. Inputs
must therefore remain trusted local operator inputs, not arbitrary public uploads.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)

MAX_DIMENSIONS = 64
MAX_VARIABLES = 512
MAX_ATTRIBUTES_PER_OBJECT = 128
MAX_TOTAL_ATTRIBUTES = 4096
MAX_ATTRIBUTE_ELEMENTS = 2048
MAX_ATTRIBUTE_BYTES = 65_536
MAX_NAME_LENGTH = 256
MAX_SERIALIZED_NODES = 65_536
MAX_REPORT_BYTES = 2 * 1024 * 1024

_DECLARED_COVERAGE_ATTRIBUTES = (
    "geospatial_lat_min",
    "geospatial_lat_max",
    "geospatial_lat_units",
    "geospatial_lon_min",
    "geospatial_lon_max",
    "geospatial_lon_units",
    "geospatial_vertical_min",
    "geospatial_vertical_max",
    "geospatial_vertical_units",
    "geospatial_vertical_positive",
    "time_coverage_start",
    "time_coverage_end",
    "time_coverage_duration",
    "time_coverage_resolution",
)


class MetadataInspectionError(Exception):
    """Inspection failure with a stable code and a path-free safe message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _limit_error() -> MetadataInspectionError:
    return MetadataInspectionError(
        "metadata_limit_exceeded", "NetCDF metadata exceeds the prototype limits."
    )


def _unsupported_metadata() -> MetadataInspectionError:
    return MetadataInspectionError(
        "unsupported_metadata", "NetCDF metadata contains an unsupported value type."
    )


@dataclass
class _Budget:
    attributes: int = 0
    nodes: int = 0
    value_bytes: int = 0
    non_finite_values: bool = False

    def add(self, *, nodes: int = 0, value_bytes: int = 0) -> None:
        self.nodes += nodes
        self.value_bytes += value_bytes
        if self.nodes > MAX_SERIALIZED_NODES or self.value_bytes > MAX_REPORT_BYTES:
            raise _limit_error()


def _name(value: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_NAME_LENGTH:
        raise _limit_error()
    return value


def _json_value(value: Any, budget: _Budget, np: Any, depth: int = 0) -> JsonValue:
    """Serialize only bounded primitive metadata, making nonfinite values null."""
    budget.add(nodes=1)
    if depth > 4:
        raise _limit_error()
    if isinstance(value, np.ndarray):
        if value.size > MAX_ATTRIBUTE_ELEMENTS or value.nbytes > MAX_ATTRIBUTE_BYTES:
            raise _limit_error()
        if value.dtype.kind not in "biufSUO":
            raise _unsupported_metadata()
        return _json_value(value.tolist(), budget, np, depth + 1)
    if isinstance(value, np.generic):
        return _json_value(value.item(), budget, np, depth + 1)
    if isinstance(value, bytes):
        if len(value) > MAX_ATTRIBUTE_BYTES:
            raise _limit_error()
        try:
            value = value.decode("utf-8")
        except UnicodeError:
            raise _unsupported_metadata() from None
    if isinstance(value, str):
        if len(value) > MAX_ATTRIBUTE_BYTES:
            raise _limit_error()
        encoded_length = len(value.encode("utf-8"))
        if encoded_length > MAX_ATTRIBUTE_BYTES:
            raise _limit_error()
        budget.add(value_bytes=encoded_length)
        return value
    if value is None or isinstance(value, bool):
        budget.add(value_bytes=5)
        return value
    if isinstance(value, int):
        budget.add(value_bytes=32)
        return value
    if isinstance(value, float):
        budget.add(value_bytes=32)
        if not math.isfinite(value):
            budget.non_finite_values = True
            return None
        return value
    if isinstance(value, list | tuple):
        if len(value) > MAX_ATTRIBUTE_ELEMENTS:
            raise _limit_error()
        return [_json_value(item, budget, np, depth + 1) for item in value]
    raise _unsupported_metadata()


def _attributes(owner: Any, budget: _Budget, np: Any) -> dict[str, JsonValue]:
    names = owner.ncattrs()
    if len(names) > MAX_ATTRIBUTES_PER_OBJECT:
        raise _limit_error()
    budget.attributes += len(names)
    if budget.attributes > MAX_TOTAL_ATTRIBUTES:
        raise _limit_error()
    return {
        _name(name): _json_value(owner.getncattr(name), budget, np) for name in names
    }


def _coordinate_candidates(
    name: str, attributes: dict[str, JsonValue]
) -> list[JsonValue]:
    """Report evidence, not verified geometry or renderable capabilities."""
    evidence: dict[str, list[JsonValue]] = {}

    def add(role: str, reason: str) -> None:
        evidence.setdefault(role, []).append(reason)

    standard_name = attributes.get("standard_name")
    if standard_name in ("longitude", "latitude", "time"):
        add(str(standard_name), f"standard_name={standard_name}")
    if standard_name in (
        "depth",
        "height",
        "altitude",
        "sea_water_pressure",
        "ocean_sigma_coordinate",
        "ocean_s_coordinate",
        "ocean_s_coordinate_g1",
        "ocean_s_coordinate_g2",
    ):
        add("vertical", f"standard_name={standard_name}")

    axis = attributes.get("axis")
    axis_roles = {
        "X": "horizontal_x",
        "Y": "horizontal_y",
        "Z": "vertical",
        "T": "time",
    }
    if isinstance(axis, str) and axis.upper() in axis_roles:
        add(axis_roles[axis.upper()], f"axis={axis}")

    units = attributes.get("units")
    if isinstance(units, str):
        normalized_units = units.strip().lower()
        if normalized_units in (
            "degrees_east",
            "degree_east",
            "degree_e",
            "degrees_e",
            "degreee",
            "degreese",
        ):
            add("longitude", f"units={units}")
        if normalized_units in (
            "degrees_north",
            "degree_north",
            "degree_n",
            "degrees_n",
            "degreen",
            "degreesn",
        ):
            add("latitude", f"units={units}")
        if " since " in normalized_units:
            add("time", f"units={units}; calendar and values not decoded")

    name_roles = {
        "lon": "longitude",
        "longitude": "longitude",
        "lat": "latitude",
        "latitude": "latitude",
        "time": "time",
        "juld": "time",
        "depth": "vertical",
        "height": "vertical",
        "pres": "vertical",
        "pressure": "vertical",
    }
    if name.lower() in name_roles:
        add(name_roles[name.lower()], f"variable_name={name}; name-only hint")
    return [
        {"name": name, "role": role, "evidence": reasons}
        for role, reasons in evidence.items()
    ]


def _inspect_header(dataset: Any, np: Any) -> dict[str, JsonValue]:
    if dataset.groups:
        raise MetadataInspectionError(
            "unsupported_groups", "Hierarchical NetCDF groups are not supported yet."
        )
    if (
        len(dataset.dimensions) > MAX_DIMENSIONS
        or len(dataset.variables) > MAX_VARIABLES
    ):
        raise _limit_error()

    budget = _Budget()
    global_attributes = _attributes(dataset, budget, np)
    dimensions: dict[str, JsonValue] = {
        _name(name): {"length": len(dimension), "unlimited": dimension.isunlimited()}
        for name, dimension in dataset.dimensions.items()
    }
    variables: dict[str, JsonValue] = {}
    candidates: list[JsonValue] = []
    for name, variable in dataset.variables.items():
        _name(name)
        # Enum, compound, and numeric variable-length arrays need a later contract.
        if variable.datatype is str:
            dtype = "string"
        elif isinstance(variable.datatype, np.dtype) and variable.dtype.kind in "iufSU":
            dtype = str(variable.dtype)
        else:
            raise MetadataInspectionError(
                "unsupported_data_type",
                "Custom NetCDF variable types are not supported yet.",
            )
        attributes = _attributes(variable, budget, np)
        observations: list[JsonValue] = []
        for required_name in ("units", "standard_name"):
            if required_name not in attributes:
                observations.append(f"{required_name}_not_declared")
        if len(variable.dimensions) > MAX_DIMENSIONS:
            raise _limit_error()
        variables[name] = {
            "dimensions": [_name(dimension) for dimension in variable.dimensions],
            "shape": [int(length) for length in variable.shape],
            "dtype": dtype,
            "attributes": attributes,
            "chunking": _json_value(variable.chunking(), budget, np),
            "observations": observations,
        }
        candidates.extend(_coordinate_candidates(name, attributes))

    report: dict[str, JsonValue] = {
        "inspection_mode": "header_only",
        "data_values_read": False,
        "data_model": str(dataset.data_model),
        "dimensions": dimensions,
        "variables": variables,
        "global_attributes": global_attributes,
        "coordinate_candidates": candidates,
        "coverage": {
            "verification": "not_computed",
            "coordinate_values_read": False,
            "declared_global_attributes": {
                name: global_attributes[name]
                for name in _DECLARED_COVERAGE_ATTRIBUTES
                if name in global_attributes
            },
            "note": (
                "Declared coverage is unverified; no axis values were read or decoded."
            ),
        },
        "capability_status": "not_evaluated",
        "observations": (
            ["non_finite_attribute_values_serialized_as_null"]
            if budget.non_finite_values
            else []
        ),
    }
    encoded = json.dumps(report, allow_nan=False, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_REPORT_BYTES:
        raise _limit_error()
    return report


def inspect_netcdf_metadata(path: Path) -> dict[str, JsonValue]:
    """Inventory a trusted local NetCDF header without reading variable arrays.

    Raises MetadataInspectionError with fixed, safe messages. Scientific libraries
    load only when the operator explicitly calls this function, never at import.
    All handles close on success, validation failure, or an underlying read error.
    This function does not verify the source checksum or mark a dataset as ready.
    """
    try:
        import netCDF4
        import numpy as np
    except ImportError:
        raise MetadataInspectionError(
            "dependency_unavailable", "NetCDF inspection dependencies are unavailable."
        ) from None
    try:
        with netCDF4.Dataset(str(path), mode="r") as dataset:
            return _inspect_header(dataset, np)
    except MetadataInspectionError:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, UnicodeError, OverflowError):
        raise MetadataInspectionError(
            "invalid_netcdf",
            "The local file could not be inspected as a supported NetCDF.",
        ) from None
