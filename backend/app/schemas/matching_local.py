"""Read-only verified-input audit; neither pair output nor a readiness flag."""

import hashlib
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .depth import DepthReport, serialize_depth_report
from .matching_policy import Digest, MatchingPolicyAssessment
from .models import ModelAxes, ModelVariableInfo
from .products import Contract


class NativeFieldVerification(Contract):
    source_variable: Literal["so", "thetao"]
    manifest_sha256: Digest
    scientific_file_sha256: Digest
    source_metadata_sha256: Digest
    axes: ModelAxes
    variable_metadata: ModelVariableInfo
    value_count: int = Field(ge=1, le=250000)
    finite_value_count: int = Field(ge=0, le=250000)
    missing_value_count: int = Field(ge=0, le=250000)
    mask_meaning: Literal["native_variable_missing_mask_not_wet_domain"] = (
        "native_variable_missing_mask_not_wet_domain"
    )

    @model_validator(mode="after")
    def counts(self):
        a = self.axes
        if (
            self.value_count
            != (len(a.times) * len(a.depth_m) * len(a.latitude) * len(a.longitude))
            or self.value_count != self.finite_value_count + self.missing_value_count
        ):
            raise ValueError("Native field counts differ from axes")
        if self.variable_metadata.source_name != self.source_variable:
            raise ValueError("Native variable metadata differs")
        return self


class LocalMatchingAudit(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["matching_local_audit_1"] = "matching_local_audit_1"
    status: Literal["inputs_verified_matching_blocked"] = (
        "inputs_verified_matching_blocked"
    )
    assessment: MatchingPolicyAssessment
    field: NativeFieldVerification
    adjusted_depth_report: DepthReport
    adjusted_depth_report_sha256: Digest
    depth_converted_count: int = Field(ge=0, le=5000)
    depth_rejected_count: int = Field(ge=0, le=5000)
    pressure_endpoints_evaluated_count: int = Field(ge=0, le=5000)
    pressure_endpoints_unavailable_count: int = Field(ge=0, le=5000)
    remaining_integration: tuple[Annotated[str, Field(max_length=128)], ...] = (
        "verified_time_wet_bottom_connectivity_and_vertical_reference_required",
        "real_matching_kernel_integration_not_enabled",
    )
    matched_pair_count: Literal[0] = 0
    overlap_status: Literal["not_evaluated"] = "not_evaluated"
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        c = self.assessment.context
        d = self.adjusted_depth_report
        f = self.field
        ref = d.source_collection
        if ref is None or (ref.collection_id, ref.collection_sha256, ref.data_mode) != (
            c.collection_id,
            c.collection_file_sha256,
            c.data_mode,
        ):
            raise ValueError("Depth collection provenance differs")
        if (
            f.manifest_sha256 != c.model_manifest_sha256
            or f.axes.times != c.source_time_labels
            or f.axes.source_time_indices != c.source_time_indices
        ):
            raise ValueError("Verified model provenance differs")
        expected = "so" if c.quantity == "practical_salinity" else "thetao"
        if f.source_variable != expected or len(d.results) != c.sample_count:
            raise ValueError("Audit selection differs")
        if any(row.input.selected_kind != "adjusted" for row in d.results):
            raise ValueError("Only the verified adjusted depth bridge is accepted")
        converted = sum(row.status == "converted" for row in d.results)
        endpoints = sum(
            row.pressure_sensitivity.status == "evaluated" for row in d.results
        )
        if (self.depth_converted_count, self.depth_rejected_count) != (
            converted,
            len(d.results) - converted,
        ) or (
            self.pressure_endpoints_evaluated_count,
            self.pressure_endpoints_unavailable_count,
        ) != (endpoints, len(d.results) - endpoints):
            raise ValueError("Audit depth counts differ")
        if (
            hashlib.sha256(serialize_depth_report(d)).hexdigest()
            != self.adjusted_depth_report_sha256
        ):
            raise ValueError("Depth report digest differs")
        if c.adjusted_depth_alignment.status != "verified_for_input_snapshot":
            raise ValueError("Adjusted depth alignment must be verified")
        if (
            any(
                getattr(c, name).status != "unresolved"
                for name in (
                    "time_support",
                    "vertical_reference",
                    "wet_mask",
                    "bottom_support",
                    "coastline_connectivity",
                )
            )
            or self.assessment.status != "blocked"
        ):
            raise ValueError("This audit cannot promote missing scientific support")
        return self
