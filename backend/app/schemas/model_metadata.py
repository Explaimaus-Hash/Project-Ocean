"""Bounded private source-attribute snapshots, with dtype and shape retained."""

from typing import Annotated, Literal

from pydantic import Field, StrictFloat, StrictInt, StrictStr, model_validator

from .products import Contract

Name = Annotated[str, Field(min_length=1, max_length=256)]
Value = StrictInt | StrictFloat | Annotated[StrictStr, Field(max_length=65536)]


class SourceAttribute(Contract):
    dtype: Annotated[str, Field(min_length=1, max_length=64)]
    shape: tuple[Annotated[int, Field(ge=0, le=2048)], ...] = Field(max_length=4)
    # NaN/+Inf/-Inf are tagged strings, distinguished by numeric dtype.
    values: tuple[Value, ...] = Field(max_length=2048)

    @model_validator(mode="after")
    def shape_matches(self) -> "SourceAttribute":
        import math

        if math.prod(self.shape) != len(self.values):
            raise ValueError("Attribute shape differs from values")
        if any(isinstance(v, float) and not math.isfinite(v) for v in self.values):
            raise ValueError("Nonfinite attributes must use tagged strings")
        return self


class SourceVariableMetadata(Contract):
    dtype: Annotated[str, Field(min_length=1, max_length=64)]
    dimensions: tuple[Name, ...] = Field(max_length=4)
    shape: tuple[Annotated[int, Field(ge=0)], ...] = Field(max_length=4)
    attributes: dict[Name, SourceAttribute] = Field(max_length=128)


class ModelSourceMetadata(Contract):
    schema_version: Literal[1] = 1
    representation: Literal["typed_flat_attributes_nonfinite_tokens_v1"] = (
        "typed_flat_attributes_nonfinite_tokens_v1"
    )
    global_attributes: dict[Name, SourceAttribute] = Field(max_length=128)
    variables: dict[Name, SourceVariableMetadata] = Field(min_length=1, max_length=512)
    interpretation: Literal["acquired_client_attributes_not_coverage_authority"] = (
        "acquired_client_attributes_not_coverage_authority"
    )
    discrepancies: tuple[str, ...] = (
        "inherited_globals_not_actual_subset_coverage",
        "source_time_labels_preserved_averaging_window_unresolved",
        "source_quantity_and_vertical_reference_not_harmonized",
    )
