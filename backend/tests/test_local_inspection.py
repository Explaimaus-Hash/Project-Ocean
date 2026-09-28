"""Local registration, explicit checksums, and atomic private reports."""

import hashlib
import io
import json
import os
from pathlib import Path

import netCDF4
import pytest

from backend.app.ingestion import incois_bio_roms as adapter
from backend.app.ingestion import netcdf_metadata as metadata_module
from backend.app.schemas.datasets import DatasetDefinition, InspectionReport
from backend.app.storage import inspection_reports as report_storage


@pytest.fixture
def local_input(tmp_path: Path) -> tuple[DatasetDefinition, Path]:
    path = tmp_path / "data" / "raw" / "synthetic.nc"
    path.parent.mkdir(parents=True)
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.title = "SYNTHETIC TEST INPUT; NOT SOURCE OCEAN DATA"
        dataset.createDimension("sample", 2)
        variable = dataset.createVariable("TEMP", "f4", ("sample",))
        variable.units = "degree_Celsius"
        variable[:] = [20, 21]
    definition = DatasetDefinition(
        source_id="incois_bio_roms",
        dataset_id="synthetic_fixture",
        title="Synthetic test fixture",
        role="model",
        access_method="local_netcdf",
        origin_url="https://example.org/synthetic",
        version="synthetic-v1",
        local_path="data/raw/synthetic.nc",
        expected_md5=hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest(),
    )
    return definition, path


def test_missing_partial_empty_and_uninspected_are_distinct(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, path = local_input
    report = adapter.input_status(definition, tmp_path)
    assert (report.status, report.reason_code) == (
        "uninspected",
        "metadata_not_inspected",
    )
    assert report.file_identity is not None
    assert report.file_identity.size_bytes == path.stat().st_size
    path.rename(path.with_suffix(".nc.crdownload"))
    missing = adapter.input_status(definition, tmp_path)
    assert (missing.status, missing.reason_code) == ("unavailable", "file_missing")
    path.touch()
    empty = adapter.input_status(definition, tmp_path)
    assert (empty.status, empty.reason_code) == ("invalid", "empty_file")


def test_status_does_not_open_data(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input

    def forbidden_open(*args: object, **kwargs: object) -> None:
        raise AssertionError("Status must not open the local input")

    monkeypatch.setattr(Path, "open", forbidden_open)
    assert adapter.input_status(definition, tmp_path).status == "uninspected"


def test_remote_adapter_is_not_configured_without_network_work(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, _ = local_input
    remote = definition.model_copy(
        update={"access_method": "opendap", "local_path": None, "expected_md5": None}
    )
    report = adapter.inspect_local_dataset(remote, tmp_path)
    assert (report.status, report.reason_code) == (
        "not_configured",
        "local_inspection_not_applicable",
    )
    assert report.metadata is None and report.prepared is False


def test_inspection_is_not_preparation_and_does_not_implicitly_hash_or_save(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input

    def forbidden_hash(path: Path) -> str:
        raise AssertionError("Checksum must require explicit opt-in")

    monkeypatch.setattr(adapter, "calculate_md5", forbidden_hash)
    report = adapter.inspect_local_dataset(definition, tmp_path)
    assert (report.status, report.reason_code) == (
        "not_prepared",
        "metadata_inspected_only",
    )
    assert report.prepared is False
    assert report.checksum_status == "not_checked"
    assert report.observed_md5 is None
    assert report.metadata is not None
    assert report.metadata["data_values_read"] is False
    assert report.metadata["capability_status"] == "not_evaluated"
    assert report.source_version == "synthetic-v1"
    assert report.checked_at.tzinfo is not None
    assert str(tmp_path) not in report.model_dump_json()
    assert not (tmp_path / "data" / "metadata").exists()


def test_explicit_checksum_match_and_mismatch(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, _ = local_input
    verified = adapter.inspect_local_dataset(definition, tmp_path, verify_checksum=True)
    assert verified.status == "not_prepared" and verified.prepared is False
    assert verified.checksum_status == "verified"
    assert verified.observed_md5 == definition.expected_md5
    mismatching = definition.model_copy(update={"expected_md5": "0" * 32})
    mismatch = adapter.inspect_local_dataset(
        mismatching, tmp_path, verify_checksum=True
    )
    assert (mismatch.status, mismatch.reason_code) == ("invalid", "checksum_mismatch")
    assert mismatch.checksum_status == "mismatch"
    assert mismatch.metadata is None


def test_checksum_without_published_digest_is_not_verified(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, _ = local_input
    definition = definition.model_copy(update={"expected_md5": None})
    report = adapter.inspect_local_dataset(definition, tmp_path, verify_checksum=True)
    assert report.status == "not_prepared"
    assert report.checksum_status == "not_provided"
    assert report.observed_md5 is None


@pytest.mark.parametrize("matching_digest", [False, True])
def test_file_change_during_checksum_invalidates_observed_evidence(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    matching_digest: bool,
) -> None:
    definition, _ = local_input

    def changed_hash(path: Path) -> str:
        previous = path.stat()
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
        return definition.expected_md5 if matching_digest else "0" * 32

    monkeypatch.setattr(adapter, "calculate_md5", changed_hash)
    report = adapter.inspect_local_dataset(definition, tmp_path, verify_checksum=True)
    assert (report.status, report.reason_code) == (
        "uninspected",
        "file_changed_during_inspection",
    )
    assert report.observed_md5 is None
    assert report.checksum_status == "not_checked"
    assert report.metadata is None


def test_file_change_during_metadata_does_not_publish_stale_metadata(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input
    original = metadata_module.inspect_netcdf_metadata

    def changed_metadata(path: Path) -> dict:
        report = original(path)
        previous = path.stat()
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
        return report

    monkeypatch.setattr(metadata_module, "inspect_netcdf_metadata", changed_metadata)
    report = adapter.inspect_local_dataset(definition, tmp_path)
    assert report.reason_code == "file_changed_during_inspection"
    assert report.metadata is None and report.prepared is False


def test_metadata_failure_after_file_change_clears_verified_checksum(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input

    def changed_and_failed(path: Path) -> dict:
        previous = path.stat()
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
        raise metadata_module.MetadataInspectionError(
            "invalid_netcdf", "Synthetic error after the input changed"
        )

    monkeypatch.setattr(metadata_module, "inspect_netcdf_metadata", changed_and_failed)
    report = adapter.inspect_local_dataset(definition, tmp_path, verify_checksum=True)
    assert (report.status, report.reason_code) == (
        "uninspected",
        "file_changed_during_inspection",
    )
    assert report.checksum_status == "not_checked"
    assert report.observed_md5 is None
    assert report.metadata is None and report.prepared is False


def test_metadata_failure_after_file_removal_clears_verified_checksum(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input

    def removed_and_failed(path: Path) -> dict:
        path.unlink()
        raise metadata_module.MetadataInspectionError(
            "invalid_netcdf", "Synthetic error after the input was removed"
        )

    monkeypatch.setattr(metadata_module, "inspect_netcdf_metadata", removed_and_failed)
    report = adapter.inspect_local_dataset(definition, tmp_path, verify_checksum=True)
    assert (report.status, report.reason_code) == ("unavailable", "file_inaccessible")
    assert report.checksum_status == "not_checked"
    assert report.observed_md5 is None
    assert report.metadata is None and report.prepared is False


def test_complete_inspection_report_budget_is_enforced(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input
    monkeypatch.setattr(adapter, "MAX_REPORT_BYTES", 1)
    report = adapter.inspect_local_dataset(definition, tmp_path)
    assert (report.status, report.reason_code) == (
        "unsupported",
        "metadata_limit_exceeded",
    )
    assert report.metadata is None and report.prepared is False
    assert not (tmp_path / "data" / "metadata").exists()


def test_corrupt_and_unsupported_inputs_are_distinct(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, path = local_input
    path.write_bytes(b"SYNTHETIC CORRUPT FILE, NOT A NETCDF")
    corrupt = adapter.inspect_local_dataset(definition, tmp_path)
    assert (corrupt.status, corrupt.reason_code) == ("invalid", "invalid_netcdf")
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.createGroup("unsupported_nested_group")
    unsupported = adapter.inspect_local_dataset(definition, tmp_path)
    assert (unsupported.status, unsupported.reason_code) == (
        "unsupported",
        "unsupported_groups",
    )
    assert str(path) not in corrupt.model_dump_json()


@pytest.mark.parametrize(
    "code, expected_status",
    [
        ("metadata_limit_exceeded", "unsupported"),
        ("dependency_unavailable", "unavailable"),
    ],
)
def test_safe_metadata_error_classification(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    expected_status: str,
) -> None:
    definition, _ = local_input

    def unavailable(path: Path) -> dict:
        raise metadata_module.MetadataInspectionError(code, "safe fixture error")

    monkeypatch.setattr(metadata_module, "inspect_netcdf_metadata", unavailable)
    report = adapter.inspect_local_dataset(definition, tmp_path)
    assert report.status == expected_status
    assert report.reason_code == code


def test_directory_is_not_an_inspectable_file(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, path = local_input
    path.unlink()
    path.mkdir()
    report = adapter.inspect_local_dataset(definition, tmp_path)
    assert (report.status, report.reason_code) == ("unavailable", "not_regular_file")


def test_checksum_stream_reads_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"small synthetic checksum fixture"
    requests: list[int] = []

    class BoundedStream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            requests.append(size)
            assert size == 7
            return super().read(size)

    monkeypatch.setattr(adapter, "HASH_CHUNK_BYTES", 7)
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: BoundedStream(payload))
    result = adapter.calculate_md5(Path("synthetic-unused-path.nc"))
    assert result == hashlib.md5(payload, usedforsecurity=False).hexdigest()
    assert len(requests) > 1


def test_report_is_explicitly_saved_and_atomically_replaced(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path
) -> None:
    definition, path = local_input
    original_bytes = path.read_bytes()
    report = adapter.inspect_local_dataset(definition, tmp_path)
    saved = report_storage.save_inspection_report(report, tmp_path)
    assert saved == tmp_path / "data" / "metadata" / "synthetic_fixture.json"
    assert InspectionReport.model_validate_json(saved.read_text()) == report
    assert saved.read_bytes().endswith(b"\n")
    replacement = report.model_copy(update={"reason_code": "synthetic_second_report"})
    assert report_storage.save_inspection_report(replacement, tmp_path) == saved
    assert json.loads(saved.read_text())["reason_code"] == "synthetic_second_report"
    assert list(saved.parent.glob(".inspection-*.tmp")) == []
    assert path.read_bytes() == original_bytes


def test_failed_report_replace_preserves_old_report_and_removes_temp(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input
    report = adapter.input_status(definition, tmp_path)
    saved = report_storage.save_inspection_report(report, tmp_path)
    original = saved.read_bytes()

    def failed_replace(source: Path, destination: Path) -> None:
        assert source.parent == destination.parent
        assert source.exists()
        assert destination.read_bytes() == original
        raise OSError("synthetic replacement failure")

    monkeypatch.setattr(report_storage.os, "replace", failed_replace)
    with pytest.raises(OSError, match="replacement failure"):
        report_storage.save_inspection_report(report, tmp_path)
    assert saved.read_bytes() == original
    assert list(saved.parent.glob(".inspection-*.tmp")) == []


@pytest.mark.parametrize("dataset_id", ["../escape", "", "Uppercase", "a" * 97])
def test_report_rejects_unsafe_ids_before_writing(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path, dataset_id: str
) -> None:
    definition, _ = local_input
    report = adapter.input_status(definition, tmp_path)
    report = report.model_copy(update={"dataset_id": dataset_id})
    with pytest.raises(ValueError, match="dataset ID"):
        report_storage.save_inspection_report(report, tmp_path)
    assert not (tmp_path / "data" / "metadata").exists()


def test_report_limit_is_enforced_before_creating_output_directory(
    local_input: tuple[DatasetDefinition, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _ = local_input
    report = adapter.input_status(definition, tmp_path)
    monkeypatch.setattr(report_storage, "MAX_REPORT_BYTES", 16)
    with pytest.raises(ValueError, match="size limit"):
        report_storage.save_inspection_report(report, tmp_path)
    assert not (tmp_path / "data" / "metadata").exists()


@pytest.mark.parametrize("symlink_file", [False, True])
def test_report_rejects_symlink_escape_without_altering_target(
    local_input: tuple[DatasetDefinition, Path], tmp_path: Path, symlink_file: bool
) -> None:
    definition, _ = local_input
    report = adapter.input_status(definition, tmp_path)
    outside = tmp_path / "outside_metadata"
    outside.mkdir()
    target = outside / "original.json"
    target.write_text("SYNTHETIC DO NOT OVERWRITE", encoding="utf-8")
    directory = tmp_path / "data" / "metadata"
    link = directory
    if symlink_file:
        directory.mkdir()
        link = directory / "synthetic_fixture.json"
    try:
        link.symlink_to(
            target if symlink_file else outside, target_is_directory=not symlink_file
        )
    except OSError as error:
        pytest.skip(f"OS does not permit test symlinks: {error.winerror}")
    with pytest.raises(ValueError, match="inside|Unsafe"):
        report_storage.save_inspection_report(report, tmp_path)
    assert target.read_text() == "SYNTHETIC DO NOT OVERWRITE"
