"""Safe local product helpers; no filesystem or scientific work at import."""

import hashlib
import json
import stat
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..schemas.products import PerformanceLimits, ProductFile


class ProductError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def contained(root: Path, relative: str) -> Path:
    resolved = root.resolve()
    target = (resolved / relative).resolve()
    if not target.is_relative_to(resolved) or target == resolved:
        raise ProductError("unsafe_product_path", "Product path is unsafe.")
    return target


def read_json(path: Path, max_bytes: int) -> Any:
    try:
        with path.open("rb") as stream:
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ProductError("metadata_limit", "Product metadata exceeds limits.")
        return json.loads(content)
    except (OSError, ValueError, RecursionError):
        raise ProductError(
            "not_prepared", "Prepared metadata is unavailable."
        ) from None


def load_limits(root: Path) -> PerformanceLimits:
    import yaml

    try:
        with (root / "config" / "performance.yaml").open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise ValueError("oversized configuration")
        return PerformanceLimits.model_validate(yaml.safe_load(raw))
    except (OSError, ValueError, yaml.YAMLError, ValidationError):
        raise ProductError(
            "configuration_unavailable", "Local limits are invalid.", 503
        ) from None


def stat_file(
    path: Path, max_bytes: int, *, check_access: bool = False
) -> tuple[int, int]:
    try:
        info = path.stat()
        if (
            not stat.S_ISREG(info.st_mode)
            or not 0 < info.st_size <= max_bytes
            or getattr(info, "st_file_attributes", 0) & (0x1000 | 0x40000 | 0x400000)
        ):
            raise ValueError("not a bounded local file")
        if check_access:
            # An ordinary byte-access check, not NetCDF parsing or scientific I/O.
            with path.open("rb") as stream:
                if not stream.read(1):
                    raise ValueError("empty file")
        return info.st_size, info.st_mtime_ns
    except (OSError, ValueError):
        raise ProductError(
            "product_unavailable", "Prepared file is unavailable."
        ) from None


def describe_file(path: Path, max_bytes: int) -> ProductFile:
    before = stat_file(path, max_bytes)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    if stat_file(path, max_bytes) != before:
        raise ProductError("product_changed", "Prepared file changed.")
    return ProductFile(
        size_bytes=before[0], modified_ns=before[1], sha256=digest.hexdigest()
    )
