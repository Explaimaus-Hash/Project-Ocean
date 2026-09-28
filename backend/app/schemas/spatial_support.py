"""Private grid diagnostics, deliberately not matching support evidence."""

from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, StrictBool, model_validator

from .models import ModelId, Sha256
from .products import Contract
from .static_support import SupportId

SampleId = Annotated[str, Field(pattern=r"^s_[a-f0-9]{24}$")]
NativeIndex = Annotated[int, Field(strict=True, ge=0)]


class SpatialPosition(Contract):
    sample_id: SampleId
    source_sample_index: NativeIndex
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, lt=180)


class GridColumnDiagnostic(Contract):
    model_latitude_index: NativeIndex
    model_longitude_index: NativeIndex
    static_latitude_index: NativeIndex
    static_longitude_index: NativeIndex
    surface_wet: StrictBool
    prepared_level_wet: tuple[StrictBool, ...] = Field(min_length=1, max_length=50)
    full_mask_shallowest_depth_coordinate_m: FiniteFloat | None
    full_mask_deepest_depth_coordinate_m: FiniteFloat | None
    deptho_below_geoid_m: FiniteFloat | None
    deptho_lev_uninterpreted: FiniteFloat | None


class SpatialDiagnosticRow(Contract):
    position: SpatialPosition
    status: Literal["outside_centre_envelope", "grid_diagnostic_only"]
    candidate: GridColumnDiagnostic | None
    horizontal_offset_m: Annotated[FiniteFloat, Field(ge=0)] | None
    stencil: tuple[GridColumnDiagnostic, ...] = Field(max_length=4)
    stencil_surface: Literal["all_wet", "all_dry", "mixed", "not_evaluated"]
    candidate_in_stencil: StrictBool | None
    observation_wet: None = None
    coastline_connected: None = None
    observation_bottom_supported: None = None

    @model_validator(mode="after")
    def consistent(self):
        outside = self.status == "outside_centre_envelope"
        if outside:
            if (
                self.candidate is not None
                or self.horizontal_offset_m is not None
                or self.stencil
                or self.candidate_in_stencil is not None
                or self.stencil_surface != "not_evaluated"
            ):
                raise ValueError("Outside points cannot have selected grid support")
        else:
            if (
                self.candidate is None
                or self.horizontal_offset_m is None
                or not self.stencil
            ):
                raise ValueError("Grid diagnostic requires a candidate and stencil")
            wet = sum(c.surface_wet for c in self.stencil)
            expected = (
                "all_wet"
                if wet == len(self.stencil)
                else "all_dry"
                if not wet
                else "mixed"
            )
            if self.stencil_surface != expected or self.candidate_in_stencil != (
                self.candidate in self.stencil
            ):
                raise ValueError("Grid diagnostic summary differs from columns")
        return self


class SpatialDiagnostics(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["spatial_support_diagnostic_1"] = (
        "spatial_support_diagnostic_1"
    )
    status: Literal["diagnostics_only_matching_blocked"] = (
        "diagnostics_only_matching_blocked"
    )
    support_id: SupportId
    model_id: ModelId
    data_mode: Literal["real", "synthetic"]
    static_snapshot_sha256: Sha256
    selection_rule: Literal["great_circle_nearest_no_wet_fallback"] = (
        "great_circle_nearest_no_wet_fallback"
    )
    stencil_rule: Literal["bracketing_native_centres_no_interpolation"] = (
        "bracketing_native_centres_no_interpolation"
    )
    results: tuple[SpatialDiagnosticRow, ...] = Field(max_length=5000)
    comparison_ready: Literal[False] = False
