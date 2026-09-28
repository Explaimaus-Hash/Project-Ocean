"""Public observation metadata/pages; private byte identities never cross HTTP."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .observations import (
    ObservationCapabilities,
    ObservationCounts,
    ObservationRequest,
    ObservationSample,
    ObservationVariable,
    ObservationVariableInfo,
    ShortText,
)
from .product_api import Code, VersionedResponse
from .products import Contract, Identifier, ProductFile

CollectionId = Annotated[str, Field(pattern=r"^o_[a-f0-9]{24}$")]
ProfileId = Annotated[str, Field(pattern=r"^r_[a-f0-9]{24}$")]


class ObservationMetadataResponse(VersionedResponse):
    processing_version: Literal["observations_1"]
    collection_id: CollectionId
    source_id: Literal["argo", "ifremer_glider"]
    dataset_id: Identifier
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    data_mode: Literal["real", "synthetic"]
    client_processing: Literal[
        "local_operator_input_client_processing_unknown", "argopy_expert_no_qc_filter"
    ]
    selection: ObservationRequest
    layout: Literal["argo_profiles", "argo_points", "ego_timeseries"]
    source_time_name: Literal["JULD", "TIME"]
    source_time_units: ShortText
    source_time_calendar: ShortText
    variables: dict[ObservationVariable, ObservationVariableInfo] = Field(
        min_length=1, max_length=5
    )
    counts: ObservationCounts
    capabilities: ObservationCapabilities
    qc_policy: Literal["core_flags_1_2_no_fallback_v1"]
    warnings: list[ShortText] = Field(max_length=16)

    @model_validator(mode="after")
    def consistent_metadata(self) -> "ObservationMetadataResponse":
        if set(self.variables) != set(self.selection.variables):
            raise ValueError("Observation variables differ from selection")
        for key, info in self.variables.items():
            if key != info.source_name:
                raise ValueError("Observation variable identity differs")
        return self


class ObservationManifest(Contract):
    schema_version: Literal[1]
    created_at: datetime
    metadata: ObservationMetadataResponse
    collection_file: ProductFile


class ReadyObservationSummary(Contract):
    collection_id: CollectionId
    status: Literal["ready"]
    metadata: ObservationMetadataResponse

    @model_validator(mode="after")
    def consistent_identity(self) -> "ReadyObservationSummary":
        if self.collection_id != self.metadata.collection_id:
            raise ValueError("Collection identities differ")
        return self


class UnpreparedObservationSummary(Contract):
    collection_id: CollectionId
    status: Literal["not_prepared"]
    reason_code: Code


class ObservationCatalogueResponse(VersionedResponse):
    collections: list[
        Annotated[
            ReadyObservationSummary | UnpreparedObservationSummary,
            Field(discriminator="status"),
        ]
    ] = Field(max_length=32)

    @model_validator(mode="after")
    def unique_collections(self) -> "ObservationCatalogueResponse":
        if len({item.collection_id for item in self.collections}) != len(
            self.collections
        ):
            raise ValueError("Collection identifiers must be unique")
        return self


class ObservationPageResponse(VersionedResponse):
    collection_id: CollectionId
    source_id: Literal["argo", "ifremer_glider"]
    dataset_id: Identifier
    data_mode: Literal["real", "synthetic"]
    display_only: Literal[False]
    comparison_result: Literal[False]
    profile_id: ProfileId | None
    offset: int = Field(ge=0, le=5000)
    limit: int = Field(ge=1, le=500)
    total: int = Field(ge=0, le=5000)
    next_offset: int | None = Field(ge=0, le=5000)
    samples: list[ObservationSample] = Field(max_length=500)

    @model_validator(mode="after")
    def consistent_page(self) -> "ObservationPageResponse":
        expected_count = min(self.limit, max(0, self.total - self.offset))
        if len(self.samples) != expected_count:
            raise ValueError("Observation page counts differ")
        expected_next = (
            self.offset + expected_count
            if self.offset + expected_count < self.total
            else None
        )
        if self.next_offset != expected_next:
            raise ValueError("Observation next page differs")
        if self.profile_id is not None and any(
            sample.profile_id != self.profile_id for sample in self.samples
        ):
            raise ValueError("Observation profile differs")
        if len({sample.sample_id for sample in self.samples}) != len(self.samples):
            raise ValueError("Sample identifiers must be unique")
        return self
