# Part 5.6 — matching policy and preflight

Separately approved on 2026-09-10. The [canonical policy](MATCHING_POLICY.md) defines the later engine's time, spatial/depth, masks, tie-breaking, QC, uncertainty, provenance and exclusion behavior. Implementation here validates requirements and reports unmet gates; it does not find or publish pairs.

## Added

- Frozen versioned policy/context/time-interval/assessment schemas, full policy SHA256 identity and bounded serialization.
- Pure policy preflight with explicit unknowns, immutable originals, joint eligibility and no automatic readiness.
- Strict D-mode adjusted QC1/error screening, separate from unchanged earlier observation APIs and quantity diagnostics.
- Read-only local operator adapter and `scripts.check_matching_policy`; safe YAML example `config/comparison.yaml` with intentionally unreviewed/null collocation limits.
- Offline tests and synchronized current Markdown context. No new dependency, credential, provider acquisition, API, dataset rewrite, server or frontend.

## Actual local evidence

Real model `m_35e4c0ab33c1469a334ca837` and Argo collection `o_c645f248f801845378f0fdaf` were read through the existing bounded verification chain. Collection/provider/client and model-manifest identity checks passed without changes. Original UTC labels remain January29/30 2019 at midnight, with no invented averaging cells.

Salinity preflight: **14 strict-QC eligible, 14 quantity eligible, 14 jointly eligible observations before matching**. It correctly returned exit3 / `blocked`, not no-overlap or successful matching. Its 10 blockers are unreviewed/null horizontal/depth/time limits, unresolved time support, vertical reference, wet mask, bottom support, coastline connectivity and adjusted-depth alignment. Output was 2,745 UTF-8 bytes at this checkpoint.

A separate in-memory temperature-policy check, without editing the YAML, found 14 strict-QC eligible but **zero quantity/joint eligible observations** because model temperature scale/reference remain unresolved. Both preflights retain zero matched pairs, comparison false and overlap not evaluated. The five earlier horizontal candidates have not become matches.

The read-only adapter performs no model field search. Current support evidence cannot be promoted by editing a boolean/config flag. The pre-existing depth diagnostic selects raw pressure, while quantity diagnostics select adjusted; a verified adjusted-depth bridge is still required. Full uncertainty is not inferred from pressure-only error endpoints.

## Verification

Full regression: **636 passed, 4 Windows symlink-privilege skips, 1,420 warnings in 266.80 seconds**. Targeted operator/QC tests: 19 passed. After tightening mixed naive/UTC source-label validation, all **67 policy tests passed separately**; this includes one additional regression case not in the preceding full-suite count. No failing checks remain in those runs.

Ruff lint and format pass for 82 Python files; `pip check` reports no broken requirements. All 23 root/docs Markdown files pass relative-link, code-fence and final-newline checks. One formatter run reported a cache-write permission warning while exiting successfully; cache-free lint/format checks then passed without changing or deleting caches. Remaining test warnings are the known NumPy/xarray/NetCDF shape/timedelta, Starlette HTTPX/AnyIO and intentionally invalid range-fixture warnings, not claimed resolved here.

Independent review caught a report-serialization gap: a consistent-looking status could omit actual blockers. Serialization now recomputes the assessment and rejects a forged result. Tests also prove positive marginal QC/quantity counts cannot bypass a zero joint count, and noon-to-noon intervals cannot pass this calendar-day policy. Current operator preflight stays outside all health/startup and HTTP routes.

## What remains

5.6's policy/preflight implementation is complete; the real scientific prerequisites are **not** all resolved. Numeric collocation limits need selection-specific justification, exact daily label/bounds mapping needs evidence, and local masks/bottom/vertical reference plus adjusted-depth alignment must be verified. The pressure-error cutoff is not a substitute for any of them. [Decision details and primary sources](MATCHING_POLICY.md).

Next only with permission: **5.7 matching engine**, enforcing this contract with synthetic fixtures and retaining blocked real-data outcomes until essential evidence exists. Metrics, comparison APIs, broad end-to-end checks and frontend remain later separately approved parts.
