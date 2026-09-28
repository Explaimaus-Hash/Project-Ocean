"""Offline source-registry validation and project-local path boundaries."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.ingestion import registry as registry_module
from backend.app.ingestion.registry import (
    RegistryError,
    find_dataset,
    load_registry,
    resolve_local_input,
)
from backend.app.schemas.datasets import DatasetDefinition, SourceRegistry


def local_definition(**changes: object) -> DatasetDefinition:
    values = {
        "source_id": "incois_bio_roms",
        "dataset_id": "synthetic_fixture",
        "title": "Synthetic registry fixture, not source ocean data",
        "role": "model",
        "access_method": "local_netcdf",
        "origin_url": "https://example.org/synthetic",
        "local_path": "data/raw/fixtures/synthetic.nc",
    }
    return DatasetDefinition.model_validate(values | changes)


def test_shipped_registry_retains_every_source_without_claiming_inspection() -> None:
    registry = load_registry()
    assert registry.schema_version == 1
    assert len(registry.datasets) == 8
    assert {item.source_id for item in registry.datasets} == {
        "incois_bio_roms",
        "incois_godas",
        "copernicus",
        "argo",
        "ifremer_glider",
    }
    bio_roms = find_dataset(registry, "incois_bio_roms_v2")
    assert bio_roms.origin_url == "https://zenodo.org/records/14614739"
    assert bio_roms.version == "v2"
    assert bio_roms.expected_md5 == "78b7c0fbaa00db58a31563bb442a693b"
    assert bio_roms.local_path is not None and bio_roms.local_path.endswith("_v2.nc")
    assert all(
        item.role == "observation"
        for item in registry.datasets
        if item.source_id in {"argo", "ifremer_glider"}
    )
    assert "not" in bio_roms.published_notes.lower()
    assert "ready" not in bio_roms.model_fields_set


@pytest.mark.parametrize(
    "path",
    [
        "../outside.nc",
        "data/raw/../../../outside.nc",
        "data/processed/input.nc",
        "/data/raw/input.nc",
        "C:/data/raw/input.nc",
        r"C:data\raw\input.nc",
        r"\\server\share\input.nc",
        "data/raw/input.nc:secret",
        "data/raw/input.nc.crdownload",
        "data/raw/input.txt",
        "data/raw/hidden\x00.nc",
    ],
)
def test_definition_rejects_unsafe_or_partial_input_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        local_definition(local_path=path)


def test_windows_relative_path_is_normalized() -> None:
    definition = local_definition(local_path=r"data\raw\fixtures\synthetic.nc")
    assert definition.local_path == "data/raw/fixtures/synthetic.nc"


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.org/input",
        "file:///private/input.nc",
        "https://user:secret@example.org/input",
        "https://example.org/input?token=private",
        "https://example.org/input#private",
        "https:///missing-host",
    ],
)
def test_origins_cannot_embed_credentials_or_private_query_values(origin: str) -> None:
    with pytest.raises(ValidationError):
        local_definition(origin_url=origin)


@pytest.mark.parametrize(
    "changes",
    [
        {"local_path": None},
        {"access_method": "opendap"},
        {"expected_md5": "not-an-md5"},
        {"dataset_id": "../escape"},
        {"source_id": "UPPERCASE"},
        {"extra_secret": "must-not-be-accepted"},
    ],
)
def test_definition_rejects_inconsistent_or_unknown_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        local_definition(**changes)


def test_nonlocal_source_cannot_carry_local_checksum() -> None:
    with pytest.raises(ValidationError):
        local_definition(
            access_method="opendap", local_path=None, expected_md5="0" * 32
        )


def test_duplicate_dataset_ids_are_rejected() -> None:
    definition = local_definition()
    with pytest.raises(ValidationError):
        SourceRegistry(datasets=[definition, definition])


def test_unknown_dataset_has_a_safe_error() -> None:
    with pytest.raises(RegistryError, match="^Unknown dataset ID$"):
        find_dataset(SourceRegistry(datasets=[local_definition()]), "private-name")


@pytest.mark.parametrize(
    "contents",
    [
        "datasets: [",
        "!!python/object/apply:os.system ['must never execute']",
        "schema_version: 2\ndatasets: []\n",
        "schema_version: 1\ndatasets: []\n",
        "- not-a-registry\n",
    ],
)
def test_invalid_registry_reports_safe_error(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "private-registry.yaml"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(RegistryError) as caught:
        load_registry(path)
    assert str(caught.value) == "Registry is unavailable or invalid"
    assert str(tmp_path) not in str(caught.value)


def test_registry_missing_or_oversized_has_safe_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(RegistryError, match="unavailable or invalid"):
        load_registry(tmp_path / "missing.yaml")
    monkeypatch.setattr(registry_module, "MAX_REGISTRY_BYTES", 16)
    path = tmp_path / "oversized.yaml"
    path.write_bytes(b"x" * 17)
    with pytest.raises(RegistryError, match="size limit"):
        load_registry(path)


def test_resolver_rejects_escape_and_accepts_missing_safe_input(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="inside"):
        resolve_local_input(tmp_path, "data/raw/../../../outside.nc")
    expected = tmp_path / "data" / "raw" / "fixture.nc"
    assert resolve_local_input(tmp_path, "data/raw/fixture.nc") == expected.resolve()


@pytest.mark.parametrize("escape_from_raw_root", [False, True])
def test_resolver_rejects_symlink_escape(
    tmp_path: Path, escape_from_raw_root: bool
) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "data").mkdir(parents=True)
    link = project / "data" / "raw"
    if not escape_from_raw_root:
        link.mkdir()
        link = link / "fixtures"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"OS does not permit test symlinks: {error.winerror}")
    with pytest.raises(RegistryError, match="inside"):
        resolve_local_input(project, "data/raw/fixtures/synthetic.nc")
