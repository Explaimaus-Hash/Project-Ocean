"""Prepared-product HTTP contracts with an isolated fake storage service."""

import builtins
import io
import os
import socket
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.api.products import get_product_store
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.schemas.product_api import (
    CatalogueResponse,
    FrameResponse,
    MetadataResponse,
    ReadinessResponse,
    TimeseriesResponse,
)
from backend.app.schemas.products import Region
from backend.app.storage.product_common import ProductError

VARIABLE_INFO = {
    "source_name": "SST",
    "units": "degC",
    "long_name": "Synthetic temperature",
    "standard_name": "",
    "cell_methods": "not_declared",
    "source_dtype": "float32",
    "scientific_definition": "source_definition_not_harmonized",
}
CAPABILITIES = {
    "surface": True,
    "timeseries": True,
    "depth_profiles": False,
    "volume": False,
    "currents": False,
    "comparison_ready": False,
}
TIMES = ["1980-01-15T00:00:00Z", "1980-02-15T00:00:00Z"]


def scientific_base() -> dict:
    return {
        "schema_version": 1,
        "product_id": "ocean_start",
        "dataset_id": "example",
        "source_id": "example_source",
        "source_version": "v2",
        "input_md5": "0" * 32,
        "processing_version": "surface_1",
        "data_mode": "synthetic",
        "variable": "SST",
        "units": "degC",
        "variable_metadata": deepcopy(VARIABLE_INFO),
        "qc_policy": "source_mask_and_nonfinite_only",
        "temporal_support": "source_timestamps_no_inferred_bounds",
        "vertical_reference": "source_surface_product_no_numeric_depth_assigned",
        "missing_value": None,
    }


class FakeStore:
    """Exercise routing independently of scientific libraries and the real download."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.error: ProductError | None = None
        self.ready = False
        self.payload_updates: dict = {}

    def result(self, name: str, *values: object) -> dict:
        self.calls.append((name, *values))
        if self.error is not None:
            raise self.error
        return {"product_id": "ocean_start", "data_mode": "synthetic"}

    def catalogue(self) -> dict:
        self.result("catalogue")
        return {
            "schema_version": 1,
            "datasets": [
                {
                    "source_id": "example_source",
                    "dataset_id": "example",
                    "title": "Synthetic example",
                    "role": "model",
                    "origin_url": "https://example.org/synthetic",
                    "status": "ready",
                    "reason_code": "prepared_selection_available",
                    "product_ids": ["ocean_start"],
                }
            ],
            "products": [
                {
                    "product_id": "ocean_start",
                    "dataset_id": "example",
                    "status": "ready",
                    "data_mode": "synthetic",
                    "variables": ["SST"],
                    "times": list(TIMES),
                    "capabilities": dict(CAPABILITIES),
                }
            ],
            **self.payload_updates,
        }

    def metadata(self, product_id: str) -> dict:
        self.result("metadata", product_id)
        return {
            "schema_version": 1,
            "processing_version": "surface_1",
            "product_id": "ocean_start",
            "source_id": "example_source",
            "dataset_id": "example",
            "source_version": "v2",
            "origin_url": "https://example.org/synthetic",
            "input_md5": "0" * 32,
            "input_size_bytes": 1024,
            "created_at": "2026-09-10T00:00:00Z",
            "data_mode": "synthetic",
            "selection": {
                "dataset_id": "example",
                "variables": ["SST"],
                "region": {"west": 40, "east": 80, "south": -10, "north": 10},
                "start_date": "1980-01-01",
                "end_date": "1980-02-29",
            },
            "variables": {"SST": deepcopy(VARIABLE_INFO)},
            "latitude": [0.0],
            "longitude": [60.0, 61.0],
            "times": list(TIMES),
            "time_units": "days since 1980-01-01",
            "calendar": "standard",
            "preview_stride": 1,
            "capabilities": dict(CAPABILITIES),
            "qc_policy": "source_mask_and_nonfinite_only",
            "temporal_support": "source_timestamps_no_inferred_bounds",
            "status": "ready",
            "ready_scope": "prepared_surface_selection",
            **self.payload_updates,
        }

    def frame(
        self,
        product_id: str,
        variable: str,
        time_index: int,
        quality: str = "preview",
        region: Region | None = None,
    ) -> dict:
        self.result("frame", product_id, variable, time_index, quality, region)
        return {
            **scientific_base(),
            "quality": quality,
            "display_only": quality == "preview",
            "sampling": "strided_source_cells_no_interpolation"
            if quality == "preview"
            else "scientific_source_cells",
            "stride": 1,
            "shape": [1, 2],
            "time_index": time_index,
            "time": TIMES[time_index],
            "latitude": [0.0],
            "longitude": [60.0, 61.0],
            "values": [[None, 1.25]],
            "dimensions": ["latitude", "longitude"],
            "valid_count": 1,
            "missing_count": 1,
            "requested_region": region.model_dump() if region else None,
            **self.payload_updates,
        }

    def timeseries(
        self, product_id: str, variable: str, longitude: float, latitude: float
    ) -> dict:
        self.result("timeseries", product_id, variable, longitude, latitude)
        return {
            **scientific_base(),
            "times": list(TIMES),
            "values": [None, 1.25],
            "requested_point": {"longitude": longitude, "latitude": latitude},
            "sample_point": {"longitude": longitude, "latitude": latitude},
            "sample_indices": {"latitude": 0, "longitude": 0},
            "distance_m": 0.0,
            "sampling": "nearest_axis_grid_cell_no_wet_cell_search",
            "display_only": False,
            "comparison_result": False,
            **self.payload_updates,
        }

    def readiness(self, required_product_ids: list[str]) -> dict:
        self.result("readiness", required_product_ids)
        return {
            "status": "ready" if self.ready else "not_ready",
            "checks": [
                {
                    "product_id": product_id,
                    "status": "ready" if self.ready else "not_ready",
                    "reason_code": "verified_local_product"
                    if self.ready
                    else "not_prepared",
                }
                for product_id in required_product_ids
            ],
        }


@pytest.fixture
def api(tmp_path: Path):
    application = create_app(
        Settings(project_root=tmp_path, required_product_ids=["ocean_start"])
    )
    store = FakeStore()
    application.dependency_overrides[get_product_store] = lambda: store
    with TestClient(application) as client:
        yield client, store


@pytest.mark.parametrize(
    "url, method",
    [
        ("/api/v1/datasets", "catalogue"),
        ("/api/v1/products/ocean_start", "metadata"),
        ("/api/v1/products/ocean_start/frame?variable=SST&time_index=0", "frame"),
        (
            "/api/v1/products/ocean_start/timeseries?variable=SST&longitude=60&latitude=0",
            "timeseries",
        ),
    ],
)
def test_product_routes_are_versioned_and_read_only(api, url: str, method: str) -> None:
    client, store = api
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["schema_version"] == 1
    assert response.headers["cache-control"] == "no-store"
    assert store.calls[-1][0] == method
    assert client.post(url).status_code == 405


def test_frame_defaults_to_preview_and_preserves_null(api) -> None:
    client, store = api
    response = client.get(
        "/api/v1/products/ocean_start/frame?variable=SST&time_index=0"
    )
    assert response.json()["values"] == [[None, 1.25]]
    assert store.calls[-1] == ("frame", "ocean_start", "SST", 0, "preview", None)


def test_frame_accepts_explicit_scientific_quality_and_full_region(api) -> None:
    client, store = api
    response = client.get(
        "/api/v1/products/ocean_start/frame",
        params={
            "variable": "SST",
            "time_index": 1,
            "quality": "scientific",
            "west": 40,
            "east": 80,
            "south": -10,
            "north": 10,
        },
    )
    assert response.status_code == 200
    assert store.calls[-1] == (
        "frame",
        "ocean_start",
        "SST",
        1,
        "scientific",
        Region(west=40, east=80, south=-10, north=10),
    )


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"variable": "SST"},
        {"variable": "SST", "time_index": -1},
        {"variable": "SST", "time_index": "nan"},
        {"variable": "../secret", "time_index": 0},
        {"variable": "SST", "time_index": 0, "quality": "ultra"},
        {"variable": "SST", "time_index": 0, "west": 30},
        {
            "variable": "SST",
            "time_index": 0,
            "west": 80,
            "east": 40,
            "south": -10,
            "north": 10,
        },
        {
            "variable": "SST",
            "time_index": 0,
            "west": 40,
            "east": 80,
            "south": 10,
            "north": 10,
        },
        {
            "variable": "SST",
            "time_index": 0,
            "west": "nan",
            "east": 80,
            "south": -10,
            "north": 10,
        },
        {
            "variable": "SST",
            "time_index": 0,
            "west": 40,
            "east": "inf",
            "south": -10,
            "north": 10,
        },
        {
            "variable": "SST",
            "time_index": 0,
            "west": -181,
            "east": 80,
            "south": -10,
            "north": 10,
        },
    ],
)
def test_frame_rejects_invalid_requests_before_storage(api, parameters: dict) -> None:
    client, store = api
    response = client.get("/api/v1/products/ocean_start/frame", params=parameters)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.headers["cache-control"] == "no-store"
    assert "../secret" not in response.text
    assert store.calls == []


@pytest.mark.parametrize(
    "longitude, latitude",
    [(180, 0), (-181, 0), (0, 91), (0, -91), ("nan", 0), (0, "inf")],
)
def test_timeseries_rejects_nonfinite_or_out_of_range_points(
    api, longitude: object, latitude: object
) -> None:
    client, store = api
    response = client.get(
        "/api/v1/products/ocean_start/timeseries",
        params={"variable": "SST", "longitude": longitude, "latitude": latitude},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert store.calls == []


@pytest.mark.parametrize("product_id", ["Bad", "bad-id", "x" * 97, "_hidden"])
def test_invalid_product_identifiers_never_reach_storage(api, product_id: str) -> None:
    client, store = api
    response = client.get(f"/api/v1/products/{product_id}")
    assert response.status_code == 422
    assert store.calls == []


@pytest.mark.parametrize(
    "code, status",
    [("unknown_product", 404), ("not_prepared", 409), ("response_limit", 413)],
)
def test_product_errors_preserve_safe_code_and_status(
    api, code: str, status: int
) -> None:
    client, store = api
    store.error = ProductError(code, "A safe public explanation.", status)
    response = client.get("/api/v1/products/ocean_start")
    assert response.status_code == status
    assert response.json() == {
        "schema_version": 1,
        "error": {"code": code, "message": "A safe public explanation."},
    }
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("is_ready, expected_status", [(True, 200), (False, 503)])
def test_readiness_uses_only_explicit_required_products(
    api, is_ready: bool, expected_status: int
) -> None:
    client, store = api
    store.ready = is_ready
    response = client.get("/ready")
    assert response.status_code == expected_status
    assert response.json()["status"] == ("ready" if is_ready else "not_ready")
    assert store.calls == [("readiness", ["ocean_start"])]
    assert response.headers["cache-control"] == "no-store"


def test_readiness_and_science_routes_remain_when_docs_are_disabled(
    tmp_path: Path,
) -> None:
    application = create_app(Settings(project_root=tmp_path, docs_enabled=False))
    store = FakeStore()
    application.state.product_store = store
    with TestClient(application) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/ready").status_code == 503
        assert client.get("/api/v1/datasets").status_code == 200
        assert client.get("/health").status_code == 200
    assert store.calls[0] == ("readiness", [])


def test_app_factory_and_health_never_touch_files_or_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Resolve the temporary path and instantiate settings before blocking I/O;
    # the factory still must not stat, open, scan, or prepare its configured root.
    settings = Settings(project_root=tmp_path, required_product_ids=["ocean_start"])

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Construction/liveness must not perform data I/O")

    with monkeypatch.context() as guarded:
        for module, attribute in (
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (os, "stat"),
            (os, "lstat"),
            (os, "listdir"),
            (os, "scandir"),
            (socket, "create_connection"),
            (socket, "getaddrinfo"),
        ):
            guarded.setattr(module, attribute, forbidden)
        application = create_app(settings)

    # Windows event-loop setup can need a loopback wakeup socket, so guard only
    # the health request after TestClient has started.
    with TestClient(application) as client, monkeypatch.context() as guarded:
        for module, attribute in (
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (os, "stat"),
            (os, "lstat"),
            (os, "listdir"),
            (os, "scandir"),
            (socket, "create_connection"),
            (socket, "getaddrinfo"),
            (socket.socket, "connect"),
            (socket.socket, "connect_ex"),
        ):
            guarded.setattr(module, attribute, forbidden)
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Project Ocean Backend"}


def test_openapi_documents_typed_success_and_error_contracts(api) -> None:
    client, _ = api
    schema = client.get("/openapi.json").json()
    for route, model in (
        ("/api/v1/datasets", "CatalogueResponse"),
        ("/api/v1/products/{product_id}", "MetadataResponse"),
        ("/api/v1/products/{product_id}/frame", "FrameResponse"),
        ("/api/v1/products/{product_id}/timeseries", "TimeseriesResponse"),
        ("/ready", "ReadinessResponse"),
    ):
        responses = schema["paths"][route]["get"]["responses"]
        assert responses["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{model}"
        }
        assert responses["422"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
        assert schema["components"]["schemas"][model]["additionalProperties"] is False
    ready_error = schema["paths"]["/ready"]["get"]["responses"]["503"]
    assert ready_error["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadinessResponse"
    }
    metadata = schema["components"]["schemas"]["MetadataResponse"]["properties"]
    assert not {"scientific_file", "preview_file", "input_modified_ns"} & set(metadata)


@pytest.mark.parametrize(
    "updates",
    [
        {"shape": [2, 1]},
        {"longitude": [61.0, 60.0]},
        {"values": [[float("nan"), 1.25]]},
        {"values": [[None]]},
        {"valid_count": 2},
        {"display_only": False},
        {"sampling": "scientific_source_cells"},
        {"time": "1980-01-15T00:00:00"},
        {"units": "wrong"},
        {"schema_version": 2},
        {"unexpected_private_path": "C:/private/secret.nc"},
    ],
)
def test_bad_store_frame_is_rejected_without_leaking_details(
    api, updates: dict
) -> None:
    client, store = api
    store.payload_updates = updates
    response = client.get(
        "/api/v1/products/ocean_start/frame?variable=SST&time_index=0"
    )
    assert response.status_code == 500
    assert response.json() == {
        "schema_version": 1,
        "error": {
            "code": "invalid_response",
            "message": "Prepared response failed contract validation.",
        },
    }
    assert "C:/private" not in response.text


def test_public_metadata_does_not_silently_accept_private_storage_fields(api) -> None:
    client, store = api
    store.payload_updates = {"scientific_file": {"path": "C:/private/data.nc"}}
    response = client.get("/api/v1/products/ocean_start")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "invalid_response"
    assert "private" not in response.text


@pytest.mark.parametrize(
    "quality, ny, nx", [("preview", 129, 128), ("scientific", 257, 256)]
)
def test_frame_contract_rejects_oversized_matrix_before_serializing(
    quality: str, ny: int, nx: int
) -> None:
    payload = FakeStore().frame("ocean_start", "SST", 0, quality)
    payload["values"] = [[1.0] * nx for _ in range(ny)]
    with pytest.raises(ValidationError, match="Frame cell limit exceeded"):
        FrameResponse.model_validate(payload)


@pytest.mark.parametrize(
    "updates",
    [
        {"times": [TIMES[0]]},
        {"times": list(reversed(TIMES))},
        {"values": [None, float("inf")]},
        {"distance_m": -1},
        {"sample_indices": {"latitude": -1, "longitude": 0}},
        {"sample_point": {"latitude": 91, "longitude": 60}},
        {"comparison_result": True},
        {"display_only": True},
        {"times": TIMES * 7, "values": [1.0] * 14},
    ],
)
def test_timeseries_contract_rejects_invalid_scientific_samples(updates: dict) -> None:
    payload = FakeStore().timeseries("ocean_start", "SST", 60.0, 0.0)
    payload.update(updates)
    with pytest.raises(ValidationError):
        TimeseriesResponse.model_validate(payload)


def test_metadata_contract_requires_matching_names_and_subset() -> None:
    payload = FakeStore().metadata("ocean_start")
    payload["variables"]["SST"]["source_name"] = "SSS"
    with pytest.raises(ValidationError, match="Variable definitions differ"):
        MetadataResponse.model_validate(payload)


def test_catalogue_contract_rejects_unknown_product_dataset() -> None:
    payload = FakeStore().catalogue()
    payload["products"][0]["dataset_id"] = "unregistered"
    with pytest.raises(ValidationError, match="not registered"):
        CatalogueResponse.model_validate(payload)


def test_catalogue_contract_accepts_explicit_unprepared_product() -> None:
    payload = FakeStore().catalogue()
    payload["products"].append(
        {
            "product_id": "not_finished",
            "status": "not_prepared",
            "reason_code": "not_prepared",
        }
    )
    assert (
        CatalogueResponse.model_validate(payload).products[-1].status == "not_prepared"
    )


def test_readiness_contract_rejects_ready_without_passing_checks() -> None:
    with pytest.raises(ValidationError):
        ReadinessResponse.model_validate(
            {"schema_version": 1, "status": "ready", "checks": []}
        )
