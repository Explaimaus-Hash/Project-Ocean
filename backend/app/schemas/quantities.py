"""Explicit quantity evidence and derived results, never matched pairs."""

from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .observations import ObservationValue
from .products import Contract

EvidenceText = Annotated[str, Field(min_length=1, max_length=2048)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
CoreName = Literal["PRES", "TEMP", "PSAL"]


class ProviderParameter(Contract):
    """Operator-inspected adjusted metadata in decoded numeric units."""

    name: CoreName
    adjusted_name: EvidenceText
    units: EvidenceText
    definition: Literal[
        "sea_pressure_dbar", "in_situ_ITS90_C", "practical_salinity_PSS78", "unresolved"
    ]
    definition_evidence: EvidenceText
    valid_min: FiniteFloat
    valid_max: FiniteFloat

    @model_validator(mode="after")
    def ordered(self) -> "ProviderParameter":
        if self.valid_min > self.valid_max:
            raise ValueError("Provider decoded bounds must increase")
        return self


class QuantityEvidence(Contract):
    """Caller must verify files/row alignment; this pure schema does no I/O."""

    client_input_sha256: Digest
    provider_input_sha256: Digest
    verification_evidence: EvidenceText
    parameters: tuple[ProviderParameter, ...] = Field(min_length=3, max_length=3)
    model_identity: EvidenceText
    model_evidence: EvidenceText
    model_salinity: Literal["practical_salinity_PSS78", "unresolved"] = "unresolved"
    model_temperature: Literal["potential_temperature", "unresolved"] = "unresolved"
    model_temperature_scale: Literal["ITS90", "IPTS68", "unresolved"] = "unresolved"
    model_reference_pressure_dbar: FiniteFloat | None = None

    @model_validator(mode="after")
    def unique(self) -> "QuantityEvidence":
        if {p.name for p in self.parameters} != {"PRES", "TEMP", "PSAL"}:
            raise ValueError("Exactly three unique core definitions are required")
        return self


class AdjustedParameter(Contract):
    name: CoreName
    original: ObservationValue
    selected_name: str | None
    provider_adjusted_name: str
    value: FiniteFloat | None
    error: FiniteFloat | None
    exclusions: tuple[str, ...]

    @model_validator(mode="after")
    def consistent(self) -> "AdjustedParameter":
        if (
            self.value != self.original.adjusted
            or self.error != self.original.adjusted_error
        ):
            raise ValueError("Adjusted values/errors must preserve the source")
        return self


class QuantityResult(Contract):
    sample_id: str
    source_sample_index: int = Field(ge=0)
    parameters: tuple[AdjustedParameter, ...] = Field(min_length=3, max_length=3)
    practical_salinity: FiniteFloat | None
    absolute_salinity_g_kg: FiniteFloat | None
    potential_temperature_0_dbar_ITS90_C: FiniteFloat | None
    salinity_exclusions: tuple[str, ...]
    temperature_exclusions: tuple[str, ...]
    conversion_exclusions: tuple[str, ...]
    converted_uncertainty: Literal[None] = None
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def result_consistency(self) -> "QuantityResult":
        if {p.name for p in self.parameters} != {"PRES", "TEMP", "PSAL"}:
            raise ValueError("Three unique core parameters are required")
        if (self.practical_salinity is None) != bool(self.salinity_exclusions):
            raise ValueError("Salinity value must agree with its exclusions")
        if any(
            (value is None) != bool(self.conversion_exclusions)
            for value in (
                self.absolute_salinity_g_kg,
                self.potential_temperature_0_dbar_ITS90_C,
            )
        ):
            raise ValueError("Conversion values must agree with exclusions")
        return self


class QuantityReport(Contract):
    processing_version: Literal["quantities_1"] = "quantities_1"
    selection_policy: Literal["argo_AD_adjusted_flags_1_2_no_fallback"] = (
        "argo_AD_adjusted_flags_1_2_no_fallback"
    )
    range_policy: Literal["provider_client_decoded_intersection"] = (
        "provider_client_decoded_intersection"
    )
    source_collection_id: str
    data_mode: Literal["real", "synthetic"]
    source_collection_canonical_sha256: Digest
    evidence: QuantityEvidence
    gsw_version: Literal["3.6.23"] = "3.6.23"
    results: tuple[QuantityResult, ...] = Field(max_length=5000)
    comparison_ready: Literal[False] = False
