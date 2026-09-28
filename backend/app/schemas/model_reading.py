"""Private verified native-field snapshot, not a scientific-support certificate."""

import math
from typing import Literal

from pydantic import Field, FiniteFloat, StrictBool, model_validator

from .models import ModelManifest
from .products import Contract, ProductFile

MAX_FIELD_VALUES = 250000


class NativeFieldSnapshot(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["native_field_read_1"] = "native_field_read_1"
    manifest: ModelManifest
    manifest_file: ProductFile
    source_variable: Literal["so", "thetao"]
    values: tuple[FiniteFloat | None, ...] = Field(max_length=MAX_FIELD_VALUES)
    valid_mask: tuple[StrictBool, ...] = Field(max_length=MAX_FIELD_VALUES)
    value_order: Literal["time,depth,latitude,longitude_C"] = (
        "time,depth,latitude,longitude_C"
    )
    mask_interpretation: Literal["variable_validity_not_wet_domain"] = (
        "variable_validity_not_wet_domain"
    )
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def aligned(self) -> "NativeFieldSnapshot":
        axes = self.manifest.identity.axes
        count = math.prod(
            map(len, (axes.times, axes.depth_m, axes.latitude, axes.longitude))
        )
        if count > MAX_FIELD_VALUES or len(self.values) != count:
            raise ValueError("Native field count differs from bounded axes")
        if len(self.valid_mask) != count or any(
            valid != (value is not None)
            for value, valid in zip(self.values, self.valid_mask, strict=True)
        ):
            raise ValueError("Native field mask differs from values")
        if self.source_variable not in self.manifest.identity.request.variables:
            raise ValueError("Variable absent from native manifest")
        return self
