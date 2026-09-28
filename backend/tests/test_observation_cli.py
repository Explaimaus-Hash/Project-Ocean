"""End-to-end operator normalization on tiny synthetic local files only."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from backend.app.processing import observations
from backend.app.schemas.acquisition import AcquisitionManifest, AcquisitionRequest
from backend.app.storage.observations import ObservationStore
from backend.app.storage.product_common import describe_file
from backend.tests.test_observations import make_observations
from scripts import prepare_observations as cli

ACQUISITION_ID = "a_" + "2" * 24


@pytest.fixture
def cli_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "data/raw").mkdir(parents=True)
    definitions = [
        {
            "source_id": "argo",
            "dataset_id": "argo_gdac",
            "title": "Synthetic Argo source",
            "role": "observation",
            "access_method": "argopy",
            "origin_url": "ftp://ftp.ifremer.fr/ifremer/argo",
        },
        {
            "source_id": "ifremer_glider",
            "dataset_id": "ifremer_glider_v2",
            "title": "Synthetic EGO source",
            "role": "observation",
            "access_method": "ftp",
            "origin_url": "ftp://ftp.ifremer.fr/ifremer/glider/v2/",
        },
        {
            "source_id": "incois_godas",
            "dataset_id": "incois_godas_2025",
            "title": "Synthetic model source",
            "role": "model",
            "access_method": "opendap",
            "origin_url": "https://las.incois.gov.in/thredds/dodsC/las/test",
        },
    ]
    (tmp_path / "config/data_sources.yaml").write_text(
        json.dumps({"schema_version": 1, "datasets": definitions}), encoding="utf-8"
    )
    (tmp_path / "selection.json").write_text(
        json.dumps(
            {
                "region": {"west": 30, "east": 120, "south": -30, "north": 30},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "pressure_min_dbar": 0,
                "pressure_max_dbar": 2000,
                "variables": ["PRES", "TEMP", "PSAL"],
                "value_mode": "raw",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def input_arguments(**changes):
    arguments = {
        "--dataset": "argo_gdac",
        "--input": "data/raw/test.nc",
        "--request": "selection.json",
    }
    arguments.update(changes)
    return [value for pair in arguments.items() for value in pair] + ["--synthetic"]


def read_output(capsys):
    output = capsys.readouterr()
    assert output.err == ""
    payload = json.loads(output.out)
    assert "Traceback" not in output.out
    assert "OneDrive" not in output.out
    return payload


def test_input_prepares_immutable_scientific_collection(cli_workspace, capsys):
    raw = make_observations(cli_workspace / "data/raw/test.nc")
    before = hashlib.sha256(raw.read_bytes()).hexdigest()
    assert cli.main(input_arguments()) == 0
    first = read_output(capsys)
    assert first["status"] == "prepared"
    metadata = first["metadata"]
    assert metadata["data_mode"] == "synthetic"
    assert metadata["counts"]["selected_samples"] == 6
    assert (
        metadata["client_processing"]
        == "local_operator_input_client_processing_unknown"
    )
    assert "input_file" not in metadata and "source_filename" not in metadata
    collection_id = metadata["collection_id"]
    collection_path = (
        cli_workspace / "data/observations" / collection_id / "collection.json"
    )
    file_before = collection_path.stat().st_mtime_ns
    assert cli.main(input_arguments()) == 0
    assert read_output(capsys) == first
    assert collection_path.stat().st_mtime_ns == file_before
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == before
    collection = ObservationStore(cli_workspace).collection(collection_id)
    assert collection.samples[0].values["TEMP"].raw == 21
    assert collection.samples[0].values["TEMP"].adjusted == 21.5
    assert collection.capabilities.comparison_ready is False


@pytest.mark.parametrize(
    "changes",
    [
        {"--dataset": "incois_godas_2025"},
        {"--dataset": "not_registered"},
        {"--input": "../secret.nc"},
        {"--request": "../secret-selection.json"},
    ],
)
def test_source_or_path_rejected_before_normalization(
    cli_workspace, capsys, monkeypatch, changes
):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid source/path must not begin normalization")

    monkeypatch.setattr(observations, "normalize_observations", forbidden)
    assert cli.main(input_arguments(**changes)) == 2
    result = read_output(capsys)
    assert "error" in result
    assert "secret" not in result["error"]["message"]
    assert not (cli_workspace / "data/observations").exists()


@pytest.mark.parametrize("content", ["{broken JSON", "{}", '{"value_mode":"auto"}'])
def test_invalid_selection_safe_error_and_no_writes(
    cli_workspace, capsys, monkeypatch, content
):
    (cli_workspace / "selection.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        observations,
        "normalize_observations",
        lambda *args, **kwargs: pytest.fail("Invalid selection must not open source"),
    )
    assert cli.main(input_arguments()) == 2
    result = read_output(capsys)
    assert "error" in result
    assert not (cli_workspace / "data/observations").exists()


def test_no_overlap_publishes_successful_empty_collection(cli_workspace, capsys):
    make_observations(cli_workspace / "data/raw/test.nc")
    selection_path = cli_workspace / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selection["region"] = {"west": 30, "east": 40, "south": -30, "north": 30}
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    assert cli.main(input_arguments()) == 0
    result = read_output(capsys)
    assert result["status"] == "prepared"
    assert result["metadata"]["counts"]["selected_samples"] == 0
    assert result["metadata"]["counts"]["outside_selection"] == 6
    assert (
        ObservationStore(cli_workspace)
        .collection(result["metadata"]["collection_id"])
        .samples
        == []
    )


def save_synthetic_acquisition(
    root, *, source_id="argo", client_processing=None, false_hash=False
):
    directory = root / "data/raw/acquisitions" / ACQUISITION_ID
    directory.mkdir(parents=True)
    source = make_observations(directory / "input.nc", layout="points")
    source_record = describe_file(source, 1024 * 1024)
    if false_hash:
        source_record = source_record.model_copy(update={"sha256": "0" * 64})
    provider = directory / "provider_input.nc"
    provider.write_bytes(source.read_bytes())
    request = AcquisitionRequest(
        provider="argo",
        dataset_id="argo_gdac",
        selection={
            "region": {"west": 30, "east": 120, "south": -30, "north": 30},
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-31T00:00:00Z",
            "vertical_min": 0,
            "vertical_max": 2000,
            "vertical_kind": "pressure_dbar",
        },
    )
    manifest = AcquisitionManifest(
        acquisition_id=ACQUISITION_ID,
        dataset_id="argo_gdac",
        source_id=source_id,
        origin_url="ftp://ftp.ifremer.fr/ifremer/argo",
        request=request,
        input_file=source_record,
        provider_file=describe_file(provider, 1024 * 1024),
        created_at=datetime(2024, 2, 1, tzinfo=UTC),
        retrieved_at=None,
        data_mode="synthetic",
        client="argopy",
        client_version="test-only",
        client_processing=client_processing
        or (
            "Argopy src=erddap, ds=phy, mode=expert; "
            "no standard/research QC/data-mode filter. Synthetic fixture only."
        ),
        transport="https",
    )
    (directory / "manifest.json").write_text(
        manifest.model_dump_json(), encoding="utf-8"
    )
    return manifest


def acquisition_arguments():
    # No --synthetic flag: the acquisition must preserve its existing fixture label.
    return [
        "--dataset",
        "argo_gdac",
        "--acquisition",
        ACQUISITION_ID,
        "--request",
        "selection.json",
    ]


def test_acquisition_preserves_hash_source_mode_and_expert_provenance(
    cli_workspace, capsys
):
    manifest = save_synthetic_acquisition(cli_workspace)
    assert cli.main(acquisition_arguments()) == 0
    metadata = read_output(capsys)["metadata"]
    assert metadata["source_id"] == "argo"
    assert metadata["dataset_id"] == "argo_gdac"
    assert metadata["data_mode"] == "synthetic"
    assert metadata["client_processing"] == "argopy_expert_no_qc_filter"
    assert metadata["input_sha256"] == manifest.input_file.sha256
    collection = ObservationStore(cli_workspace).collection(metadata["collection_id"])
    assert collection.input_file == manifest.input_file
    assert "argopy_point_representation_is_not_untouched_gdac" in collection.warnings


@pytest.mark.parametrize(
    "change,code", [("source", "source_mismatch"), ("hash", "input_changed")]
)
def test_acquisition_source_or_checksum_mismatch_not_published(
    cli_workspace, capsys, change, code
):
    save_synthetic_acquisition(
        cli_workspace,
        source_id="ifremer_glider" if change == "source" else "argo",
        false_hash=change == "hash",
    )
    assert cli.main(acquisition_arguments()) == 2
    assert read_output(capsys)["error"]["code"] == code
    assert not (cli_workspace / "data/observations").exists()


def test_acquisition_standard_mode_never_claims_expert(cli_workspace, capsys):
    save_synthetic_acquisition(
        cli_workspace,
        client_processing=(
            "Argopy mode=standard; synthetic fixture with QC filtering already applied."
        ),
    )
    result_code = cli.main(acquisition_arguments())
    result = read_output(capsys)
    if result_code == 0:
        assert result["metadata"]["client_processing"] != "argopy_expert_no_qc_filter"
    else:
        assert result_code == 2
        assert "error" in result
        assert not (cli_workspace / "data/observations").exists()
