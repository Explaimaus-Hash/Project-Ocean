"""Explicit local BIO-ROMS inspection, without downloads or data preparation."""

import hashlib
import stat
from datetime import UTC, datetime
from pathlib import Path

from ..schemas.datasets import (
    MAX_REPORT_BYTES,
    DatasetDefinition,
    FileIdentity,
    InspectionReport,
    serialize_inspection_report,
)
from .registry import PROJECT_ROOT, RegistryError, resolve_local_input

HASH_CHUNK_BYTES = 1024 * 1024
# Windows offline / recall-on-open / recall-on-data-access file attributes.
UNAVAILABLE_LOCAL_ATTRIBUTES = 0x1000 | 0x40000 | 0x400000


def _identity(path: Path) -> FileIdentity:
    details = path.stat()
    if not stat.S_ISREG(details.st_mode):
        raise ValueError("not_regular_file")
    if getattr(details, "st_file_attributes", 0) & UNAVAILABLE_LOCAL_ATTRIBUTES:
        raise ValueError("file_not_local")
    return FileIdentity(size_bytes=details.st_size, modified_ns=details.st_mtime_ns)


def input_status(
    definition: DatasetDefinition, project_root: Path = PROJECT_ROOT
) -> InspectionReport:
    """Check only the configured final path; never open a download or NetCDF."""
    report = InspectionReport(
        source_id=definition.source_id,
        dataset_id=definition.dataset_id,
        source_version=definition.version,
        origin_url=definition.origin_url,
        checked_at=datetime.now(UTC),
        status="not_configured",
        reason_code="local_inspection_not_applicable",
        local_path=definition.local_path,
        expected_md5=definition.expected_md5,
    )
    if definition.access_method != "local_netcdf":
        return report
    try:
        path = resolve_local_input(project_root, definition.local_path or "")
        identity = _identity(path)
        if identity.size_bytes == 0:
            return report.model_copy(
                update={"status": "invalid", "reason_code": "empty_file"}
            )
    except FileNotFoundError:
        return report.model_copy(
            update={"status": "unavailable", "reason_code": "file_missing"}
        )
    except RegistryError:
        return report.model_copy(
            update={"status": "invalid", "reason_code": "unsafe_local_path"}
        )
    except ValueError as error:
        return report.model_copy(
            update={"status": "unavailable", "reason_code": str(error)}
        )
    except OSError:
        return report.model_copy(
            update={"status": "unavailable", "reason_code": "file_inaccessible"}
        )
    return report.model_copy(
        update={
            "status": "uninspected",
            "reason_code": "metadata_not_inspected",
            "file_identity": identity,
        }
    )


def calculate_md5(path: Path) -> str:
    """Stream file-integrity bytes in bounded memory; explicit operator work."""
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        while block := stream.read(HASH_CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def _interrupted_report(
    report: InspectionReport, *, inaccessible: bool = False
) -> InspectionReport:
    return report.model_copy(
        update={
            "status": "unavailable" if inaccessible else "uninspected",
            "reason_code": (
                "file_inaccessible"
                if inaccessible
                else "file_changed_during_inspection"
            ),
            "checksum_status": "not_checked",
            "observed_md5": None,
            "metadata": None,
        }
    )


def inspect_local_dataset(
    definition: DatasetDefinition,
    project_root: Path = PROJECT_ROOT,
    *,
    verify_checksum: bool = False,
) -> InspectionReport:
    """Inspect a completed local input, keeping inspection separate from readiness.

    Metadata inspection does not read variable values. Optional MD5 verification
    reads every file byte sequentially and may take time for a 9.2 GB input.
    """
    report = input_status(definition, project_root)
    if report.status != "uninspected":
        return report

    from .netcdf_metadata import MetadataInspectionError, inspect_netcdf_metadata

    try:
        path = resolve_local_input(project_root, definition.local_path or "")
        if _identity(path) != report.file_identity:
            raise ValueError("file_changed_during_inspection")
        if verify_checksum and definition.expected_md5:
            observed = calculate_md5(path)
            report = report.model_copy(update={"observed_md5": observed})
            if observed != definition.expected_md5:
                if _identity(path) != report.file_identity:
                    raise ValueError("file_changed_during_inspection")
                return report.model_copy(
                    update={
                        "status": "invalid",
                        "reason_code": "checksum_mismatch",
                        "checksum_status": "mismatch",
                    }
                )
            report = report.model_copy(update={"checksum_status": "verified"})
        elif verify_checksum:
            report = report.model_copy(update={"checksum_status": "not_provided"})

        metadata = inspect_netcdf_metadata(path)
        if _identity(path) != report.file_identity:
            raise ValueError("file_changed_during_inspection")
        candidate = report.model_copy(
            update={
                "status": "not_prepared",
                "reason_code": "metadata_inspected_only",
                "metadata": metadata,
            }
        )
        try:
            serialize_inspection_report(candidate, max_bytes=MAX_REPORT_BYTES)
        except ValueError:
            raise MetadataInspectionError(
                "metadata_limit_exceeded", "Wrapped report exceeds prototype limits."
            ) from None
        return candidate
    except RegistryError:
        return report.model_copy(
            update={"status": "invalid", "reason_code": "unsafe_local_path"}
        )
    except MetadataInspectionError as error:
        # A failed header read can itself be caused by an in-progress replacement.
        # Never retain a verified checksum for an input that changed/disappeared.
        try:
            if _identity(path) != report.file_identity:
                return _interrupted_report(report)
        except ValueError:
            return _interrupted_report(report)
        except OSError:
            return _interrupted_report(report, inaccessible=True)
        unsupported = error.code.startswith("unsupported") or "limit" in error.code
        status = "unsupported" if unsupported else "invalid"
        if error.code == "dependency_unavailable":
            status = "unavailable"
        return report.model_copy(
            update={
                "status": status,
                "reason_code": error.code,
            }
        )
    except ValueError:
        return _interrupted_report(report)
    except OSError:
        return _interrupted_report(report, inaccessible=True)
