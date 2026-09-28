"""Exploratory results are deliberately incompatible with verified-match reports."""

import hashlib
from typing import Literal

from pydantic import Field, model_validator

from .matching import MatchResult, NativeMatchingReport
from .matching_policy import Digest, ModelTimeCell
from .products import Contract
from .spatial_support import SpatialDiagnostics


class ExploratoryAssumptions(Contract):
    version: Literal["shallow_salinity_exploration_1"] = (
        "shallow_salinity_exploration_1"
    )
    assurance: Literal["assumed_not_verified"] = "assumed_not_verified"
    horizontal_m: Literal[7000] = 7000
    vertical_m: Literal[1] = 1
    time_seconds: Literal[43200] = 43200
    maximum_model_depth_m: Literal[10] = 10
    time_rule: Literal["label_date_UTC_midnight_to_midnight"] = (
        "label_date_UTC_midnight_to_midnight"
    )
    vertical_rule: Literal["nominal_depth_GSW_defaults_no_SSH_correction"] = (
        "nominal_depth_GSW_defaults_no_SSH_correction"
    )
    spatial_rule: Literal["all_bracketing_nodes_wet_candidate_in_stencil"] = (
        "all_bracketing_nodes_wet_candidate_in_stencil"
    )
    limits_basis: Literal["engineering_defaults_not_validated_or_fitted_to_pairs"] = (
        "engineering_defaults_not_validated_or_fitted_to_pairs"
    )

    def assumption_id(self):
        return "ea_" + hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ExploratoryMatchResult(MatchResult):
    assurance: Literal["exploratory_assumptions"] = "exploratory_assumptions"


class ExploratoryMatchingReport(Contract):
    processing_version: Literal["exploratory_matching_1"] = "exploratory_matching_1"
    assurance: Literal["exploratory_assumptions"] = "exploratory_assumptions"
    comparison_ready: Literal[False] = False
    independent_validation: Literal[False] = False
    unresolved_systematic_uncertainty: Literal["time_label_and_vertical_datum"] = (
        "time_label_and_vertical_datum"
    )
    spatial_proxy_limitation: Literal[
        "no_subgrid_coastline_or_observed_bottom_proof"
    ] = "no_subgrid_coastline_or_observed_bottom_proof"
    data_mode: Literal["real", "synthetic"]
    assumptions: ExploratoryAssumptions
    assumption_id: str = Field(pattern=r"^ea_[a-f0-9]{64}$")
    strict_assessment: NativeMatchingReport
    spatial_diagnostics: SpatialDiagnostics
    static_manifest_sha256: Digest
    static_subset_sha256: Digest
    time_cells: tuple[ModelTimeCell, ...] = Field(max_length=12)
    blockers: tuple[str, ...] = Field(max_length=64)
    status: Literal["blocked", "evaluated", "partially_blocked"]
    overlap_status: Literal["not_evaluated", "matched", "no_valid_pairs"]
    matched_pair_count: int = Field(ge=0, le=5000)
    results: tuple[ExploratoryMatchResult, ...] = Field(max_length=5000)

    @model_validator(mode="after")
    def consistent(self):
        strict = self.strict_assessment
        if self.assumption_id != self.assumptions.assumption_id():
            raise ValueError("Assumption identity differs")
        if self.data_mode != strict.data_mode or (
            self.spatial_diagnostics.data_mode != self.data_mode
            or self.spatial_diagnostics.model_id != strict.policy.model_id
        ):
            raise ValueError("Exploratory source identity differs")
        if self.matched_pair_count != sum(r.matched for r in self.results):
            raise ValueError("Exploratory pair count differs")
        if self.status == "blocked":
            if (
                not self.blockers
                or self.results
                or self.overlap_status != "not_evaluated"
            ):
                raise ValueError("Blocked exploration cannot claim overlap")
            return self
        if self.blockers or len(self.results) != strict.context.sample_count:
            raise ValueError("Exploration must account for every observation")
        if strict.source_variable != "so":
            raise ValueError("Exploration supports practical salinity only")
        if tuple((c.source_time_index, c.label) for c in self.time_cells) != tuple(
            zip(
                strict.context.source_time_indices,
                strict.context.source_time_labels,
                strict=True,
            )
        ):
            raise ValueError("Assumed time cells differ from source labels")
        if any(c.start != c.label for c in self.time_cells):
            raise ValueError("Assumed daily start must equal midnight source label")
        expected_keys = [
            (r.position.sample_id, r.position.source_sample_index)
            for r in self.spatial_diagnostics.results
        ]
        if [
            (r.sample_id, r.source_sample_index) for r in self.results
        ] != expected_keys:
            raise ValueError("Exploratory rows differ from spatial diagnostics")
        if len(set(expected_keys)) != len(expected_keys):
            raise ValueError("Duplicate exploratory observations")
        unresolved = any("support_unresolved" in r.exclusions for r in self.results)
        if (self.status == "partially_blocked") != unresolved:
            raise ValueError("Unresolved support must remain visible")
        expected_overlap = (
            "matched"
            if self.matched_pair_count
            else "not_evaluated"
            if unresolved
            else "no_valid_pairs"
        )
        if self.overlap_status != expected_overlap:
            raise ValueError("Exploratory overlap differs from outcomes")
        for row in self.results:
            c = row.candidate
            if c is not None and not any(
                (c.source_time_index, c.model_time_label, c.time_start, c.time_end)
                == (t.source_time_index, t.label, t.start, t.end)
                for t in self.time_cells
            ):
                raise ValueError("Candidate differs from assumed daily cell")
            if row.matched and (
                c.horizontal_offset_m > self.assumptions.horizontal_m
                or c.vertical_offset_m > self.assumptions.vertical_m
                or c.midpoint_offset_seconds > self.assumptions.time_seconds
                or c.model_depth_m > self.assumptions.maximum_model_depth_m
                or row.reported_adjusted_errors["PRES"]
                > strict.policy.maximum_pressure_error_dbar
            ):
                raise ValueError("Exploratory match exceeds limits")
        return self
