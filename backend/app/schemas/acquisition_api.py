"""Public acquisition inventory excludes operator input paths and private stats."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from .acquisition import SourceSelection
from .product_api import VersionedResponse
from .products import Contract, Identifier, VariableName


class PublicAcquisition(Contract):
    acquisition_id: Annotated[str, Field(pattern=r"^a_[a-f0-9]{24}$")]
    dataset_id: Identifier
    source_id: Identifier
    origin_url: str = Field(max_length=2048)
    source_version: str | None = Field(max_length=128)
    provider: Literal["godas", "copernicus", "argo", "glider", "local"]
    provider_dataset_id: str | None = Field(max_length=128)
    selection: SourceSelection | None
    variables: list[VariableName] = Field(max_length=4)
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    size_bytes: int = Field(gt=0, le=134217728)
    retrieved_at: datetime | None
    data_mode: Literal["real", "synthetic"]
    status: Literal["acquired_not_prepared"]
    client: str = Field(max_length=128)
    client_version: str = Field(max_length=64)
    client_processing: str = Field(max_length=2048)
    transport: Literal["https", "ftp", "local"]
    comparison_ready: Literal[False]


class AcquisitionCatalogueResponse(VersionedResponse):
    scope: Literal["locally_available_acquisitions_not_live_access"]
    acquisitions: list[PublicAcquisition] = Field(max_length=64)
