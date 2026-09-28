"""Liveness contract and developer-route tests without scientific datasets."""

import builtins
import io
import os
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app

EXPECTED_HEALTH = {"status": "ok", "service": "Project Ocean Backend"}


def test_health_response_is_exact_and_not_cacheable() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_HEALTH
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"


def test_developer_docs_describe_only_implemented_routes() -> None:
    with TestClient(create_app()) as client:
        docs_response = client.get("/docs")
        schema_response = client.get("/openapi.json")
        redoc_response = client.get("/redoc")

    assert docs_response.status_code == 200
    assert docs_response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in docs_response.text
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema["info"]["title"] == "Project Ocean Backend"
    assert schema["info"]["version"] == "0.1.0"
    assert set(schema["paths"]) == {
        "/health",
        "/ready",
        "/api/v1/datasets",
        "/api/v1/products/{product_id}",
        "/api/v1/products/{product_id}/frame",
        "/api/v1/products/{product_id}/timeseries",
        "/api/v1/observations",
        "/api/v1/observations/{collection_id}",
        "/api/v1/observations/{collection_id}/samples",
        "/api/v1/acquisitions",
        "/api/v1/comparisons",
        "/api/v1/comparisons/{comparison_id}",
        "/api/v1/comparisons/{comparison_id}/samples",
    }
    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert health_schema["properties"]["status"]["const"] == "ok"
    assert health_schema["properties"]["service"]["const"] == "Project Ocean Backend"
    assert health_schema["additionalProperties"] is False
    response_schema = schema["paths"]["/health"]["get"]["responses"]["200"]
    assert response_schema["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert redoc_response.status_code == 404


def test_disabled_developer_docs_do_not_disable_health() -> None:
    application = create_app(Settings(docs_enabled=False))
    assert application.debug is False
    with TestClient(application) as client:
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == EXPECTED_HEALTH
        for route in ("/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"):
            assert client.get(route).status_code == 404


@pytest.mark.parametrize("docs_enabled", [True, False])
def test_unimplemented_singular_comparison_alias_stays_absent(
    docs_enabled: bool,
) -> None:
    with TestClient(create_app(Settings(docs_enabled=docs_enabled))) as client:
        assert client.get("/api/v1/comparison").status_code == 404


def test_health_does_not_accept_mutating_requests() -> None:
    with TestClient(create_app()) as client:
        assert client.post("/health").status_code == 405


def test_health_needs_no_credentials_network_or_file_reads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for variable in (
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.chdir(tmp_path)

    def forbidden_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("Health must not perform network or filesystem I/O")

    with TestClient(create_app()) as client:
        # Start the event loop before guarding sockets: Windows may use a
        # loopback socket pair for its internal wake-up mechanism.
        with monkeypatch.context() as guarded:
            for module, attribute in (
                (builtins, "open"),
                (io, "open"),
                (os, "open"),
                (os, "listdir"),
                (os, "scandir"),
                (os, "stat"),
                (os, "lstat"),
                (socket, "create_connection"),
                (socket, "getaddrinfo"),
                (socket.socket, "connect"),
                (socket.socket, "connect_ex"),
                (socket.socket, "sendto"),
            ):
                guarded.setattr(module, attribute, forbidden_io)
            response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_HEALTH
    assert list(tmp_path.iterdir()) == []
