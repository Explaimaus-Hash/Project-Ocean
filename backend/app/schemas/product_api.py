"""Public, versioned surface-product contracts with no private storage fields."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, FiniteFloat, model_validator

from .products import (
    Capabilities,
    Contract,
    Identifier,
    PreparationRequest,
    Region,
    VariableInfo,
    VariableName,
)


def utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamps must explicitly use UTC")
    return value


UtcTimestamp = Annotated[str, Field(max_length=40), AfterValidator(utc_timestamp)]
LongitudeValue = Annotated[FiniteFloat, Field(ge=-180, lt=180)]
LatitudeValue = Annotated[FiniteFloat, Field(ge=-90, le=90)]
Code = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,95}$")]


def ordered_axis(values: list[float]) -> list[float]:
    if any(a >= b for a, b in zip(values, values[1:], strict=False)):
        raise ValueError("Coordinates must strictly increase")
    return values


LatitudeAxis = Annotated[
    list[LatitudeValue],
    Field(min_length=1, max_length=10000),
    AfterValidator(ordered_axis),
]
LongitudeAxis = Annotated[
    list[LongitudeValue],
    Field(min_length=1, max_length=10000),
    AfterValidator(ordered_axis),
]


def ordered_times(values: list[str]) -> list[str]:
    parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in values]
    if any(a >= b for a, b in zip(parsed, parsed[1:], strict=False)):
        raise ValueError("Times must strictly increase")
    return values


TimeAxis = Annotated[
    list[UtcTimestamp],
    Field(min_length=1, max_length=12),
    AfterValidator(ordered_times),
]


class VersionedResponse(Contract):
    schema_version: Literal[1]


class PublicError(Contract):
    code: Code
    message: str = Field(min_length=1, max_length=512)


class ErrorResponse(VersionedResponse):
    error: PublicError


class DatasetSummary(Contract):
    source_id: Identifier
    dataset_id: Identifier
    title: str = Field(min_length=1, max_length=256)
    role: Literal["model", "observation"]
    origin_url: str = Field(min_length=1, max_length=2048)
    status: Literal["ready", "not_prepared", "not_configured"]
    reason_code: Literal[
        "prepared_selection_available", "no_prepared_product", "adapter_not_implemented"
    ]
    product_ids: list[Identifier] = Field(max_length=128)

    @model_validator(mode="after")
    def consistent_status(self) -> "DatasetSummary":
        expected = {
            "ready": "prepared_selection_available",
            "not_prepared": "no_prepared_product",
            "not_configured": "adapter_not_implemented",
        }
        if self.reason_code != expected[self.status]:
            raise ValueError("Dataset status and reason differ")
        if (self.status == "ready") != bool(self.product_ids):
            raise ValueError("Dataset status and available products differ")
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("Product identifiers must be unique")
        return self


class ReadyProductSummary(Contract):
    product_id: Identifier
    dataset_id: Identifier
    status: Literal["ready"]
    data_mode: Literal["real", "synthetic"]
    variables: list[VariableName] = Field(min_length=1, max_length=4)
    times: TimeAxis
    capabilities: Capabilities
    region: Region | None = None


class UnpreparedProductSummary(Contract):
    product_id: Identifier
    status: Literal["not_prepared"]
    reason_code: Code


ProductSummary = Annotated[
    ReadyProductSummary | UnpreparedProductSummary, Field(discriminator="status")
]


class CatalogueResponse(VersionedResponse):
    datasets: list[DatasetSummary] = Field(min_length=1, max_length=100)
    products: list[ProductSummary] = Field(max_length=128)

    @model_validator(mode="after")
    def consistent_products(self) -> "CatalogueResponse":
        dataset_ids = {item.dataset_id for item in self.datasets}
        product_ids = {item.product_id for item in self.products}
        if len(dataset_ids) != len(self.datasets) or len(product_ids) != len(
            self.products
        ):
            raise ValueError("Catalogue identifiers must be unique")
        ready_products = {
            item.product_id: item
            for item in self.products
            if isinstance(item, ReadyProductSummary)
        }
        for item in ready_products.values():
            if item.dataset_id not in dataset_ids:
                raise ValueError("Prepared product dataset is not registered")
        for item in self.datasets:
            expected = {
                product_id
                for product_id, product in ready_products.items()
                if product.dataset_id == item.dataset_id
            }
            if set(item.product_ids) != expected:
                raise ValueError("Catalogue source/product links differ")
        return self


class MetadataResponse(VersionedResponse):
    """Safe public manifest; raw paths/file descriptors are deliberately absent."""

    processing_version: Literal["surface_1"]
    product_id: Identifier
    source_id: Identifier
    dataset_id: Identifier
    source_version: str = Field(max_length=128)
    origin_url: str = Field(max_length=2048)
    input_md5: str = Field(pattern=r"^[a-f0-9]{32}$")
    input_size_bytes: int = Field(gt=0)
    created_at: datetime
    selection: PreparationRequest
    data_mode: Literal["real", "synthetic"]
    variables: dict[VariableName, VariableInfo] = Field(min_length=1, max_length=4)
    latitude: LatitudeAxis
    longitude: LongitudeAxis
    times: TimeAxis
    time_units: str = Field(max_length=256)
    calendar: Literal["standard", "gregorian", "proleptic_gregorian"]
    preview_stride: int = Field(ge=1, le=10000)
    capabilities: Capabilities
    qc_policy: Literal["source_mask_and_nonfinite_only"]
    temporal_support: Literal["source_timestamps_no_inferred_bounds"]
    status: Literal["ready"]
    ready_scope: Literal["prepared_surface_selection"]

    @model_validator(mode="after")
    def consistent_selection(self) -> "MetadataResponse":
        if self.dataset_id != self.selection.dataset_id:
            raise ValueError("Dataset identities differ")
        if set(self.variables) != set(self.selection.variables):
            raise ValueError("Variable selection differs")
        if any(name != info.source_name for name, info in self.variables.items()):
            raise ValueError("Variable definitions differ")
        if (
            len(self.latitude)
            * len(self.longitude)
            * len(self.times)
            * len(self.variables)
            > 8000000
        ):
            raise ValueError("Prepared scientific selection exceeds limits")
        preview_cells = len(self.latitude[:: self.preview_stride]) * len(
            self.longitude[:: self.preview_stride]
        )
        if preview_cells > 16384:
            raise ValueError("Prepared preview exceeds limits")
        return self


class ScientificResponse(VersionedResponse):
    product_id: Identifier
    dataset_id: Identifier
    source_id: Identifier
    source_version: str = Field(max_length=128)
    input_md5: str = Field(pattern=r"^[a-f0-9]{32}$")
    processing_version: Literal["surface_1"]
    data_mode: Literal["real", "synthetic"]
    variable: VariableName
    units: str = Field(min_length=1, max_length=128)
    variable_metadata: VariableInfo
    qc_policy: Literal["source_mask_and_nonfinite_only"]
    temporal_support: Literal["source_timestamps_no_inferred_bounds"]
    vertical_reference: Literal["source_surface_product_no_numeric_depth_assigned"]
    missing_value: None

    @model_validator(mode="after")
    def consistent_variable(self) -> "ScientificResponse":
        if self.variable != self.variable_metadata.source_name:
            raise ValueError("Variable identity differs from metadata")
        if self.units != self.variable_metadata.units:
            raise ValueError("Variable units differ from metadata")
        return self


MatrixRow = Annotated[list[FiniteFloat | None], Field(min_length=1, max_length=10000)]


class FrameResponse(ScientificResponse):
    quality: Literal["preview", "scientific"]
    display_only: bool
    sampling: Literal[
        "strided_source_cells_no_interpolation", "scientific_source_cells"
    ]
    stride: int = Field(ge=1, le=10000)
    dimensions: tuple[Literal["latitude"], Literal["longitude"]]
    shape: tuple[
        Annotated[int, Field(ge=1, le=10000)], Annotated[int, Field(ge=1, le=10000)]
    ]
    time_index: int = Field(ge=0, lt=12)
    time: UtcTimestamp
    latitude: LatitudeAxis
    longitude: LongitudeAxis
    values: list[MatrixRow] = Field(min_length=1, max_length=10000)
    valid_count: int = Field(ge=0, le=65536)
    missing_count: int = Field(ge=0, le=65536)
    requested_region: Region | None

    @model_validator(mode="before")
    @classmethod
    def bounded_matrix(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(value.get("values"), list):
            rows = value["values"]
            if len(rows) > 10000:
                raise ValueError("Frame row limit exceeded")
            count = sum(len(row) for row in rows if isinstance(row, list))
            limit = 16384 if value.get("quality") == "preview" else 65536
            if count > limit:
                raise ValueError("Frame cell limit exceeded")
        return value

    @model_validator(mode="after")
    def consistent_frame(self) -> "FrameResponse":
        ny, nx = self.shape
        cells = ny * nx
        if (ny, nx) != (len(self.latitude), len(self.longitude)):
            raise ValueError("Frame shape differs from axes")
        if len(self.values) != ny or any(len(row) != nx for row in self.values):
            raise ValueError("Frame values differ from shape")
        is_preview = self.quality == "preview"
        if cells > (16384 if is_preview else 65536):
            raise ValueError("Frame cell limit exceeded")
        if self.display_only != is_preview:
            raise ValueError("Display/scientific labels differ")
        sampling = (
            "strided_source_cells_no_interpolation"
            if is_preview
            else "scientific_source_cells"
        )
        if self.sampling != sampling or (not is_preview and self.stride != 1):
            raise ValueError("Sampling policy differs from quality")
        valid = sum(value is not None for row in self.values for value in row)
        if (self.valid_count, self.missing_count) != (valid, cells - valid):
            raise ValueError("Missing/value counts differ")
        if self.requested_region is not None:
            region = self.requested_region
            if not (
                region.west <= self.longitude[0] <= self.longitude[-1] <= region.east
                and region.south
                <= self.latitude[0]
                <= self.latitude[-1]
                <= region.north
            ):
                raise ValueError("Frame coordinates are outside requested bounds")
        return self


class Point(Contract):
    longitude: LongitudeValue
    latitude: LatitudeValue


class PointIndices(Contract):
    latitude: int = Field(ge=0, lt=10000)
    longitude: int = Field(ge=0, lt=10000)


class TimeseriesResponse(ScientificResponse):
    times: TimeAxis
    values: list[FiniteFloat | None] = Field(min_length=1, max_length=12)
    requested_point: Point
    sample_point: Point
    sample_indices: PointIndices
    distance_m: FiniteFloat = Field(ge=0, le=20100000)
    sampling: Literal["nearest_axis_grid_cell_no_wet_cell_search"]
    display_only: Literal[False]
    comparison_result: Literal[False]

    @model_validator(mode="after")
    def aligned_times(self) -> "TimeseriesResponse":
        if len(self.times) != len(self.values):
            raise ValueError("Time/value lengths differ")
        return self


class ReadinessCheck(Contract):
    product_id: Identifier
    status: Literal["ready", "not_ready"]
    reason_code: Code


class ReadinessResponse(VersionedResponse):
    status: Literal["ready", "not_ready"]
    reason_code: Code | None = None
    checks: list[ReadinessCheck] = Field(max_length=16)

    @model_validator(mode="after")
    def consistent_readiness(self) -> "ReadinessResponse":
        if len({item.product_id for item in self.checks}) != len(self.checks):
            raise ValueError("Readiness checks must have unique identifiers")
        if self.status == "ready" and (
            not self.checks
            or self.reason_code is not None
            or any(item.status != "ready" for item in self.checks)
        ):
            raise ValueError("Ready response requires passing configured products")
        return self
