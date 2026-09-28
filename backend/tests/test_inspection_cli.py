"""Operator argument, exit-code, and save-opt-in tests on tiny local fixtures."""

import json
import subprocess
import sys
from pathlib import Path

import netCDF4
import pytest

from backend.app.ingestion.incois_bio_roms import input_status
from backend.app.ingestion.registry import RegistryError, load_registry
from backend.app.schemas.datasets import DatasetDefinition, SourceRegistry
from scripts import inspect_dataset as cli


@pytest.fixture
def isolated_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DatasetDefinition:
    definition = DatasetDefinition(
        source_id="incois_bio_roms",
        dataset_id="synthetic_fixture",
        title="Synthetic CLI fixture, not source ocean data",
        role="model",
        access_method="local_netcdf",
        origin_url="https://example.org/synthetic",
        local_path="data/raw/synthetic.nc",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        cli, "load_registry", lambda: SourceRegistry(datasets=[definition])
    )
    return definition


def create_tiny_input(tmp_path: Path) -> None:
    path = tmp_path / "data" / "raw" / "synthetic.nc"
    path.parent.mkdir(parents=True)
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.title = "SYNTHETIC CLI TEST ONLY"
        dataset.createDimension("sample", 1)
        variable = dataset.createVariable("TEMP", "f4", ("sample",))
        variable.units = "degree_Celsius"


@pytest.mark.parametrize(
    "arguments",
    [[], ["inspect"], ["unknown"], ["status", "--save"], ["inspect", "x", "--unknown"]],
)
def test_cli_rejects_invalid_arguments(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 2


def test_status_lists_all_sources_without_inspecting_or_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = load_registry()
    monkeypatch.setattr(cli, "load_registry", lambda: registry)
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Status must not inspect or save")

    monkeypatch.setattr(cli, "inspect_local_dataset", forbidden)
    monkeypatch.setattr(cli, "save_inspection_report", forbidden)
    assert cli.main(["status"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    payload = json.loads(output.out)
    assert payload["schema_version"] == 1
    assert len(payload["datasets"]) == 8
    assert {report["status"] for report in payload["datasets"]} == {
        "not_configured",
        "unavailable",
    }
    assert list(tmp_path.iterdir()) == []


def test_inspect_defaults_do_not_hash_or_save(
    isolated_cli: DatasetDefinition,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_tiny_input(tmp_path)

    def forbidden_save(*args: object, **kwargs: object) -> None:
        raise AssertionError("Inspection must not save without --save")

    monkeypatch.setattr(cli, "save_inspection_report", forbidden_save)
    assert cli.main(["inspect", isolated_cli.dataset_id]) == 0
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert output.err == ""
    assert report["status"] == "not_prepared"
    assert report["prepared"] is False
    assert report["checksum_status"] == "not_checked"
    assert not (tmp_path / "data" / "metadata").exists()


def test_verify_and_save_flags_are_explicitly_forwarded(
    isolated_cli: DatasetDefinition,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_tiny_input(tmp_path)
    original_inspect = cli.inspect_local_dataset
    observed: list[bool] = []

    def inspect_spy(
        definition: DatasetDefinition, project_root: Path, *, verify_checksum: bool
    ):
        assert project_root == tmp_path
        observed.append(verify_checksum)
        return original_inspect(
            definition, project_root, verify_checksum=verify_checksum
        )

    monkeypatch.setattr(cli, "inspect_local_dataset", inspect_spy)
    assert (
        cli.main(["inspect", isolated_cli.dataset_id, "--verify-checksum", "--save"])
        == 0
    )
    assert observed == [True]
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["checksum_status"] == "not_provided"
    saved = tmp_path / "data" / "metadata" / "synthetic_fixture.json"
    assert json.loads(saved.read_text()) == report


def test_unavailable_input_returns_nonzero_without_implicit_save(
    isolated_cli: DatasetDefinition, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["inspect", isolated_cli.dataset_id]) == 2
    report = json.loads(capsys.readouterr().out)
    assert (report["status"], report["reason_code"]) == ("unavailable", "file_missing")
    assert list(tmp_path.iterdir()) == []


def test_unknown_dataset_or_registry_failure_has_safe_operator_error(
    isolated_cli: DatasetDefinition,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["inspect", "unknown_dataset"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"] == "operator_request_failed"

    def failed_load() -> SourceRegistry:
        raise RegistryError(f"synthetic private error: {tmp_path}")

    monkeypatch.setattr(cli, "load_registry", failed_load)
    assert cli.main(["status"]) == 2
    output = capsys.readouterr()
    assert json.loads(output.err)["error"] == "operator_request_failed"
    assert str(tmp_path) not in output.err


@pytest.mark.parametrize(
    "status", ["invalid", "unsupported", "uninspected", "not_configured"]
)
def test_nonprepared_inspection_outcomes_return_exit_two(
    isolated_cli: DatasetDefinition,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
) -> None:
    report = input_status(isolated_cli, tmp_path).model_copy(update={"status": status})
    monkeypatch.setattr(cli, "inspect_local_dataset", lambda *args, **kwargs: report)
    assert cli.main(["inspect", isolated_cli.dataset_id]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == status


def test_save_failure_returns_safe_error_and_exit_two(
    isolated_cli: DatasetDefinition,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_tiny_input(tmp_path)

    def failed_save(*args: object, **kwargs: object) -> None:
        raise OSError(f"synthetic private error: {tmp_path}")

    monkeypatch.setattr(cli, "save_inspection_report", failed_save)
    assert cli.main(["inspect", isolated_cli.dataset_id, "--save"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"] == "operator_request_failed"
    assert str(tmp_path) not in output.err


def test_module_entry_point_help_succeeds_without_inspection() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.inspect_dataset", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "status" in result.stdout and "inspect" in result.stdout
