"""Public source-stage inventory uses manifests, never provider requests."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.schemas.acquisition import AcquisitionManifest, AcquisitionRequest


def test_empty_acquisition_inventory_needs_no_registry_or_data(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(project_root=tmp_path))) as client:
        response = client.get("/api/v1/acquisitions")
        assert response.status_code == 200
        assert response.json() == {
            "schema_version": 1,
            "scope": "locally_available_acquisitions_not_live_access",
            "acquisitions": [],
        }
        assert response.headers["cache-control"] == "no-store"
        assert client.post("/api/v1/acquisitions").status_code == 405
        assert client.get("/health").status_code == 200


def test_acquisition_api_excludes_operator_paths(tmp_path: Path, monkeypatch) -> None:
    from backend.app.ingestion import acquisition

    manifest = AcquisitionManifest(
        acquisition_id="a_" + "1" * 24,
        dataset_id="argo_gdac",
        source_id="argo",
        origin_url="ftp://ftp.ifremer.fr/ifremer/argo",
        source_version=None,
        request=AcquisitionRequest(
            provider="local",
            dataset_id="argo_gdac",
            local_path="data/raw/private-input.nc",
        ),
        input_file={"size_bytes": 12, "modified_ns": 42, "sha256": "a" * 64},
        original_filename="private-input.nc",
        created_at=datetime.now(UTC),
        retrieved_at=None,
        data_mode="synthetic",
        client="local operator",
        client_version="test",
        client_processing="No provider download; synthetic fixture.",
        transport="local",
    )
    monkeypatch.setattr(acquisition, "list_acquisitions", lambda root: [manifest])
    with TestClient(create_app(Settings(project_root=tmp_path))) as client:
        response = client.get("/api/v1/acquisitions")
        assert response.status_code == 200
        item = response.json()["acquisitions"][0]
        assert item["status"] == "acquired_not_prepared"
        assert item["comparison_ready"] is False
        assert item["data_mode"] == "synthetic"
        assert item["input_sha256"] == "a" * 64
        assert item["retrieved_at"] is None
        for private in (
            "private-input",
            "modified_ns",
            "local_path",
            "original_filename",
        ):
            assert private not in response.text


def test_acquisition_inventory_io_errors_are_safe(tmp_path: Path, monkeypatch) -> None:
    from backend.app.ingestion import acquisition

    def broken(root):
        raise OSError("private-password-and-path")

    monkeypatch.setattr(acquisition, "list_acquisitions", broken)
    with TestClient(create_app(Settings(project_root=tmp_path))) as client:
        response = client.get("/api/v1/acquisitions")
        assert response.status_code == 503
        assert "private-password" not in response.text
        assert response.json()["error"]["code"] == "acquisitions_unavailable"
