"""Prepared-product reads with tiny labelled files; no raw ocean dependency."""

import json
from datetime import UTC, datetime
from pathlib import Path

import netCDF4
import numpy as np
import pytest

from backend.app.schemas.products import (
    PerformanceLimits,
    PreparationRequest,
    ProductManifest,
    Region,
    VariableInfo,
)
from backend.app.storage import products
from backend.app.storage.product_common import ProductError, describe_file


@pytest.fixture
def prepared_store(tmp_path: Path) -> tuple[products.ProductStore, ProductManifest]:
    root = tmp_path
    (root / "config").mkdir()
    limits = PerformanceLimits()
    (root / "config/performance.yaml").write_text(limits.model_dump_json())
    (root / "config/data_sources.yaml").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "datasets": [
                    {
                        "source_id": "incois_bio_roms",
                        "dataset_id": "incois_bio_roms_v2",
                        "title": "SYNTHETIC product test",
                        "role": "model",
                        "access_method": "local_netcdf",
                        "origin_url": "https://example.org/synthetic",
                        "version": "fixture",
                        "local_path": "data/raw/absent.nc",
                    },
                    {
                        "source_id": "argo",
                        "dataset_id": "argo_gdac",
                        "title": "Official Argo",
                        "role": "observation",
                        "access_method": "argopy",
                        "origin_url": "ftp://ftp.ifremer.fr/ifremer/argo",
                    },
                ],
            }
        )
    )
    product_id = "p_fixture"
    scientific = root / f"data/processed/{product_id}/fields.nc"
    preview = root / f"data/cache/{product_id}/preview.nc"
    lat = [-1.0, 0.0, 1.0, 2.0]
    lon = [40.0, 41.0, 42.0, 43.0, 44.0]
    values = np.arange(60, dtype=float).reshape(3, 4, 5)
    values[0, 0, 0] = np.nan
    for path, stride in ((scientific, 1), (preview, 2)):
        path.parent.mkdir(parents=True)
        with netCDF4.Dataset(path, "w") as dataset:
            dataset.title = "SYNTHETIC; not source ocean data"
            for name, coords in (
                ("LAT", lat[::stride]),
                ("LON", lon[::stride]),
                ("TIME", [0, 1, 2]),
            ):
                dataset.createDimension(name, len(coords))
                axis = dataset.createVariable(name, "f8", (name,))
                axis[:] = coords
                if name == "TIME":
                    axis.units = "days since 2020-01-01"
                    axis.calendar = "proleptic_gregorian"
            field = dataset.createVariable(
                "SST", "f8", ("TIME", "LAT", "LON"), fill_value=np.nan
            )
            field.units = "deg C"
            field[:] = values[:, ::stride, ::stride]
    manifest = ProductManifest(
        product_id=product_id,
        source_id="incois_bio_roms",
        dataset_id="incois_bio_roms_v2",
        source_version="fixture",
        origin_url="https://example.org/synthetic",
        input_md5="0" * 32,
        input_size_bytes=100,
        input_modified_ns=1,
        created_at=datetime.now(UTC),
        selection=PreparationRequest(
            variables=["SST"],
            region=Region(west=40, east=44, south=-1, north=2),
            start_date="2020-01-01",
            end_date="2020-01-03",
        ),
        data_mode="synthetic",
        latitude=lat,
        longitude=lon,
        times=[f"2020-01-0{i}T00:00:00Z" for i in (1, 2, 3)],
        time_units="days since 2020-01-01",
        calendar="proleptic_gregorian",
        preview_stride=2,
        variables={
            "SST": VariableInfo(
                source_name="SST",
                units="deg C",
                long_name="Synthetic surface temperature",
                source_dtype="float64",
            )
        },
        scientific_file=describe_file(scientific, limits.max_product_file_bytes),
        preview_file=describe_file(preview, limits.max_product_file_bytes),
    )
    (scientific.parent / "manifest.json").write_text(manifest.model_dump_json())
    return products.ProductStore(root), manifest


def test_catalogue_preserves_unimplemented_source_and_synthetic_label(prepared_store):
    store, _ = prepared_store
    result = store.catalogue()
    assert result["datasets"][0]["status"] == "ready"
    assert result["datasets"][1]["status"] == "not_prepared"
    assert result["products"][0]["data_mode"] == "synthetic"
    assert "raw/absent" not in json.dumps(result)


def test_public_metadata_does_not_expose_private_file_records(prepared_store):
    store, manifest = prepared_store
    result = store.metadata(manifest.product_id)
    assert result["capabilities"]["volume"] is False
    assert result["ready_scope"] == "prepared_surface_selection"
    assert "scientific_file" not in result
    assert "preview_file" not in result
    assert "input_modified_ns" not in result


def test_preview_frame_is_explicit_and_preserves_missing(prepared_store):
    store, manifest = prepared_store
    result = store.frame(manifest.product_id, "SST", 0)
    assert result["display_only"] is True
    assert result["shape"] == [2, 3]
    assert result["values"] == [[None, 2.0, 4.0], [10.0, 12.0, 14.0]]
    assert result["missing_count"] == 1
    assert result["time"] == manifest.times[0]
    json.dumps(result, allow_nan=False)


def test_scientific_frame_subset_preserves_native_samples(prepared_store):
    store, manifest = prepared_store
    result = store.frame(
        manifest.product_id,
        "SST",
        1,
        "scientific",
        Region(west=40, east=42, south=0, north=1),
    )
    assert result["display_only"] is False
    assert result["shape"] == [2, 3]
    assert result["values"] == [[25.0, 26.0, 27.0], [30.0, 31.0, 32.0]]


def test_timeseries_does_not_search_for_wet_neighbour(prepared_store):
    store, manifest = prepared_store
    result = store.timeseries(manifest.product_id, "SST", 40, -1)
    assert result["values"] == [None, 20.0, 40.0]
    assert result["distance_m"] == 0
    assert result["comparison_result"] is False
    assert result["display_only"] is False


@pytest.mark.parametrize(
    "point", [(50, 0), (40, -2), (float("nan"), 0), (40, float("inf"))]
)
def test_timeseries_outside_support_rejected(prepared_store, point):
    store, manifest = prepared_store
    with pytest.raises(ProductError, match="outside"):
        store.timeseries(manifest.product_id, "SST", *point)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"variable": "UNKNOWN", "time_index": 0},
        {"variable": "SST", "time_index": 3},
        {"variable": "SST", "time_index": -1},
        {"variable": "SST", "time_index": 0, "quality": "invented"},
    ],
)
def test_invalid_frame_selection(prepared_store, kwargs):
    store, manifest = prepared_store
    with pytest.raises(ProductError):
        store.frame(manifest.product_id, **kwargs)


def test_cell_limit_before_scientific_open(prepared_store, monkeypatch):
    store, manifest = prepared_store
    limits_path = store.root / "config/performance.yaml"
    limits_path.write_text(
        PerformanceLimits(max_scientific_frame_cells=5).model_dump_json()
    )

    def denied(*args, **kwargs):
        raise AssertionError("Must reject before NetCDF open")

    monkeypatch.setattr(netCDF4, "Dataset", denied)
    with pytest.raises(ProductError) as error:
        store.frame(manifest.product_id, "SST", 0, "scientific")
    assert error.value.http_status == 413


def test_readiness_uses_no_netcdf_and_rejects_synthetic(prepared_store, monkeypatch):
    store, manifest = prepared_store

    def denied(*args, **kwargs):
        raise AssertionError("Readiness cannot inspect raw/prepared NetCDF contents")

    monkeypatch.setattr(netCDF4, "Dataset", denied)
    assert store.readiness([])["status"] == "not_ready"
    assert (
        store.readiness([manifest.product_id])["checks"][0]["reason_code"]
        == "synthetic_product"
    )
    # Deliberately label this fixture as real ONLY to exercise manifest policy.
    path = store.root / f"data/processed/{manifest.product_id}/manifest.json"
    path.write_text(manifest.model_copy(update={"data_mode": "real"}).model_dump_json())
    assert store.readiness([manifest.product_id])["status"] == "ready"
    assert store.readiness([manifest.product_id, "missing"])["status"] == "not_ready"


def test_changed_file_rejected(prepared_store):
    store, manifest = prepared_store
    path = store.root / f"data/processed/{manifest.product_id}/fields.nc"
    with path.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ProductError) as error:
        store.metadata(manifest.product_id)
    assert error.value.code == "product_changed"


@pytest.mark.parametrize(
    "value", ["../outside", "C:/private", "p_fixture/../../raw", "a\n"]
)
def test_unsafe_product_id_rejected(prepared_store, value):
    store, _ = prepared_store
    with pytest.raises(ProductError):
        store.metadata(value)


def test_missing_corrupt_oversized_manifest(prepared_store):
    store, manifest = prepared_store
    with pytest.raises(ProductError) as error:
        store.metadata("missing")
    assert error.value.http_status == 404
    path = store.root / f"data/processed/{manifest.product_id}/manifest.json"
    for content in ("{broken", " " * (524288 + 1), '{"private_path":"do not echo"}'):
        path.write_text(content)
        with pytest.raises(ProductError) as error:
            store.metadata(manifest.product_id)
        assert "private_path" not in error.value.message


def test_busy_scientific_read_is_bounded(prepared_store):
    store, manifest = prepared_store
    with products._scientific_access():
        with pytest.raises(ProductError) as error:
            store.frame(manifest.product_id, "SST", 0)
        assert error.value.code == "busy"


def test_changed_header_not_silently_trusted_even_after_stat_update(prepared_store):
    store, manifest = prepared_store
    path = store.root / f"data/processed/{manifest.product_id}/fields.nc"
    with netCDF4.Dataset(path, "a") as dataset:
        dataset["SST"].units = "unexpected_units"
    updated = manifest.model_copy(
        update={"scientific_file": describe_file(path, 134217728)}
    )
    (path.parent / "manifest.json").write_text(updated.model_dump_json())
    with pytest.raises(ProductError, match="units"):
        store.timeseries(manifest.product_id, "SST", 40, -1)


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", [-2, 0, 1, 2]),
        ("longitude", [40, 41, 42, 43, 45]),
        (
            "times",
            ["2019-12-31T00:00:00Z", "2020-01-02T00:00:00Z", "2020-01-03T00:00:00Z"],
        ),
    ],
)
def test_manifest_cannot_relabel_out_of_selection_samples(prepared_store, field, value):
    store, manifest = prepared_store
    payload = manifest.model_dump(mode="json")
    payload[field] = value
    path = store.root / f"data/processed/{manifest.product_id}/manifest.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ProductError) as error:
        store.metadata(manifest.product_id)
    assert error.value.code == "invalid_product"


def test_real_store_through_http_contract(prepared_store):
    from fastapi.testclient import TestClient

    from backend.app.config import Settings
    from backend.app.main import create_app

    store, manifest = prepared_store
    app = create_app(Settings(project_root=store.root))
    with TestClient(app) as client:
        prefix = f"/api/v1/products/{manifest.product_id}"
        for url in (
            "/health",
            "/api/v1/datasets",
            prefix,
            f"{prefix}/frame?variable=SST&time_index=0",
            f"{prefix}/timeseries?variable=SST&longitude=40&latitude=-1",
        ):
            response = client.get(url)
            assert response.status_code == 200, response.text
        assert client.get("/ready").status_code == 503


def test_readiness_rejects_stat_accessible_but_unreadable_product(
    prepared_store, monkeypatch
):
    store, manifest = prepared_store
    path = store.root / f"data/processed/{manifest.product_id}/manifest.json"
    path.write_text(manifest.model_copy(update={"data_mode": "real"}).model_dump_json())
    original = Path.open

    def denied(target, *args, **kwargs):
        if target.name == "fields.nc":
            raise PermissionError("private access reason")
        return original(target, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    result = store.readiness([manifest.product_id])
    assert result["status"] == "not_ready"
    assert result["checks"][0]["reason_code"] == "product_unavailable"
    assert "private access" not in json.dumps(result)
