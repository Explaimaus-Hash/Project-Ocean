"""Operator-only acquisition contracts; these are not HTTP upload requests."""

from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, FiniteFloat, field_validator, model_validator

from .products import Contract, Identifier, ProductFile, Region, VariableName

MAX_ACQUISITION_BYTES = 134_217_728
MAX_ACQUISITION_MANIFEST = 65_536
MAX_ACQUISITIONS = 64


class SourceSelection(Contract):
    region: Region
    start_time: datetime
    end_time: datetime
    vertical_min: FiniteFloat = Field(ge=0, le=12000)
    vertical_max: FiniteFloat = Field(ge=0, le=12000)
    vertical_kind: Literal["depth_m", "pressure_dbar"]

    @field_validator("start_time", "end_time")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Explicit UTC-aware timestamps are required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordered(self) -> "SourceSelection":
        if not 0 < (self.end_time - self.start_time).total_seconds() <= 31 * 86400:
            raise ValueError("Use an increasing interval of at most 31 days")
        if self.vertical_min > self.vertical_max:
            raise ValueError("Vertical bounds must increase")
        return self


class ModelCoordinates(Contract):
    longitude: VariableName
    latitude: VariableName
    time: VariableName
    depth: VariableName

    @model_validator(mode="after")
    def distinct(self) -> "ModelCoordinates":
        if len(set(self.model_dump().values())) != 4:
            raise ValueError("Coordinate names must be distinct")
        return self


class AcquisitionRequest(Contract):
    schema_version: Literal[1] = 1
    provider: Literal["godas", "copernicus", "argo", "glider", "local"]
    dataset_id: Identifier
    selection: SourceSelection | None = None
    variables: list[VariableName] = Field(default_factory=list, max_length=4)
    coordinates: ModelCoordinates | None = None
    provider_dataset_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$"
    )
    provider_version: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$"
    )
    remote_path: str | None = Field(default=None, max_length=512)
    local_path: str | None = Field(default=None, max_length=512)
    deadline_seconds: int = Field(default=90, ge=5, le=180)
    max_bytes: int = Field(default=67_108_864, ge=1024, le=MAX_ACQUISITION_BYTES)
    max_values: int = Field(default=2_000_000, ge=1, le=8_000_000)
    max_samples: int = Field(default=20_000, ge=1, le=100_000)

    @field_validator("local_path")
    @classmethod
    def local_raw_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        path = PurePosixPath(value)
        if (
            "\\" in value
            or ":" in value
            or "\x00" in value
            or path.is_absolute()
            or ".." in path.parts
            or path.parts[:2] != ("data", "raw")
            or path.suffix.lower() != ".nc"
        ):
            raise ValueError("Local input must be a relative data/raw NetCDF path")
        return value

    @field_validator("remote_path")
    @classmethod
    def glider_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        import re

        if not re.fullmatch(
            r"/ifremer/glider/v2/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.nc",
            value,
        ):
            raise ValueError("Select one explicit IFREMER v2 deployment NetCDF")
        return value

    @model_validator(mode="after")
    def provider_contract(self) -> "AcquisitionRequest":
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("Variables must be unique")
        if self.provider in {"godas", "copernicus"}:
            if not self.selection or not self.coordinates or not self.variables:
                raise ValueError(
                    "Model subset needs variables, selection and coordinates"
                )
            if self.selection.vertical_kind != "depth_m":
                raise ValueError("Model vertical selection is depth in metres")
        if self.provider == "copernicus" and (
            not self.provider_dataset_id or not self.provider_version
        ):
            raise ValueError("Select an inspected provider dataset ID and version")
        if self.provider == "copernicus" and self.provider_dataset_id not in {
            "cmems_mod_glo_phy_my_0.083deg_P1D-m",
            "cmems_mod_glo_phy_my_0.083deg_P1M-m",
        }:
            raise ValueError(
                "Only the documented GLOBAL_MULTIYEAR_PHY_001_030 grids are supported"
            )
        if self.provider == "argo" and (
            not self.selection or self.selection.vertical_kind != "pressure_dbar"
        ):
            raise ValueError("Argo requires region, time and sea-pressure selection")
        if self.provider == "glider" and not self.remote_path:
            raise ValueError("Glider requires one explicit file path")
        if self.provider == "local" and not self.local_path:
            raise ValueError("Local import requires one existing raw NetCDF")
        if self.provider in {"local", "glider"} and (
            self.selection or self.variables or self.coordinates
        ):
            raise ValueError(
                "File acquisition preserves the file; subset in preparation"
            )
        if self.provider == "argo" and (self.variables or self.coordinates):
            raise ValueError(
                "Core Argo expert acquisition retains all returned QC fields"
            )
        if self.provider != "local" and self.local_path is not None:
            raise ValueError("Local paths are only accepted by local import")
        if self.provider != "glider" and self.remote_path is not None:
            raise ValueError("Remote paths are only accepted by glider acquisition")
        if self.provider != "copernicus" and (
            self.provider_dataset_id is not None or self.provider_version is not None
        ):
            raise ValueError("Provider dataset/version fields are Copernicus-only")
        return self


class AcquisitionManifest(Contract):
    schema_version: Literal[1] = 1
    acquisition_version: Literal["acquisition_1"] = "acquisition_1"
    acquisition_id: Identifier
    dataset_id: Identifier
    source_id: Identifier
    origin_url: str = Field(max_length=2048)
    source_version: str | None = Field(default=None, max_length=128)
    request: AcquisitionRequest
    input_file: ProductFile
    provider_file: ProductFile | None = None
    original_filename: str | None = Field(default=None, max_length=256)
    created_at: datetime
    retrieved_at: datetime | None
    data_mode: Literal["real", "synthetic"] = "real"
    status: Literal["acquired_not_prepared"] = "acquired_not_prepared"
    client: str = Field(max_length=128)
    client_version: str = Field(max_length=64)
    client_processing: str = Field(max_length=2048)
    transport: Literal["https", "ftp", "local"]
    transfer_integrity: Literal["local_sha256_not_provider_signature"] = (
        "local_sha256_not_provider_signature"
    )
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def same_dataset(self) -> "AcquisitionManifest":
        if self.dataset_id != self.request.dataset_id:
            raise ValueError("Acquisition dataset identity mismatch")
        return self
