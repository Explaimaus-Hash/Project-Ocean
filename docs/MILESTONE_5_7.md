# Part 5.7 — synthetic matching safe checkpoint

Status: approved work has produced a private synthetic-only matching kernel and an adjusted-pressure/depth bridge. This is a safe checkpoint, **not completion of real matching integration**. The verified real-field/support adapter remains unfinished; continue it only after permission before moving to 5.8. Frontend remains last.

## Implemented scope

- `schemas/matching.py`: frozen native axes/value/mask/support inputs and versioned pair/exclusion reports. These are internal contracts, not HTTP request/response endpoints or file-authentication evidence.
- `comparison/adjusted_depth.py`: bind original collection/sample IDs and native indices to adjusted quantity parameters/errors, re-evaluate quantity diagnostics, and call the existing GSW pressure-depth conversion. Canonical collection identity and on-disk file identity remain separate. Original raw-selected observations are not rewritten.
- `comparison/matching.py`: deterministic geographic nearest native column, verified containing daily interval and nearest adjusted central-depth level; then explicit tolerance, wet/mask/connectivity/bottom/pressure-endpoint checks. A missing/dry/masked nearest candidate never triggers a farther-cell replacement.
- Reports retain source/native indices, observation and model values, actual labels and verified time bounds, spatial/depth/time offsets, pressure-error endpoints, adjusted errors and exclusions. Policy/context/input hashes remain explicit. They contain no model-minus-observation differences, bias, RMSE or uncertainty weights.

The canonical [matching policy](MATCHING_POLICY.md) remains authoritative. Strict matching D-mode/QC1 differs deliberately from the earlier A/D flags-1/2 diagnostics. Tolerances require a reviewed selection-specific rationale; no real threshold is invented to obtain pairs. Mean-sphere great-circle distance uses radius 6,371,008.8 m. Interval membership is `[start, end)` and temporal offset uses the verified interval midpoint, not a guessed interpretation of a midnight label. Exact ties use native source indices. Full pressure-error-derived depth endpoints must fit verified local support; no clamping or tolerance expansion.

## Fail-closed behavior and limits

The kernel explicitly returns the blocker `real_field_and_support_adapter_not_implemented` for real mode. A caller cannot enable real matching by labelling support evidence verified or providing hash strings. The existing read-only `scripts.check_matching_policy` remains separate and does not read fields or search pairs; actual `config/comparison.yaml` limits remain null/unreviewed.

Global blockers leave overlap `not_evaluated` without evaluated rows. Unknown per-row support is `partially_blocked`; if no pairs are accepted, overlap remains `not_evaluated`. Fully evaluated unsuccessful rows report `no_valid_pairs` with exclusions, not fabricated numeric zeros or universal no-overlap. All reports retain `comparison_ready=false`, including synthetic successful pairs. `serialize_matches(request)` recomputes results rather than serializing an arbitrary claimed report.

Bounds: 250,000 native scalar values, one million horizontal candidate checks, 5,000 observations, 12 model times, 16 MiB serialized input, and 1 MiB output with incremental row accounting. These are engineering ceilings, not a hard OS-memory sandbox, throughput guarantee or measured browser performance. Large selections must be explicitly split without replacing native science with display previews.

## Verification record

Work began on 2026-09-14 and resumed after interruption on 2026-09-15. Full backend regression: **715 passed, 4 Windows symlink-permission skips, 1,465 warnings in 343.95 seconds**. One additional successful synthetic-temperature matching test was added after that full run was collected; all **79 latest matching/bridge/output-contract tests passed separately**, with 47 warnings in 29.12 seconds. These overlapping counts are not additive; no full-suite claim is made for the extra test beyond its separately verified group.

Final Ruff lint and formatting pass for 88 Python files; `pip check` reports no broken requirements. All 24 root/docs Markdown files pass local-link, fence and final-newline checks. Test coverage is in `backend/tests/test_matching_engine.py`, `backend/tests/test_matching_adjusted_depth.py` and `backend/tests/test_matching_output_contract.py`, alongside existing policy/preflight/conversion tests. Review added explicit field/quantity/units binding, source-index ties, rejection of raw-depth substitution, inclusive tolerance boundaries, output consistency and bounded-failure tests. Serialization recomputes from input; schema checks alone do not authenticate a scientific result.

Known warnings remain NumPy shape/timedelta deprecations, xarray/NetCDF fixture paths, Starlette HTTPX/AnyIO deprecations and the deliberately invalid range fixture. They are not claimed fixed. Checks found no remaining test failures; this is not a production-readiness, independent-validation or browser-performance guarantee. No Git operation, source cleanup or server launch was performed.

### Read-only real-data checks on 2026-09-15

The existing policy command again returned **exit3 / blocked**: 14 strict-QC, quantity and jointly eligible salinity observations; 10 unresolved policy/support requirements, zero pairs and overlap not evaluated. Canonical collection/client/provider/model-manifest hashes equal the preceding checkpoint; original model labels remain midnight, without invented time cells.

The new adjusted-depth bridge was exercised through the existing audited provider/quantity chain, separately from matching. All **14 adjusted central depths converted**, but only **12 pressure-error endpoint ranges evaluated**. The first raw pressure remains 2.799999952316284 dbar; adjusted pressure is 2.7300000190734863 dbar and diagnostic depth is 2.7149846595678846 m under the explicit zero-geopotential assumption.

Native observation indices 5 and 6 have adjusted pressures 1 and 2 dbar with error 2.4000000953674316 dbar. Their lower pressure endpoints are negative, outside this converter's supported 0–12,000 dbar domain. Both retain `outside_pressure_domain` and null depth endpoints: no surface clamping, zero replacement or match is inferred. Pressure endpoints remain sensitivity, not full uncertainty/confidence intervals or model-datum evidence.

Pre/post SHA256 and size/mtime identities were unchanged for five files: the scientific observation collection, model manifest, model scientific fields, Argopy client input and preserved provider input. The large BIO-ROMS original was not reread or changed. No derived report was persisted and no actual pair search was run on real data.

No live download, provider authentication, new dependency, persistent comparison product, new CLI, HTTP route or frontend was added in this checkpoint. Existing source-specific limits remain in [5.1](MILESTONE_5_1.md), [5.5](MILESTONE_5_5.md) and [5.6](MILESTONE_5_6.md); the checks above explicitly distinguish this resume's evidence from those historical checkpoints.

## Remaining 5.7 work — request permission

Implement a bounded verified real scientific-file/support adapter before enabling real kernel inputs. It must bind actual fields, per-variable/time/depth masks, axes and source identities to verified temporal, vertical-reference, observation/cell wet, bottom and candidate-specific connectivity evidence. Original model timestamps, raw observations and manifests must remain unchanged. Static support data/evidence may need a separately authorized acquisition; unavailable evidence remains blocked.

The current real Copernicus/Argo selection still lacks reviewed collocation limits and the required verified support evidence; model potential-temperature scale/reference also remains unresolved. An adjusted-depth calculation does not establish a common vertical datum. After completing the verified adapter and its checks, ask separately before 5.8 metrics, 5.9 comparison API, 5.10 end-to-end verification and the final frontend milestone.
