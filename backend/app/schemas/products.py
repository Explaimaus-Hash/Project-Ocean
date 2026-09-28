"""Versioned, bounded contracts for prepared surface products, not comparisons."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,95}$")]
VariableName = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]
PROCESSING_VERSION = "surface_1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Region(Contract):
    west: FiniteFloat = Field(ge=-180, lt=180)
    east: FiniteFloat = Field(gt=-180, le=180)
    south: FiniteFloat = Field(ge=-90, le=90)
    north: FiniteFloat = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def ordered(self) -> "Region":
        if self.west >= self.east or self.south >= self.north:
            raise ValueError("Bounds must increase; dateline wrapping is unsupported")
        return self


class PreparationRequest(Contract):
    dataset_id: Identifier = "incois_bio_roms_v2"
    variables: list[VariableName] = Field(min_length=1, max_length=4)
    region: Region
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def bounded_selection(self) -> "PreparationRequest":
        if self.end_date < self.start_date:
            raise ValueError("Dates must increase")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("At most 366 days per operator preparation")
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("Variables must be unique")
        return self


class PerformanceLimits(Contract):
    schema_version: Literal[1] = 1
    max_axis_values: int = Field(default=10000, ge=1, le=10000)
    max_time_steps: int = Field(default=12, ge=1, le=12)
    max_preparation_values: int = Field(default=8000000, ge=1, le=8000000)
    max_source_chunk_bytes: int = Field(default=33554432, ge=1024, le=33554432)
    netcdf_cache_bytes: int = Field(default=16777216, ge=1024, le=16777216)
    max_preview_cells: int = Field(default=16384, ge=1, le=16384)
    max_scientific_frame_cells: int = Field(default=65536, ge=1, le=65536)
    max_response_bytes: int = Field(default=2097152, ge=1024, le=2097152)
    max_manifest_bytes: int = Field(default=524288, ge=1024, le=524288)
    max_product_file_bytes: int = Field(default=134217728, ge=1024, le=134217728)
    max_products: int = Field(default=64, ge=1, le=128)


class VariableInfo(Contract):
    source_name: VariableName
    units: str = Field(min_length=1, max_length=128)
    long_name: str = Field(max_length=512)
    standard_name: str = Field(default="", max_length=512)
    cell_methods: str = Field(default="not_declared", max_length=512)
    source_dtype: str = Field(max_length=64)
    # These units/names are preserved verbatim, not converted semantic quantities.
    scientific_definition: Literal["source_definition_not_harmonized"] = (
        "source_definition_not_harmonized"
    )


class ProductFile(Contract):
    size_bytes: int = Field(gt=0, le=134217728)
    modified_ns: int
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class Capabilities(Contract):
    surface: Literal[True] = True
    timeseries: Literal[True] = True
    depth_profiles: Literal[False] = False
    volume: Literal[False] = False
    currents: Literal[False] = False
    comparison_ready: Literal[False] = False


class ProductManifest(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["surface_1"] = PROCESSING_VERSION
    product_id: Identifier
    source_id: Identifier
    dataset_id: Identifier
    source_version: str = Field(max_length=128)
    origin_url: str = Field(max_length=2048)
    input_md5: str = Field(pattern=r"^[a-f0-9]{32}$")
    input_size_bytes: int = Field(gt=0)
    input_modified_ns: int
    created_at: datetime
    selection: PreparationRequest
    data_mode: Literal["real", "synthetic"]
    variables: dict[VariableName, VariableInfo] = Field(min_length=1, max_length=4)
    latitude: list[FiniteFloat] = Field(min_length=1, max_length=10000)
    longitude: list[FiniteFloat] = Field(min_length=1, max_length=10000)
    times: list[str] = Field(min_length=1, max_length=12)
    time_units: str = Field(max_length=256)
    calendar: Literal["standard", "gregorian", "proleptic_gregorian"]
    preview_stride: int = Field(ge=1, le=10000)
    scientific_file: ProductFile
    preview_file: ProductFile
    capabilities: Capabilities = Field(default_factory=Capabilities)
    qc_policy: Literal["source_mask_and_nonfinite_only"] = (
        "source_mask_and_nonfinite_only"
    )
    temporal_support: Literal["source_timestamps_no_inferred_bounds"] = (
        "source_timestamps_no_inferred_bounds"
    )

    @model_validator(mode="after")
    def consistent(self) -> "ProductManifest":
        if self.dataset_id != self.selection.dataset_id:
            raise ValueError("Dataset identities differ")
        if set(self.variables) != set(self.selection.variables):
            raise ValueError("Variable selection differs")
        if any(name != info.source_name for name, info in self.variables.items()):
            raise ValueError("Source variable identities differ")
        for values, lower, upper in (
            (self.latitude, -90, 90),
            (self.longitude, -180, 180),
        ):
            if any(v < lower or v > upper for v in values):
                raise ValueError("Coordinates outside geographic range")
            if any(a >= b for a, b in zip(values, values[1:], strict=False)):
                raise ValueError("Coordinates must strictly increase")
        if any(v >= 180 for v in self.longitude):
            raise ValueError("Longitude must remain below 180")
        region = self.selection.region
        if not (
            region.south <= self.latitude[0] <= self.latitude[-1] <= region.north
            and region.west <= self.longitude[0] <= self.longitude[-1] <= region.east
        ):
            raise ValueError("Prepared coordinates exceed the requested selection")
        parsed = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in self.times]
        if any(t.tzinfo is None or t.utcoffset().total_seconds() != 0 for t in parsed):
            raise ValueError("Times must have an explicit UTC offset")
        if any(a >= b for a, b in zip(parsed, parsed[1:], strict=False)):
            raise ValueError("Times must strictly increase")
        if any(
            not self.selection.start_date <= t.date() <= self.selection.end_date
            for t in parsed
        ):
            raise ValueError("Prepared times exceed the requested selection")
        return self
