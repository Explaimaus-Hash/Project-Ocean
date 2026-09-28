# Part 5.8 — exploratory salinity residuals and metrics

Subsequent approved [5.9 snapshot/API milestone](MILESTONE_5_9.md) adds explicit publication and prepared-result GET routes. The no-persistence/no-API statements below describe the completed 5.8 checkpoint; its read-only metrics CLI and scientific restrictions are unchanged.

## Scope

The user approved 5.8 after the explicitly assumption-labelled 5.7 implementation. This adds descriptive model-minus-observation residuals, pair/exclusion counts, bias and RMSE. It does not promote exploratory matches to verified science, resolve provider questions, add HTTP routes or start frontend work. Strict matching, source selection, tolerances and raw files remain unchanged.

Supported operator workflow: existing Copernicus daily 202311 shallow practical salinity versus the existing Argo collection. All four source families remain required by the project, but this milestone does not invent matching support for INCOIS, gliders or temperature.

## Run

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.run_exploratory_metrics --accept-assumptions
```

Optional `--policy` and `--support-id` use the same existing inputs as the matching CLI. The policy is contained within the project, capped at 16 KiB and rechecked before output. There is deliberately no input option for a saved or user-uploaded matching report.

The command reruns authenticated local matching, including its source/QC/quantity/depth/static checks and post-read identity checks, then summarizes that immutable in-memory result. It writes JSON to stdout only: no saved product, cache, acquisition, credentials or data modification. Startup and health remain independent.

Exit 0: exploration evaluated, possibly with no valid pairs. Exit 3: blocked or partially blocked, with explicit remaining reasons. Exit 2: sanitized input/execution failure. `--accept-assumptions` is required. A partial result may contain descriptive metrics for its accepted subset but never represents the entire selection as resolved.

## Arithmetic and interpretation

For each accepted pair, `d = model_value - observation_value`. Bias is `sum(d) / N`; RMSE is `sqrt(sum(d²) / N)`, with denominator N, not N−1. Positive bias means model salinity exceeds observed salinity in the selected matched samples. Units remain `1 (PSS-78)` for differences, bias and RMSE; no conversion to g/kg is made.

Each accepted sample gets equal weight. No profile averaging, independence assumption, uncertainty weighting, correlation, significance test or confidence interval is implemented. Reported observation errors and all matching assumptions remain in the embedded matching report; uncertainty is **not propagated**. Sample counts are not independent-profile counts or effective statistical sample sizes. A small RMSE is not evidence of whole-model accuracy.

Unmatched rows never contribute zeros. If N=0, bias/RMSE are `null`, `metrics_available=false` and the residual list is empty. Counts distinguish:

- total selected observations;
- evaluated observations;
- matched pairs;
- evaluated but excluded observations;
- observations not evaluated because matching was blocked.

Exclusion counts count each reason at most once per row. Several reasons can apply to one excluded sample, so their sum need not equal the number of excluded samples. Blockers remain separate from per-row exclusions.

Scaled finite arithmetic avoids unnecessary intermediate square/sum overflow. An unrepresentable residual is rejected, never emitted as infinity/null or silently dropped. Tiny synthetic fixtures test zero, one, mixed-sign, very large and subnormal residuals.

## Contracts and safety

`ExploratoryMetricsReport` includes the complete original matching report, a SHA-256 identity of its canonical schema serialization, residuals bound to accepted sample IDs/indices, and a recomputed summary. It preserves `data_mode`, blocked/partial/evaluated status, assumption policy/version, source provenance, QC/errors, offsets and exclusions. The report and residuals carry `exploratory_assumptions`; `comparison_ready=false`, `independent_validation=false` and `uncertainty=not_propagated` remain mandatory.

Both generation and serialization validate counts, residual sign/values/identity, matching hash and arithmetic. The complete output, including nested matching evidence and residuals, is capped at 1 MiB; work is limited to the existing maximum 5,000 observations. Oversized reports fail rather than being silently truncated. No new dependency was added.

`summarize_exploratory` is a pure internal function for already trusted matching output, not an authenticator of externally supplied JSON. The operator entry point always reruns matching from verified local files. Neither schema validation nor a self-consistent hash proves external authenticity. A future API must not accept arbitrary reports as verified source evidence or expose this entire private operator schema directly.

## Actual local result — 2026-09-27

The unchanged selection evaluated 14 rows: **2 matched pairs, 12 exclusions, 0 unevaluated**. Exclusions: 9 outside the horizontal envelope and 3 with pressure-error endpoints outside support. Matching and source IDs are retained in [the 5.7 evidence](MILESTONE_5_7_EXPLORATORY.md).

| Quantity | Result, PSS-78 |
| --- | --- |
| Source sample 1 residual | +0.04678230918943882 |
| Source sample 2 residual | +0.04625583440065384 |
| Bias, N=2 | +0.04651907179504633 |
| RMSE, N=2 | 0.04651981657958769 |

These two samples share location/time; do not describe them as two independent profiles. The result is explicitly exploratory/descriptive. No matching limits were tuned and no extra source was downloaded to obtain these numbers.

## Verification and next part

Final offline regression: **966 passed, 4 skipped, 1,733 warnings in 248.39 seconds**. The four skips are existing Windows symlink-permission cases (OS error 1314). The suite includes 41 metrics tests covering arithmetic/sign/counts, null empty results, blocked versus excluded rows, partial subsets, non-finite/overflow rejection, unchanged assurance, tamper rejection, policy changes, sanitized failures, byte budgets and explicit CLI opt-in. Existing startup, health, strict matching and other backend regressions passed as part of this run.

Ruff lint and formatting passed for all 118 Python files; `pip check` reported no broken requirements. Local relative links resolved in all 12 updated Markdown files. Two real metrics CLI runs exited 0 with identical JSON; the complete output was 33,511 UTF-8 bytes including its final newline. An independent PowerShell calculation from the emitted residuals matched both bias and RMSE. Strict matching remained blocked inside both reports, and the strict policy file's SHA-256 stayed unchanged. These checks are not a browser/deployment latency benchmark or a guarantee of unmeasured scientific accuracy.

```powershell
.\ocean-env\Scripts\python.exe -m pytest backend/tests -q --disable-warnings --tb=short
.\ocean-env\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m ruff format --check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m pip check
```

Next, only after approval: **5.9 comparison API**, with bounded public contracts and safe failures. Decide on a prepared-result publication boundary so expensive matching/file audits do not run implicitly in requests. Part 5.10 end-to-end acceptance and frontend remain separately approved later work. No worker, persistence, comparison route or browser readiness is implied by this CLI.
