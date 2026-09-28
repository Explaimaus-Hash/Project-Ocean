"""Read-only provider row verification and safe operator failures."""

import json

import netCDF4
import numpy as np
import pytest
import test_quantities

from backend.app.processing.quantity_audit import _provider_parameters
from backend.app.storage.product_common import ProductError
from scripts import audit_quantities as cli


@pytest.fixture
def collection(tmp_path):
    return test_quantities.collection.__wrapped__(tmp_path)


@pytest.fixture
def provider(tmp_path, collection):
    path = tmp_path / "provider.nc"
    with netCDF4.Dataset(path, "w", format="NETCDF3_CLASSIC") as ds:
        ds.createDimension("row", len(collection.samples))
        ds.createDimension("char", 1)
        numbers = {"latitude": 5, "longitude": 70, "time": 1}
        flags = {"time_qc": "1", "position_qc": "1", "data_mode": "D"}
        for name, value, units, low, high, standard, long in (
            (
                "pres",
                5,
                "dbar",
                0,
                12000,
                "sea_water_pressure",
                "Sea water pressure, equals 0 at sea-level",
            ),
            (
                "temp",
                21,
                "degree_Celsius",
                -2.5,
                40,
                "sea_water_temperature",
                "Sea temperature in-situ ITS-90 scale",
            ),
            (
                "psal",
                35,
                "psu",
                2,
                41,
                "sea_water_practical_salinity",
                "Practical salinity",
            ),
        ):
            numbers.update(
                {
                    name: value,
                    name + "_adjusted": value + 0.5,
                    name + "_adjusted_error": 0.1,
                }
            )
            flags.update({name + "_qc": "1", name + "_adjusted_qc": "2"})
            var = ds.createVariable(name + "_adjusted", "f8", ("row",))
            var.units, var.valid_min, var.valid_max = units, low, high
            var.standard_name, var.long_name = standard, long
        for name, value in numbers.items():
            var = (
                ds[name]
                if name in ds.variables
                else ds.createVariable(name, "f8", ("row",))
            )
            var[:] = value
        ds["time"].units = "days since 2024-01-01 00:00:00"
        for name, value in flags.items():
            ds.createVariable(name, "S1", ("row", "char"))[:] = np.full(
                (len(collection.samples), 1), value.encode()
            )
    return path


def test_provider_metadata_and_read_only(provider, collection):
    before = provider.read_bytes()
    parameters = _provider_parameters(provider, collection)
    assert parameters[1].valid_min == -2.5
    assert parameters[2].definition == "practical_salinity_PSS78"
    assert provider.read_bytes() == before


@pytest.mark.parametrize(
    "name,value", [("latitude", 4), ("pres_adjusted", 5.4), ("temp_adjusted_error", 1)]
)
def test_provider_mismatch_rejected(provider, collection, name, value):
    with netCDF4.Dataset(provider, "a") as ds:
        ds[name][0] = value
    with pytest.raises(ProductError):
        _provider_parameters(provider, collection)


def test_cli_invalid_ids_no_trace(capsys):
    assert (
        cli.main(
            [
                "--collection-id",
                "../private",
                "--acquisition-id",
                "bad",
                "--model-id",
                "bad",
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert not output.out
    assert "private" not in output.err and "Traceback" not in output.err
    assert "error" in json.loads(output.err)
