"""Private static input contracts; structural verification is not collocation."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, StrictBool, model_validator

from .models import ModelAxes, ModelId, Sha256, require_utc
from .products import Contract, ProductFile

SupportId = Annotated[str, Field(pattern=r"^b_[a-f0-9]{24}$")]
SourceKey = Annotated[
    str,
    Field(
        pattern=(
            r"^(catalogue\.json|catalogue_end\.json|metadata_end\.json|\.zmetadata|"
            r"(elevation|latitude|longitude|mask|deptho|deptho_lev)/[0-9]+(\.[0-9]+)*)$"
        )
    ),
]
Index = Annotated[int, Field(strict=True, ge=0, lt=5000)]
MaskValue = Annotated[int, Field(strict=True, ge=0, le=1)]


class StaticObject(Contract):
    sha256: Sha256
    size_bytes: int = Field(strict=True, gt=0, le=4194320)


class StaticChecks(Contract):
    surface_wet_count: int = Field(strict=True, ge=0, le=625)
    surface_dry_count: int = Field(strict=True, ge=0, le=625)
    wet_level_count_equals_deptho_lev: StrictBool
    bottom_level_numbering: Literal["unresolved_not_inferred_from_numeric_agreement"]
    vertical_reference: Literal["unresolved"]
    coastline_connectivity: Literal["not_evaluated"]


class StaticManifest(Contract):
    schema_version: Literal[1]
    processing_version: Literal["static_acquisition_1"]
    status: Literal["acquired_grid_checked_not_matching_ready"]
    data_mode: Literal["real", "synthetic"]
    model_id: ModelId
    model_manifest: ProductFile
    dataset_id: Literal["cmems_mod_glo_phy_my_0.083deg_static_202311--ext--bathy"]
    source_asset: Annotated[str, Field(max_length=512)]
    retrieved_at: datetime
    source_read_set: dict[SourceKey, StaticObject] = Field(min_length=7, max_length=128)
    source_read_set_is_complete_global_store: Literal[False]
    source_latitude_indices: tuple[Index, ...] = Field(min_length=1, max_length=25)
    source_longitude_indices: tuple[Index, ...] = Field(min_length=1, max_length=25)
    source_elevation_indices: tuple[Index, ...] = Field(min_length=50, max_length=50)
    axis_interpretation: Literal["original_negative_elevation_and_attributes_preserved"]
    transfer_bytes: int = Field(strict=True, gt=0, le=67108864)
    decoded_chunk_bytes: int = Field(strict=True, gt=0, le=134217728)
    subset: ProductFile
    checks: StaticChecks
    comparison_ready: Literal[False]

    @model_validator(mode="after")
    def consistent(self):
        require_utc(self.retrieved_at)
        if self.subset.size_bytes > 4194304 or self.model_manifest.size_bytes > 1048576:
            raise ValueError("Static/model file exceeds limit")
        if self.source_elevation_indices != tuple(range(50)):
            raise ValueError("All original static levels are required")
        for indices in (self.source_latitude_indices, self.source_longitude_indices):
            if any(b != a + 1 for a, b in zip(indices, indices[1:], strict=False)):
                raise ValueError("Contiguous native selection required")
        if self.transfer_bytes != sum(
            r.size_bytes for r in self.source_read_set.values()
        ):
            raise ValueError("Transfer count differs from retained objects")
        if (
            not {
                "catalogue.json",
                "catalogue_end.json",
                ".zmetadata",
                "metadata_end.json",
            }
            <= self.source_read_set.keys()
        ):
            raise ValueError("Original/final source metadata required")
        cells = len(self.source_latitude_indices) * len(self.source_longitude_indices)
        if self.checks.surface_wet_count + self.checks.surface_dry_count != cells:
            raise ValueError("Surface counts differ from selection")
        return self


class StaticSupportSnapshot(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["static_local_read_1"] = "static_local_read_1"
    status: Literal["static_inputs_verified_not_matching_ready"] = (
        "static_inputs_verified_not_matching_ready"
    )
    support_id: SupportId
    manifest_file: ProductFile
    manifest: StaticManifest
    model_axes: ModelAxes
    source_elevation_m: tuple[FiniteFloat, ...] = Field(min_length=50, max_length=50)
    # Native model depth position -> original static source elevation index.
    model_depth_to_source_elevation_index: tuple[Index, ...] = Field(
        min_length=1, max_length=50
    )
    mask: tuple[MaskValue, ...] = Field(min_length=50, max_length=31250)
    deptho_m: tuple[FiniteFloat | None, ...] = Field(min_length=1, max_length=625)
    deptho_lev: tuple[FiniteFloat | None, ...] = Field(min_length=1, max_length=625)
    mask_order: Literal["source_elevation,latitude,longitude_C"] = (
        "source_elevation,latitude,longitude_C"
    )
    missing_bottom_policy: Literal["source_fill_or_nonfinite_to_null"] = (
        "source_fill_or_nonfinite_to_null"
    )
    scientific_support_status: Literal[
        "interpretation_and_observation_binding_pending"
    ] = "interpretation_and_observation_binding_pending"
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def aligned(self):
        axes, m = self.model_axes, self.manifest
        cells = len(axes.latitude) * len(axes.longitude)
        if (len(axes.latitude), len(axes.longitude)) != (
            len(m.source_latitude_indices),
            len(m.source_longitude_indices),
        ) or (len(self.mask), len(self.deptho_m), len(self.deptho_lev)) != (
            50 * cells,
            cells,
            cells,
        ):
            raise ValueError("Static snapshot shape mismatch")
        z = self.source_elevation_m
        if any(v >= 0 for v in z) or any(
            b <= a for a, b in zip(z, z[1:], strict=False)
        ):
            raise ValueError("Original negative increasing elevation required")
        mapping = self.model_depth_to_source_elevation_index
        if len(mapping) != len(axes.depth_m) or any(
            i >= 50 or -z[i] != depth
            for i, depth in zip(mapping, axes.depth_m, strict=True)
        ):
            raise ValueError("Explicit exact depth-index mapping required")
        wet = sum(self.mask[-cells:])
        if wet != m.checks.surface_wet_count:
            raise ValueError("Snapshot wet count differs")
        return self
