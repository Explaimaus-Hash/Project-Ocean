"""Storage/wire contracts use tiny synthetic objects, never downloaded data."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.schemas.observation_api import ObservationPageResponse
from backend.app.schemas.observations import ObservationCollection
from backend.app.storage.observations import ObservationStore
from backend.app.storage.product_common import ProductError

COLLECTION_ID = "o_" + "1" * 24
PROFILE_ID = "r_" + "2" * 24


@pytest.fixture
def collection() -> ObservationCollection:
    variables = ("PRES", "TEMP", "PSAL")
    samples = []
    for index in range(3):
        values = {}
        for variable, value in zip(variables, (float(index), 20.0, 35.0), strict=True):
            values[variable] = {
                "raw": value,
                "raw_qc": "1",
                "adjusted": None,
                "adjusted_qc": None,
                "adjusted_error": None,
                "data_mode": "R",
                "selected_kind": "raw",
                "selected_source_name": variable,
                "selected_value": value,
                "selected_qc": "1",
                "qc_eligible": True,
                "exclusions": [],
            }
        samples.append(
            {
                "sample_id": "s_" + f"{index:024x}",
                "source_sample_index": index,
                "source_profile_index": 0,
                "source_level_index": index,
                "profile_id": PROFILE_ID,
                "profile_identity_status": "source_profile",
                "platform_id": "1234567",
                "cycle_number": 1,
                "direction": "A",
                "time": "2019-01-29T00:00:00Z",
                "longitude": 65.0,
                "latitude": 5.0,
                "source_longitude": 65.0,
                "pressure_dbar": float(index),
                "depth_m": None,
                "time_qc": "1",
                "position_qc": "1",
                "coordinate_qc_eligible": True,
                "values": values,
            }
        )
    return ObservationCollection.model_validate(
        {
            "collection_id": COLLECTION_ID,
            "source_id": "argo",
            "dataset_id": "argo_gdac",
            "source_filename": "private-fixture.nc",
            "input_file": {"size_bytes": 1, "modified_ns": 1, "sha256": "a" * 64},
            "data_mode": "synthetic",
            "client_processing": "local_operator_input_client_processing_unknown",
            "selection": {
                "region": {"west": 60, "east": 70, "south": 0, "north": 10},
                "start_date": "2019-01-01",
                "end_date": "2019-01-31",
                "pressure_min_dbar": 0,
                "pressure_max_dbar": 100,
                "variables": list(variables),
                "value_mode": "raw",
            },
            "layout": "argo_profiles",
            "source_time_name": "JULD",
            "source_time_units": "days since 1950-01-01",
            "source_time_calendar": "standard",
            "variables": {
                variable: {
                    "source_name": variable,
                    "units": units,
                    "raw_name": variable,
                    "adjusted_name": None,
                    "adjusted_error_name": None,
                    "qc_convention": "argo_reference_table_2",
                }
                for variable, units in zip(
                    variables, ("dbar", "degree_Celsius", "psu"), strict=True
                )
            },
            "samples": samples,
            "counts": {
                "input_samples": 3,
                "selected_samples": 3,
                "outside_selection": 0,
                "missing_filter_coordinates": 0,
                "coordinate_qc_rejected": 0,
                "variable_qc_rejected": {key: 0 for key in variables},
            },
            "capabilities": {"profiles": True},
            "warnings": [],
        }
    )


@pytest.fixture
def prepared(tmp_path: Path, collection: ObservationCollection) -> ObservationStore:
    store = ObservationStore(tmp_path)
    store.publish(collection)
    return store


def test_public_metadata_omits_private_identity(prepared: ObservationStore) -> None:
    metadata = prepared.metadata(COLLECTION_ID)
    assert metadata["input_sha256"] == "a" * 64
    assert not {"input_file", "source_filename", "samples"} & set(metadata)
    assert metadata["data_mode"] == "synthetic"
    assert metadata["capabilities"]["comparison_ready"] is False
    assert prepared.collection(COLLECTION_ID).source_filename == "private-fixture.nc"


def test_idempotent_publication_preserves_bytes(
    prepared: ObservationStore, collection: ObservationCollection
) -> None:
    before = prepared._path(COLLECTION_ID, "collection.json").stat()
    prepared.publish(collection)
    after = prepared._path(COLLECTION_ID, "collection.json").stat()
    assert (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size)


def test_conflicting_publication_does_not_replace(
    prepared: ObservationStore, collection: ObservationCollection
) -> None:
    changed = collection.model_copy(update={"warnings": ["different_provenance"]})
    with pytest.raises(ProductError, match="differs"):
        prepared.publish(changed)
    assert prepared.collection(COLLECTION_ID).warnings == []


def test_page_and_profile_filter(prepared: ObservationStore) -> None:
    first = prepared.samples(COLLECTION_ID, limit=2)
    assert len(first["samples"]) == 2
    assert first["next_offset"] == 2
    assert first["comparison_result"] is False
    second = prepared.samples(COLLECTION_ID, offset=2, limit=2, profile_id=PROFILE_ID)
    assert second["next_offset"] is None
    assert len(second["samples"]) == 1
    assert prepared.samples(COLLECTION_ID, offset=5)["samples"] == []
    with pytest.raises(ProductError) as caught:
        prepared.samples(COLLECTION_ID, profile_id="r_" + "f" * 24)
    assert caught.value.http_status == 404


@pytest.mark.parametrize(
    "options",
    [
        {"offset": -1},
        {"offset": 5001},
        {"limit": 0},
        {"limit": 501},
        {"profile_id": "../private"},
    ],
)
def test_storage_rejects_invalid_pages(
    prepared: ObservationStore, options: dict
) -> None:
    with pytest.raises(ProductError) as caught:
        prepared.samples(COLLECTION_ID, **options)
    assert caught.value.http_status == 422


def test_snapshot_hash_detects_same_stat_mutation(prepared: ObservationStore) -> None:
    import os

    path = prepared._path(COLLECTION_ID, "collection.json")
    before = path.stat()
    content = path.read_bytes().replace(b"private-fixture", b"changed-fixture")
    path.write_bytes(content)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(ProductError) as caught:
        prepared.collection(COLLECTION_ID)
    assert caught.value.code == "observations_changed"


def test_missing_or_changed_collection_is_not_ready(prepared: ObservationStore) -> None:
    prepared._path(COLLECTION_ID, "collection.json").unlink()
    entry = prepared.catalogue()["collections"][0]
    assert entry["status"] == "not_prepared"


def test_api_pages_and_empty_catalogue(
    tmp_path: Path, prepared: ObservationStore
) -> None:
    with TestClient(create_app(Settings(project_root=tmp_path))) as client:
        catalogue = client.get("/api/v1/observations")
        assert catalogue.status_code == 200
        assert len(catalogue.json()["collections"]) == 1
        response = client.get(f"/api/v1/observations/{COLLECTION_ID}/samples?limit=2")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert len(response.json()["samples"]) == 2
        assert "private-fixture.nc" not in response.text
        metadata = client.get(f"/api/v1/observations/{COLLECTION_ID}")
        assert metadata.status_code == 200
        assert "modified_ns" not in metadata.text
        assert client.get("/health").status_code == 200
    with TestClient(create_app(Settings(project_root=tmp_path / "empty"))) as client:
        assert client.get("/api/v1/observations").json()["collections"] == []
        assert client.get(f"/api/v1/observations/{COLLECTION_ID}").status_code == 404


@pytest.mark.parametrize(
    "query",
    [
        "offset=-1",
        "offset=5001",
        "limit=501",
        "limit=0",
        "profile_id=secret-value",
        "limit=nan",
    ],
)
def test_bad_http_pages_are_sanitized(tmp_path: Path, query: str) -> None:
    with TestClient(create_app(Settings(project_root=tmp_path))) as client:
        response = client.get(f"/api/v1/observations/{COLLECTION_ID}/samples?{query}")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        assert "secret-value" not in response.text


def test_api_never_needs_raw_inputs(tmp_path: Path, prepared: ObservationStore) -> None:
    assert not (tmp_path / "data" / "raw").exists()
    assert prepared.samples(COLLECTION_ID)["total"] == 3


def test_page_contract_rejects_wrong_counts(prepared: ObservationStore) -> None:
    page = prepared.samples(COLLECTION_ID)
    page["total"] = 4
    with pytest.raises(ValidationError):
        ObservationPageResponse.model_validate(page)


def test_private_invalid_snapshot_fails_validation(prepared: ObservationStore) -> None:
    path = prepared._path(COLLECTION_ID, "collection.json")
    value = json.loads(path.read_bytes())
    value["samples"][0]["longitude"] = 800
    content = json.dumps(value).encode()
    path.write_bytes(content)
    manifest_path = prepared._path(COLLECTION_ID, "manifest.json")
    manifest = json.loads(manifest_path.read_bytes())
    manifest["collection_file"] = {
        "size_bytes": len(content),
        "modified_ns": path.stat().st_mtime_ns,
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ProductError) as caught:
        prepared.collection(COLLECTION_ID)
    assert caught.value.code == "invalid_observations"
