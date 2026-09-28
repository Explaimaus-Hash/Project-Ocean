"""Read-only, bounded adapter for preserved Argo ERDDAP and native model metadata."""

import math
import re
from datetime import UTC, datetime

from ..ingestion.acquisition import read_acquisition
from ..schemas.models import ModelManifest
from ..schemas.quantities import ProviderParameter, QuantityEvidence
from ..storage.observations import ObservationStore, observation_id
from ..storage.product_common import ProductError, describe_file, read_json
from .prepare_model import private_path
from .quantities import derive_quantities


def _require(condition):
    if not condition:
        raise ProductError(
            "quantity_source_mismatch", "Quantity source verification failed."
        )


def audit_quantities(root, collection_id, acquisition_id, model_id):
    """Verify original values/QC/coordinates before deriving a private report.

    Only the inspected uncompressed scalar ERDDAP row layout is supported.
    This deliberately rejects unknown transforms/layouts instead of guessing.
    """
    collection_id = observation_id(collection_id)
    _require(re.fullmatch(r"a_[a-f0-9]{24}", acquisition_id))
    _require(re.fullmatch(r"m_[a-f0-9]{24}", model_id))
    paths = {
        "collection": private_path(
            root, f"data/observations/{collection_id}/collection.json"
        ),
        "client": private_path(
            root, f"data/raw/acquisitions/{acquisition_id}/input.nc"
        ),
        "provider": private_path(
            root, f"data/raw/acquisitions/{acquisition_id}/provider_input.nc"
        ),
        "model": private_path(root, f"data/models/{model_id}/manifest.json"),
    }
    before = {
        name: describe_file(path, 16 * 1024 * 1024) for name, path in paths.items()
    }
    collection = ObservationStore(root).collection(collection_id)
    acquisition = read_acquisition(root, acquisition_id)
    _require(collection.source_id == acquisition.source_id == "argo")
    _require(collection.layout == "argo_points")
    _require(collection.client_processing == "argopy_expert_no_qc_filter")
    _require(collection.input_file == before["client"] == acquisition.input_file)
    _require(before["provider"] == acquisition.provider_file)
    model = ModelManifest.model_validate(read_json(paths["model"], 1024 * 1024))
    _require(model.model_id == model_id)
    fields = {v.source_name: v for v in model.identity.variables}
    _require({"so", "thetao"} <= fields.keys())
    parameters = _provider_parameters(paths["provider"], collection)
    so, thetao = fields["so"], fields["thetao"]
    salinity_verified = (
        so.units == "1e-3"
        and so.standard_name == "sea_water_salinity"
        and so.unit_long == "Practical Salinity Unit"
    )
    evidence = QuantityEvidence(
        client_input_sha256=before["client"].sha256,
        provider_input_sha256=before["provider"].sha256,
        verification_evidence=(
            "Preserved acquisition hashes; exact provider/client collection row "
            "values, errors, modes, QC, time and position checked by quantity_audit v1."
        ),
        parameters=parameters,
        model_identity=model_id,
        model_evidence="Validated native-model manifest SHA256 "
        + before["model"].sha256
        + "; quantity metadata only, no model field read or matching.",
        model_salinity="practical_salinity_PSS78"
        if salinity_verified
        else "unresolved",
        model_temperature="potential_temperature"
        if thetao.standard_name == "sea_water_potential_temperature"
        else "unresolved",
        model_temperature_scale="unresolved",
        model_reference_pressure_dbar=None,
    )
    report = derive_quantities(collection, evidence)
    _require(
        all(
            describe_file(paths[name], 16 * 1024 * 1024) == value
            for name, value in before.items()
        )
    )
    return report


def _provider_parameters(path, collection):
    import netCDF4
    import numpy as np

    def number(ds, name, index):
        value = ds[name][index]
        return (
            None
            if np.ma.is_masked(value) or not math.isfinite(float(value))
            else float(value)
        )

    def text(ds, name, index):
        return (
            np.asarray(ds[name][index]).tobytes().decode("ascii").strip("\x00 ") or None
        )

    definitions = {
        "PRES": (
            "sea_water_pressure",
            "Sea water pressure, equals 0 at sea-level",
            "sea_pressure_dbar",
        ),
        "TEMP": (
            "sea_water_temperature",
            "Sea temperature in-situ ITS-90 scale",
            "in_situ_ITS90_C",
        ),
        "PSAL": (
            "sea_water_practical_salinity",
            "Practical salinity",
            "practical_salinity_PSS78",
        ),
    }
    with netCDF4.Dataset(path, "r") as ds:
        _require("row" in ds.dimensions and len(ds.dimensions["row"]) <= 100000)
        _require(len(ds.variables) <= 100)
        for var in ds.variables.values():
            _require(var.size <= 100000 and var.dtype.kind in "fiuS")
            _require(var.dimensions[0] == "row" and var.ndim in (1, 2))
            _require(var.chunking() in (None, "contiguous"))
            _require(
                not any(
                    n in var.ncattrs()
                    for n in ("scale_factor", "add_offset", "_Unsigned")
                )
            )
        parameters = []
        for name, (standard, long_name, definition) in definitions.items():
            variable = ds[name.lower() + "_adjusted"]
            verified = (
                getattr(variable, "standard_name", None) == standard
                and getattr(variable, "long_name", None) == long_name
            )
            parameters.append(
                ProviderParameter(
                    name=name,
                    adjusted_name=variable.name,
                    units=variable.units,
                    definition=definition if verified else "unresolved",
                    definition_evidence=(
                        f"provider_input.nc {variable.name}: "
                        f"standard_name={getattr(variable, 'standard_name', '')}; "
                        f"long_name={getattr(variable, 'long_name', '')}"
                    ),
                    valid_min=float(variable.valid_min),
                    valid_max=float(variable.valid_max),
                )
            )
        for sample in collection.samples:
            index = sample.source_sample_index
            _require(index < len(ds.dimensions["row"]))
            _require(number(ds, "latitude", index) == sample.latitude)
            _require(number(ds, "longitude", index) == sample.source_longitude)
            stamp = netCDF4.num2date(
                ds["time"][index],
                ds["time"].units,
                calendar=getattr(ds["time"], "calendar", "standard"),
                only_use_cftime_datetimes=False,
            )
            _require(stamp.replace(tzinfo=UTC) == datetime.fromisoformat(sample.time))
            _require(text(ds, "time_qc", index) == sample.time_qc)
            _require(text(ds, "position_qc", index) == sample.position_qc)
            for name in definitions:
                original = sample.values[name]
                prefix = name.lower()
                _require(text(ds, "data_mode", index) == original.data_mode)
                for suffix, expected in (
                    ("", original.raw),
                    ("_adjusted", original.adjusted),
                    ("_adjusted_error", original.adjusted_error),
                ):
                    _require(number(ds, prefix + suffix, index) == expected)
                _require(text(ds, prefix + "_qc", index) == original.raw_qc)
                _require(
                    text(ds, prefix + "_adjusted_qc", index) == original.adjusted_qc
                )
    return tuple(parameters)
