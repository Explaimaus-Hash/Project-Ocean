"""Native reader integrity and masks; only temporary synthetic files."""

import shutil

import netCDF4
import numpy as np
import pytest

from backend.app.comparison import model_reader
from backend.app.processing.prepare_model import prepare_model
from backend.app.schemas.model_reading import NativeFieldSnapshot
from backend.app.schemas.models import ModelManifest
from backend.app.storage.product_common import ProductError, describe_file
from backend.tests.test_model_preparation import local_model as _local_model


@pytest.fixture(scope="module")
def prepared_reader(tmp_path_factory):
    root = tmp_path_factory.mktemp("native_reader")
    with pytest.MonkeyPatch.context() as patch:
        root, raw, request = _local_model.__wrapped__(root, patch)
        manifest = prepare_model(request, root)
    return root, manifest


@pytest.fixture
def isolated_reader(prepared_reader, tmp_path):
    root, manifest = prepared_reader
    target = tmp_path / "copy"
    shutil.copytree(root, target, copy_function=shutil.copy2)
    return target, manifest


def refresh(root, manifest, name):
    directory = root / "data/models" / manifest.model_id
    data = manifest.model_dump(mode="json")
    field = "scientific_file" if name == "fields.nc" else "source_metadata_file"
    data[field] = describe_file(directory / name, 134217728).model_dump(mode="json")
    updated = ModelManifest.model_validate(data)
    (directory / "manifest.json").write_text(updated.model_dump_json())


@pytest.mark.parametrize("variable,missing", [("so", 5), ("thetao", 6)])
def test_native_values_identity_masks_and_immutability(
    prepared_reader, variable, missing
):
    root, manifest = prepared_reader
    directory = root / "data/models" / manifest.model_id
    records = {p.name: describe_file(p, 134217728) for p in directory.iterdir()}
    result = model_reader.read_native_field(root, manifest.model_id, variable)
    assert result.manifest == manifest
    assert result.manifest_file == records["manifest.json"]
    assert result.manifest.identity.provenance.data_mode == "synthetic"
    assert len(result.values) == 16
    assert result.values[1:11] == tuple(10 + i * 0.5 for i in range(1, 11))
    assert result.values.count(None) == missing
    assert result.valid_mask.count(False) == missing
    assert result.values[0] == (10 if variable == "so" else None)
    assert result.comparison_ready is False
    assert result.manifest.identity.axes.times[0].hour == 0
    assert records == {p.name: describe_file(p, 134217728) for p in directory.iterdir()}
    with pytest.raises(ValueError):
        result.source_variable = "so"


@pytest.mark.parametrize("name", ["manifest.json", "fields.nc", "source_metadata.json"])
def test_corruption_rejected(isolated_reader, name):
    root, manifest = isolated_reader
    path = root / "data/models" / manifest.model_id / name
    path.write_bytes(b"invalid local fixture")
    with pytest.raises(ProductError) as error:
        model_reader.read_native_field(root, manifest.model_id, "so")
    assert str(root) not in error.value.message


@pytest.mark.parametrize(
    "case",
    ["units", "packing", "axis", "time", "identity", "positive", "calendar", "fill"],
)
def test_rehashed_header_tampering_rejected(isolated_reader, case):
    root, manifest = isolated_reader
    path = root / "data/models" / manifest.model_id / "fields.nc"
    with netCDF4.Dataset(path, "a") as ds:
        if case == "units":
            ds["so"].units = "wrong"
        elif case == "packing":
            ds["so"].scale_factor = 0.5
        elif case == "axis":
            ds["latitude"][:] = [-0.9, 0]
        elif case == "time":
            ds["time"][:] = [12, 36]
        elif case == "identity":
            ds.model_id = "m_" + "f" * 24
        elif case == "positive":
            ds["depth"].positive = "up"
        elif case == "calendar":
            ds["time"].calendar = "standard"
        elif case == "fill":
            ds["so"].missing_value = np.float64(-999)
    refresh(root, manifest, "fields.nc")
    with pytest.raises(ProductError):
        model_reader.read_native_field(root, manifest.model_id, "so")


def test_infinity_is_missing_without_changing_neighbour(isolated_reader):
    root, manifest = isolated_reader
    path = root / "data/models" / manifest.model_id / "fields.nc"
    with netCDF4.Dataset(path, "a") as ds:
        ds["so"][0, 0, 0, 0] = np.inf
    refresh(root, manifest, "fields.nc")
    result = model_reader.read_native_field(root, manifest.model_id, "so")
    assert result.values[:2] == (None, 10.5)
    assert result.valid_mask[:2] == (False, True)


@pytest.mark.parametrize("model_id", ["../private", "m_" + "z" * 24, "", None])
def test_unsafe_identifier_rejected_before_io(tmp_path, model_id, monkeypatch):
    monkeypatch.setattr(model_reader, "describe_file", lambda *a: pytest.fail("I/O"))
    with pytest.raises(ProductError, match="invalid_model_id"):
        model_reader.read_native_field(tmp_path, model_id, "so")


def test_budget_rejects_before_field_read(prepared_reader, monkeypatch):
    root, manifest = prepared_reader
    monkeypatch.setattr(model_reader, "MAX_FIELD_VALUES", 15)
    monkeypatch.setattr(
        model_reader, "_read_fields", lambda *a: pytest.fail("field read")
    )
    with pytest.raises(ProductError, match="model_field_limit"):
        model_reader.read_native_field(root, manifest.model_id, "so")


def test_snapshot_rejects_misaligned_mask(prepared_reader):
    root, manifest = prepared_reader
    payload = model_reader.read_native_field(root, manifest.model_id, "so").model_dump()
    payload["valid_mask"] = (False,) * 16
    with pytest.raises(ValueError):
        NativeFieldSnapshot.model_validate(payload)


def test_postread_change_rejected(isolated_reader, monkeypatch):
    root, manifest = isolated_reader
    original = model_reader._read_fields

    def change(*args):
        values = original(*args)
        target = root / "data/models" / manifest.model_id / "source_metadata.json"
        target.write_bytes(target.read_bytes() + b" ")
        return values

    monkeypatch.setattr(model_reader, "_read_fields", change)
    with pytest.raises(ProductError, match="model_input_changed"):
        model_reader.read_native_field(root, manifest.model_id, "so")


@pytest.mark.parametrize(
    "variable", ["time", "depth", "latitude", "longitude", "so", "thetao"]
)
@pytest.mark.parametrize(
    "attribute", ["bounds", "formula_terms", "coordinates", "grid_mapping"]
)
def test_unexpected_scientific_semantics_rejected_even_when_rehashed(
    isolated_reader, variable, attribute
):
    root, manifest = isolated_reader
    path = root / "data/models" / manifest.model_id / "fields.nc"
    with netCDF4.Dataset(path, "a") as ds:
        ds[variable].setncattr(attribute, "unsupported_synthetic_metadata")
    refresh(root, manifest, "fields.nc")
    with pytest.raises(ProductError) as error:
        model_reader.read_native_field(root, manifest.model_id, "so")
    assert error.value.code in {"model_axes_mismatch", "model_field_mismatch"}
