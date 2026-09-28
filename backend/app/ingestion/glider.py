"""One explicit IFREMER EGO glider file; FTP cannot geographically subset it."""

from ftplib import FTP
from pathlib import Path
from typing import Any

from ..schemas.acquisition import AcquisitionRequest
from ..schemas.datasets import DatasetDefinition
from .base import SOCKET_TIMEOUT, fail, validate_raw


def fetch(
    request: AcquisitionRequest, definition: DatasetDefinition, destination: Path
) -> dict[str, Any]:
    assert request.remote_path is not None
    transferred = 0
    with FTP(timeout=SOCKET_TIMEOUT) as ftp:
        ftp.connect("ftp.ifremer.fr", timeout=SOCKET_TIMEOUT)
        ftp.login("anonymous", "project-ocean@example.invalid")
        ftp.voidcmd("TYPE I")
        expected = ftp.size(request.remote_path)
        if expected is None or not 0 < expected <= request.max_bytes:
            raise fail("acquisition_limit")
        with destination.open("xb") as stream:

            def consume(block: bytes) -> None:
                nonlocal transferred
                transferred += len(block)
                if transferred > request.max_bytes or transferred > expected:
                    raise fail("acquisition_limit")
                stream.write(block)

            ftp.retrbinary(f"RETR {request.remote_path}", consume, blocksize=65536)
        if transferred != expected or ftp.size(request.remote_path) != expected:
            raise fail("input_changed")
    validate_raw(destination, request)
    return {
        "client": "Python ftplib",
        "client_version": "stdlib",
        "client_processing": (
            "Original single deployment NetCDF unchanged; no geographic/time/sensor "
            "filtering. FTP is unencrypted; SHA256 identifies local bytes, not an "
            "authenticated provider checksum."
        ),
        "transport": "ftp",
        "original_filename": Path(request.remote_path).name,
    }
