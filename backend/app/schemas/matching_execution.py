"""Private integrated blocked execution, not an accepted real-pair contract."""

from typing import Literal

from pydantic import model_validator

from .matching import NativeMatchingReport
from .models import Sha256
from .products import Contract
from .spatial_support import SpatialDiagnostics


class LocalMatchingExecution(Contract):
    schema_version: Literal[1] = 1
    processing_version: Literal["matching_local_execution_1"] = (
        "matching_local_execution_1"
    )
    status: Literal["verified_pipeline_matching_blocked"] = (
        "verified_pipeline_matching_blocked"
    )
    engine: NativeMatchingReport
    spatial: SpatialDiagnostics
    static_manifest_sha256: Sha256
    static_subset_sha256: Sha256
    local_audit_sha256: Sha256
    comparison_ready: Literal[False] = False

    @model_validator(mode="after")
    def bound(self):
        e, s = self.engine, self.spatial
        if (
            e.context.model_id != s.model_id
            or e.data_mode != s.data_mode
            or e.context.sample_count != len(s.results)
            or e.status != "blocked"
            or not e.blockers
            or e.results
            or e.matched_pair_count != 0
            or e.overlap_status != "not_evaluated"
        ):
            raise ValueError("Integrated blocked report identities/state differ")
        return self
