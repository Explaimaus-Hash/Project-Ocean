"""Operator acquisition orchestration; no network/scientific imports at import.

Provider work runs in one disposable child with a wall-clock deadline. The child
cannot publish: the parent validates and atomically renames the completed stage.
Native-library allocations are not an operating-system memory sandbox.
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..schemas.acquisition import (
    MAX_ACQUISITION_BYTES,
    MAX_ACQUISITION_MANIFEST,
    MAX_ACQUISITIONS,
    AcquisitionManifest,
    AcquisitionRequest,
)
from ..schemas.datasets import DatasetDefinition
from ..storage.product_common import (
    ProductError,
    contained,
    describe_file,
    read_json,
    stat_file,
)
from .base import fail


def _definition(root: Path, request: AcquisitionRequest) -> DatasetDefinition:
    from .registry import RegistryError, find_dataset, load_registry

    try:
        definition = find_dataset(
            load_registry(root / "config/data_sources.yaml"), request.dataset_id
        )
    except RegistryError:
        raise ProductError(
            "configuration_unavailable", "Source configuration is invalid."
        ) from None
    expected = {
        "godas": ("incois_godas", "opendap"),
        "copernicus": ("copernicus", "copernicusmarine"),
        "argo": ("argo", "argopy"),
        "glider": ("ifremer_glider", "ftp"),
    }
    if request.provider == "local":
        if definition.source_id not in {
            "incois_godas",
            "copernicus",
            "argo",
            "ifremer_glider",
        }:
            raise fail("unsupported_source")
    elif (definition.source_id, definition.access_method) != expected[request.provider]:
        raise fail("unsupported_source")
    if request.provider == "godas":
        from urllib.parse import urlsplit

        url = urlsplit(definition.origin_url)
        if (
            url.scheme != "https"
            or url.hostname != "las.incois.gov.in"
            or not url.path.startswith("/thredds/dodsC/las/id-")
        ):
            raise fail("unsafe_transport")
    return definition


def _acquisition_dir(root: Path, acquisition_id: str) -> Path:
    if not re.fullmatch(r"a_[0-9a-f]{24}", acquisition_id):
        raise ProductError(
            "invalid_acquisition_id", "Acquisition identifier is invalid."
        )
    return contained(root, f"data/raw/acquisitions/{acquisition_id}")


def read_acquisition(root: Path, acquisition_id: str) -> AcquisitionManifest:
    """Read bounded manifest/stat identity only, not NetCDF or provider data."""
    directory = _acquisition_dir(root, acquisition_id)
    try:
        manifest = AcquisitionManifest.model_validate(
            read_json(
                contained(
                    root, str((directory / "manifest.json").relative_to(root.resolve()))
                ),
                MAX_ACQUISITION_MANIFEST,
            )
        )
        if manifest.acquisition_id != acquisition_id:
            raise ValueError("identity")
        for name, record in (
            ("input.nc", manifest.input_file),
            ("provider_input.nc", manifest.provider_file),
        ):
            if record is not None and stat_file(
                contained(root, str((directory / name).relative_to(root.resolve()))),
                MAX_ACQUISITION_BYTES,
            ) != (record.size_bytes, record.modified_ns):
                raise ValueError("changed input")
        return manifest
    except (ValidationError, ValueError):
        raise ProductError(
            "acquisition_unavailable", "Acquisition manifest or input is invalid."
        ) from None


def list_acquisitions(root: Path) -> list[AcquisitionManifest]:
    """List at most 64 finished acquisitions; invalid entries never count ready."""
    directory = contained(root, "data/raw/acquisitions")
    if not directory.exists():
        return []
    result = []
    count = 0
    for path in directory.iterdir():
        count += 1
        if count > MAX_ACQUISITIONS:
            raise fail("acquisition_limit")
        if re.fullmatch(r"a_[0-9a-f]{24}", path.name):
            try:
                result.append(read_acquisition(root, path.name))
            except ProductError:
                # Missing/corrupt source acquisition is not a ready product.
                continue
    return sorted(result, key=lambda item: item.acquisition_id)


def _cleanup_stage(stage: Path) -> None:
    """Only remove this invocation's known temporary files, never recursive raw data."""
    for name in (
        "input.nc",
        "provider_input.nc",
        "request.json",
        "result.json",
        "manifest.json",
    ):
        (stage / name).unlink(missing_ok=True)
    try:
        stage.rmdir()
    except OSError:
        # Leave unrecognized provider artifacts for explicit operator review;
        # never recursively delete them or mask the original acquisition error.
        pass


def _run_worker(root: Path, stage: Path, request: AcquisitionRequest) -> dict[str, Any]:
    request_path = stage / "request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    # No credentials in command arguments or stdout/stderr. stdin is disabled.
    process = subprocess.Popen(
        [sys.executable, "-m", "scripts.acquire_dataset", "--worker", str(stage)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    try:
        process.wait(timeout=request.deadline_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        raise ProductError(
            "acquisition_timeout", "Acquisition exceeded its operator deadline."
        ) from None
    except BaseException:
        process.kill()
        process.wait(timeout=10)
        raise
    result = read_json(stage / "result.json", MAX_ACQUISITION_MANIFEST)
    if not isinstance(result, dict) or result.get("ok") is not True:
        code = (
            result.get("code", "provider_unavailable")
            if isinstance(result, dict)
            else "provider_unavailable"
        )
        if code not in {
            "provider_unavailable",
            "acquisition_limit",
            "unsupported_source",
            "no_data",
            "credentials_missing",
            "unsafe_transport",
            "input_changed",
            "dependency_unavailable",
            "provider_request_rejected",
            "provider_auth_failed",
        }:
            code = "provider_unavailable"
        raise fail(code)
    return result["details"]


def acquire_dataset(
    request: AcquisitionRequest, root: Path, *, data_mode: str = "real"
) -> AcquisitionManifest:
    """Acquire one bounded source subset/file; successful acquisition is not ready."""
    definition = _definition(root, request)
    if request.provider == "copernicus":
        from .copernicus import credentials

        credentials()  # Fail before child setup/client import if not configured.
    raw = contained(root, "data/raw/acquisitions")
    raw.mkdir(parents=True, exist_ok=True)
    if len(list(islice(raw.iterdir(), MAX_ACQUISITIONS))) >= MAX_ACQUISITIONS:
        raise fail("acquisition_limit")
    stage = Path(tempfile.mkdtemp(prefix=".acquire_", dir=raw))
    try:
        details = _run_worker(root, stage, request)
        file_record = describe_file(stage / "input.nc", request.max_bytes)
        provider_path = stage / "provider_input.nc"
        provider_record = (
            describe_file(provider_path, request.max_bytes)
            if provider_path.exists()
            else None
        )
        identity = {
            "request": request.model_dump(mode="json"),
            "source_id": definition.source_id,
            "source_version": request.provider_version or definition.version,
            "origin_url": definition.origin_url,
            "sha256": file_record.sha256,
            "provider_sha256": provider_record.sha256 if provider_record else None,
            "acquisition_version": "acquisition_1",
            "data_mode": data_mode,
        }
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:24]
        acquisition_id = f"a_{digest}"
        now = datetime.now(UTC)
        manifest = AcquisitionManifest(
            acquisition_id=acquisition_id,
            dataset_id=definition.dataset_id,
            source_id=definition.source_id,
            origin_url=definition.origin_url,
            source_version=request.provider_version or definition.version,
            request=request,
            input_file=file_record,
            provider_file=provider_record,
            created_at=now,
            retrieved_at=None if request.provider == "local" else now,
            data_mode=data_mode,
            **details,
        )
        encoded = manifest.model_dump_json(indent=2).encode()
        if len(encoded) > MAX_ACQUISITION_MANIFEST:
            raise fail("acquisition_limit")
        final = _acquisition_dir(root, acquisition_id)
        if final.exists():
            existing = read_acquisition(root, acquisition_id)
            if (
                existing.input_file.sha256 != file_record.sha256
                or describe_file(final / "input.nc", request.max_bytes).sha256
                != file_record.sha256
            ):
                raise fail("input_changed")
            if (
                provider_record is not None
                and describe_file(final / "provider_input.nc", request.max_bytes).sha256
                != provider_record.sha256
            ):
                raise fail("input_changed")
            return existing
        (stage / "request.json").unlink(missing_ok=True)
        (stage / "result.json").unlink(missing_ok=True)
        (stage / "manifest.json").write_bytes(encoded)
        stage.rename(final)
        return manifest
    finally:
        if stage.exists():
            _cleanup_stage(stage)


def run_worker(stage: Path, root: Path) -> None:
    """Private CLI subprocess entry; never serve this as an HTTP job endpoint."""
    # Only a generated stage under this project's raw acquisition directory.
    expected_root = contained(root, "data/raw/acquisitions")
    if stage.resolve().parent != expected_root or not stage.name.startswith(
        ".acquire_"
    ):
        raise fail("unsupported_source")
    outcome: dict[str, Any]
    try:
        request = AcquisitionRequest.model_validate(
            read_json(stage / "request.json", MAX_ACQUISITION_MANIFEST)
        )
        definition = _definition(root, request)
        if request.provider == "local":
            details = _import_local(request, definition, stage / "input.nc", root)
        else:
            from importlib import import_module

            module_name = (
                "incois_godas" if request.provider == "godas" else request.provider
            )
            adapter = import_module(f"backend.app.ingestion.{module_name}")
            details = adapter.fetch(request, definition, stage / "input.nc")
        outcome = {"ok": True, "details": details}
    except ProductError as error:
        outcome = {"ok": False, "code": error.code}
    except ImportError:
        outcome = {"ok": False, "code": "dependency_unavailable"}
    except Exception:
        outcome = {"ok": False, "code": "provider_unavailable"}
    (stage / "result.json").write_text(json.dumps(outcome), encoding="utf-8")


def _import_local(
    request: AcquisitionRequest,
    definition: DatasetDefinition,
    destination: Path,
    root: Path,
) -> dict[str, Any]:
    from .base import validate_raw
    from .registry import resolve_local_input

    assert request.local_path is not None
    source = resolve_local_input(root, request.local_path)
    before = stat_file(source, request.max_bytes)
    transferred = 0
    with source.open("rb") as original, destination.open("xb") as copied:
        while block := original.read(1_048_576):
            transferred += len(block)
            if transferred > request.max_bytes:
                raise fail("acquisition_limit")
            copied.write(block)
    if before != stat_file(source, request.max_bytes) or transferred != before[0]:
        raise fail("input_changed")
    validate_raw(destination, request)
    return {
        "client": "Project Ocean immutable local import",
        "client_version": "acquisition_1",
        "client_processing": (
            "Existing operator-provided NetCDF copied unchanged. Source family is "
            "operator-assigned; original retrieval time unknown. No spatial/time/QC "
            "filtering or scientific conversion."
        ),
        "transport": "local",
        "original_filename": source.name,
    }
