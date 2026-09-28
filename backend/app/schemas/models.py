"""Part-5.2 private model contracts; no reader, writer, API or comparison engine."""

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, field_validator, model_validator

from .acquisition import SourceSelection
from .products import Contract, Identifier, PerformanceLimits, ProductFile

AcquisitionId = Annotated[str, Field(pattern=r"^a_[a-f0-9]{24}$")]
ModelId = Annotated[str, Field(pattern=r"^m_[a-f0-9]{24}$")]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelVariable = Literal["thetao", "so", "uo", "vo"]
ShortText = Annotated[str, Field(min_length=1, max_length=512)]
Axis = Annotated[tuple[FiniteFloat, ...], Field(min_length=1, max_length=10000)]
Indices = Annotated[
    tuple[Annotated[int, Field(strict=True, ge=0)], ...],
    Field(min_length=1, max_length=10000),
]


def require_utc(value: datetime) -> datetime:
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("Explicit UTC timestamps are required")
    return value


class ModelPreparationRequest(Contract):
    """Select native centres in one existing, verified Copernicus acquisition."""

    schema_version: Literal[1] = 1
    acquisition_id: AcquisitionId
    variables: tuple[ModelVariable, ...] = Field(min_length=1, max_length=4)
    selection: SourceSelection

    @model_validator(mode="after")
    def supported(self) -> "ModelPreparationRequest":
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("Variables must be unique")
        if self.selection.vertical_kind != "depth_m":
            raise ValueError("Model selection uses metres, not pressure")
        return self


class ModelLimits(PerformanceLimits):
    """Existing prototype ceilings plus a bounded native-depth axis."""

    max_depth_levels: int = Field(default=64, strict=True, ge=1, le=64)


class ModelProvenance(Contract):
    acquisition_id: AcquisitionId
    acquisition_manifest_sha256: Sha256
    input_sha256: Sha256
    input_size_bytes: int = Field(strict=True, gt=0, le=134217728)
    source_id: Literal["copernicus"] = "copernicus"
    dataset_id: Identifier
    provider_dataset_id: Literal[
        "cmems_mod_glo_phy_my_0.083deg_P1D-m",
        "cmems_mod_glo_phy_my_0.083deg_P1M-m",
    ]
    source_version: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,128}$")]
    client: ShortText
    client_version: ShortText
    client_processing: Annotated[str, Field(min_length=1, max_length=2048)]
    retrieved_at: datetime | None
    data_mode: Literal["real", "synthetic"]
    metadata_authority: Literal["acquired_attributes_with_client_provenance"] = (
        "acquired_attributes_with_client_provenance"
    )

    @field_validator("retrieved_at")
    @classmethod
    def utc_retrieval(cls, value: datetime | None) -> datetime | None:
        return require_utc(value) if value is not None else None


class ModelAxes(Contract):
    """Actual centres, not requested bounds or inherited global coverage."""

    dimensions: Literal["time,depth,latitude,longitude"] = (
        "time,depth,latitude,longitude"
    )
    times: tuple[datetime, ...] = Field(min_length=1, max_length=12)
    depth_m: Annotated[tuple[FiniteFloat, ...], Field(min_length=1, max_length=64)]
    latitude: Axis
    longitude: Axis
    source_time_indices: Indices
    source_depth_indices: Indices
    source_latitude_indices: Indices
    source_longitude_indices: Indices
    source_time_units: ShortText
    calendar: Literal["standard", "gregorian", "proleptic_gregorian"]
    depth_units: Literal["m"] = "m"
    depth_positive: Literal["down"] = "down"
    vertical_reference: Literal["source_depth_reference_not_harmonized"] = (
        "source_depth_reference_not_harmonized"
    )

    @model_validator(mode="after")
    def native_axes(self) -> "ModelAxes":
        for value in self.times:
            require_utc(value)
        for values, indices in (
            (self.times, self.source_time_indices),
            (self.depth_m, self.source_depth_indices),
            (self.latitude, self.source_latitude_indices),
            (self.longitude, self.source_longitude_indices),
        ):
            if len(values) != len(indices):
                raise ValueError("Axis and source-index lengths differ")
            if any(a >= b for a, b in zip(values, values[1:], strict=False)):
                raise ValueError("Native axes must strictly increase")
            if any(b != a + 1 for a, b in zip(indices, indices[1:], strict=False)):
                raise ValueError("Source indices must be contiguous; no decimation")
        if any(not 0 <= v <= 12000 for v in self.depth_m):
            raise ValueError("Depth centres outside supported range")
        if any(not -90 <= v <= 90 for v in self.latitude):
            raise ValueError("Latitude outside geographic range")
        if any(not -180 <= v < 180 for v in self.longitude):
            raise ValueError("Longitude outside canonical range")
        return self


class ModelVariableInfo(Contract):
    source_name: ModelVariable
    units: ShortText
    standard_name: ShortText
    long_name: ShortText
    source_dtype: ShortText
    cell_methods: ShortText
    unit_long: ShortText | None
    definition_status: Literal["source_definition_not_harmonized"] = (
        "source_definition_not_harmonized"
    )
    temperature_scale: Literal["unresolved", "not_applicable"]
    reference_pressure_dbar: None = None

    @model_validator(mode="after")
    def temperature_gate(self) -> "ModelVariableInfo":
        expected = "unresolved" if self.source_name == "thetao" else "not_applicable"
        if self.temperature_scale != expected:
            raise ValueError("Temperature-scale evidence cannot be inferred")
        return self


class ModelScientificPolicy(Contract):
    """Known unknowns are mandatory, not a comparison-ready Boolean switch."""

    sampling: Literal["native_centres_no_interpolation"] = (
        "native_centres_no_interpolation"
    )
    output_dtype: Literal["float64"] = "float64"
    mask_policy: Literal["source_packing_range_fill_and_nonfinite_v1"] = (
        "source_packing_range_fill_and_nonfinite_v1"
    )
    temporal_support: Literal["source_labels_averaging_window_unresolved"] = (
        "source_labels_averaging_window_unresolved"
    )
    wet_domain: Literal["per_variable_masks_not_bathymetry_or_connectivity"] = (
        "per_variable_masks_not_bathymetry_or_connectivity"
    )
    vector_status: Literal["source_components_not_render_verified"] = (
        "source_components_not_render_verified"
    )
    metadata_coverage: Literal["actual_axes_not_inherited_globals"] = (
        "actual_axes_not_inherited_globals"
    )
    comparison_ready: Literal[False] = False
    api_serving: Literal[False] = False
    display_only: Literal[False] = False


class ModelIdentity(Contract):
    """Deterministic, immutable scientific identity; no output stat or clock."""

    schema_version: Literal[1] = 1
    processing_version: Literal["model_native_1"] = "model_native_1"
    request: ModelPreparationRequest
    provenance: ModelProvenance
    axes: ModelAxes
    variables: tuple[ModelVariableInfo, ...] = Field(min_length=1, max_length=4)
    limits: ModelLimits = Field(default_factory=ModelLimits)
    policy: ModelScientificPolicy = Field(default_factory=ModelScientificPolicy)

    @model_validator(mode="after")
    def bounded_identity(self) -> "ModelIdentity":
        if self.request.acquisition_id != self.provenance.acquisition_id:
            raise ValueError("Acquisition identities differ")
        if tuple(v.source_name for v in self.variables) != self.request.variables:
            raise ValueError("Variable identities/order differ from selection")
        axes, limits, selection = self.axes, self.limits, self.request.selection
        if (
            len(axes.times) > limits.max_time_steps
            or len(axes.depth_m) > limits.max_depth_levels
            or max(len(axes.latitude), len(axes.longitude)) > limits.max_axis_values
        ):
            raise ValueError("Axis budget exceeded")
        count = (
            len(axes.times)
            * len(axes.depth_m)
            * len(axes.latitude)
            * len(axes.longitude)
            * len(self.variables)
        )
        if count > limits.max_preparation_values:
            raise ValueError("Selected scalar-value budget exceeded")
        region = selection.region
        if not (
            selection.start_time
            <= axes.times[0]
            <= axes.times[-1]
            <= selection.end_time
            and selection.vertical_min
            <= axes.depth_m[0]
            <= axes.depth_m[-1]
            <= selection.vertical_max
            and region.south <= axes.latitude[0] <= axes.latitude[-1] <= region.north
            and region.west <= axes.longitude[0] <= axes.longitude[-1] <= region.east
        ):
            raise ValueError("Actual centres exceed the requested selection")
        return self

    def model_id(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return "m_" + hashlib.sha256(canonical).hexdigest()[:24]


class ModelManifest(Contract):
    """Future publication marker, NOT proof that a schema instance exists on disk."""

    schema_version: Literal[1] = 1
    model_id: ModelId
    identity: ModelIdentity
    created_at: datetime
    status: Literal["prepared_native_not_comparison_ready"] = (
        "prepared_native_not_comparison_ready"
    )
    scientific_file: ProductFile
    source_metadata_file: ProductFile
    # Metadata is a separate bounded JSON snapshot; never active packing on float64.
    storage_layout: Literal["private_models_fields_and_source_metadata_v1"] = (
        "private_models_fields_and_source_metadata_v1"
    )

    @field_validator("created_at")
    @classmethod
    def utc_creation(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def publication_contract(self) -> "ModelManifest":
        if self.model_id != self.identity.model_id():
            raise ValueError("Model identity digest differs")
        if (
            self.scientific_file.size_bytes
            > self.identity.limits.max_product_file_bytes
        ):
            raise ValueError("Scientific file budget exceeded")
        if (
            self.source_metadata_file.size_bytes
            > self.identity.limits.max_manifest_bytes
        ):
            raise ValueError("Source metadata budget exceeded")
        return self


def serialize_model_manifest(manifest: ModelManifest) -> bytes:
    """Validate a publication payload and bound its bytes without writing files."""
    checked = ModelManifest.model_validate_json(manifest.model_dump_json())
    payload = (checked.model_dump_json() + "\n").encode("utf-8")
    if len(payload) > checked.identity.limits.max_manifest_bytes:
        raise ValueError("Model manifest byte budget exceeded")
    return payload
