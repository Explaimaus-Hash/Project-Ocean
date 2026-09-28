"""Source-registry and inspection contracts, distinct from data readiness."""

from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

DatasetStatus = Literal[
    "not_configured",
    "unavailable",
    "uninspected",
    "invalid",
    "unsupported",
    "not_prepared",
]

MAX_REPORT_BYTES = 2 * 1024 * 1024


class DatasetDefinition(BaseModel):
    """One configured input; published descriptions are not inspected metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    dataset_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,95}$")
    title: str = Field(min_length=1, max_length=256)
    role: Literal["model", "observation"]
    access_method: Literal[
        "local_netcdf", "opendap", "copernicusmarine", "argopy", "ftp"
    ]
    origin_url: str = Field(max_length=2048)
    version: str | None = Field(default=None, max_length=128)
    local_path: str | None = Field(default=None, max_length=512)
    expected_md5: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    published_notes: str = Field(default="", max_length=4096)

    @field_validator("origin_url")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "ftp"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Use a public HTTPS/FTP origin without credentials or query"
            )
        return value

    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        posix = PurePosixPath(value.replace("\\", "/"))
        windows = PureWindowsPath(value)
        if (
            posix.is_absolute()
            or windows.drive
            or windows.root
            or ".." in posix.parts
            or posix.parts[:2] != ("data", "raw")
            or posix.suffix.lower() != ".nc"
            or ":" in value
            or "\x00" in value
        ):
            raise ValueError("Local inputs must be .nc files below project data/raw")
        return posix.as_posix()

    @model_validator(mode="after")
    def consistent_local_definition(self) -> "DatasetDefinition":
        if self.access_method == "local_netcdf" and self.local_path is None:
            raise ValueError("Local NetCDF input requires local_path")
        if self.access_method != "local_netcdf" and (
            self.local_path is not None or self.expected_md5 is not None
        ):
            raise ValueError("Only local inputs accept local_path and expected_md5")
        return self


class SourceRegistry(BaseModel):
    """Versioned registry with unique identities and bounded entries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    datasets: list[DatasetDefinition] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_dataset_ids(self) -> "SourceRegistry":
        ids = [entry.dataset_id for entry in self.datasets]
        if len(ids) != len(set(ids)):
            raise ValueError("Dataset IDs must be unique")
        return self


class FileIdentity(BaseModel):
    """Stat identity checked before/after inspection; not a content checksum."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    size_bytes: int = Field(ge=0)
    modified_ns: int


class InspectionReport(BaseModel):
    """Recorded local findings; this contract never advertises ready data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    inspector_version: Literal["0.1.0"] = "0.1.0"
    source_id: str
    dataset_id: str
    source_version: str | None = None
    origin_url: str
    checked_at: datetime
    status: DatasetStatus
    reason_code: str
    local_path: str | None = None
    file_identity: FileIdentity | None = None
    expected_md5: str | None = None
    observed_md5: str | None = None
    checksum_status: Literal["not_checked", "verified", "mismatch", "not_provided"] = (
        "not_checked"
    )
    metadata: dict[str, JsonValue] | None = None
    prepared: Literal[False] = False


def serialize_inspection_report(
    report: InspectionReport, *, max_bytes: int = MAX_REPORT_BYTES
) -> bytes:
    """Apply one wrapped-report byte budget for inspection and publication."""
    payload = report.model_dump_json(indent=2).encode("utf-8") + b"\n"
    if len(payload) > max_bytes:
        raise ValueError("Inspection report exceeds the size limit")
    return payload
