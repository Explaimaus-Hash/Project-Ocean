"""Atomic bounded inspection-report storage, separate from raw downloads."""

import os
import tempfile
from pathlib import Path

from ..schemas.datasets import (
    MAX_REPORT_BYTES,
    InspectionReport,
    serialize_inspection_report,
)


def save_inspection_report(report: InspectionReport, project_root: Path) -> Path:
    """Publish a report only on explicit operator request, never from /health."""
    if (
        not report.dataset_id
        or len(report.dataset_id) > 96
        or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
            for character in report.dataset_id
        )
    ):
        raise ValueError("Invalid report dataset ID")
    root = project_root.resolve()
    data_root = (root / "data").resolve()
    directory = (data_root / "metadata").resolve()
    if not data_root.is_relative_to(root) or not directory.is_relative_to(data_root):
        raise ValueError("Report directory must stay inside project data")
    destination = directory / f"{report.dataset_id}.json"
    if destination.is_symlink() or not destination.resolve().is_relative_to(directory):
        raise ValueError("Unsafe report destination")
    payload = serialize_inspection_report(report, max_bytes=MAX_REPORT_BYTES)
    directory.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=directory, prefix=".inspection-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
