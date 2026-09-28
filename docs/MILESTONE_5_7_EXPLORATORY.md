# Part 5.7 — assumption-labelled shallow salinity matching

Subsequent approved milestone: [5.8 descriptive exploratory metrics](MILESTONE_5_8.md) is now implemented over this matching output. The no-metrics statements below record the completed 5.7 checkpoint; its assumptions, strict-mode restrictions and matching results are unchanged.

## Current scope — 2026-09-27

The user explicitly approved building from assumptions after cross-checking online sources. This changes the earlier verified-only scope **for this separate exploratory workflow**, not the strict scientific contract. The exploratory implementation is complete; provider-verified matching remains blocked. Part 5.8, the comparison API and frontend have not started.

The read-only operator command authenticates existing files, recomputes adjusted-depth/QC alignment and static diagnostics, selects native stored-product values, retains every excluded observation, and rechecks inputs before returning. It does not acquire data, edit raw files, persist results, change startup/health or require credentials. INCOIS, Copernicus, Argo and gliders remain in the project; this narrow experiment covers only prepared Copernicus daily 202311 salinity and Argo.

## Evidence versus assumptions

The [official Copernicus product manual, issue 1.7, November 2025](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf) describes daily midnight-to-midnight averaging with a noon midpoint (p.9), and a distributed regular 1/12-degree grid with 50 levels (p.6). That grid is interpolated from the model's computational grid: here “native” means unchanged stored-product centres, not original NEMO C-grid cells. The manual also describes assimilation of in-situ temperature/salinity profiles (p.8); these comparisons are not automatically independent validation.

The [official GSW pressure-to-height documentation](https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html) defines sea pressure in dbar, height with ocean depth of opposite sign, and optional dynamic-height/surface-geopotential arguments. It does **not** establish a shared datum with this model subset. The existing depth bridge uses GSW defaults; omitted reference-surface corrections remain unquantified.

These sources were checked online on 2026-09-27. They do not resolve the precise interpretation of this saved source's midnight labels. The human support reply described interval-centred values but did not settle that discrepancy; the pending clarification remains relevant to strict mode. No new provider message was sent.

| Explicit experimental choice | Rationale and limitation |
| --- | --- |
| A midnight source label denotes that same UTC calendar day, `[00:00, next 00:00)` | Inference from the documented daily product, **not confirmed label metadata**. Original labels remain unchanged. |
| Compare nominal positive model depth directly with pressure-derived depth | Approximation only; no SSH/dynamic-height/datum correction, and no claim of bounded systematic vertical error. |
| All bracketing surface nodes wet, nearest candidate in that stencil | Grid-resolution proxy only; does not establish instrument wetness or exclude subgrid coasts/barriers. Dry/mixed stencils are rejected, not searched for alternative wet cells. |
| Common support uses the maximum shallowest wet centre and minimum deepest wet centre/bottom across candidate and stencil | Requires complete, consistent bottom/mask diagnostics. Missing or inconsistent support stays unresolved. `deptho_lev` indexing is not inferred or used. |
| Horizontal 7,000 m; vertical 1 m; midpoint offset 43,200 s | Fixed engineering defaults chosen **before running pairs**, not literature-validated or tuned to produce matches. About 6.6 km is the half-diagonal of a 1/12-degree equatorial cell; 7 km rounds that upward. Half the largest spacing in the current shallow eight-level selection is below 1 m. Twelve hours covers the assumed daily interval. |
| Prepared model centres no deeper than 10 m | Keeps the experiment narrow. These limits are not a policy for deep-ocean profiles, other sources or monthly fields. |

Changing these choices requires a new reviewed assumption version and tests; they are immutable literals, not permissive user-supplied evidence switches. `config/comparison.yaml` remains unchanged with null/unreviewed strict tolerances.

## Preserved safeguards and output

- Separate `ExploratoryMatchingReport`, incompatible with strict `NativeMatchingReport`; report and every row say `exploratory_assumptions`. Real data stays `data_mode=real`; `comparison_ready=false` and `independent_validation=false` always remain.
- Assumption ID, original strict assessment/blockers, source/manifest/subset hashes, recomputed spatial diagnostics, assumed time bounds, native indices, offsets, selected values, reported errors and exclusion reasons are retained.
- Existing strict D-mode adjusted QC1, quantity checks, missing-error rejection and maximum pressure error remain. Full pressure-error endpoints must fit prepared model and local support. No clipping, extrapolation, wet-cell fallback or tolerance expansion.
- Identity, quantity, adjusted-depth-alignment and budget failures are not assumption-overridable. Temperature remains unsupported: EOS-80 potential temperature is not silently equated with the existing ITS-90/GSW comparison target.
- Existing input/grid/work limits remain; JSON output is capped at 1 MiB, policy input at 16 KiB. These are bounded operator jobs, not an OS memory sandbox or a frontend performance benchmark.
- No residuals, bias/RMSE, HTTP comparison endpoints or UI are implemented here. A future metrics implementation must opt into this report type explicitly and propagate its limitations; it must not treat these as verified or independent-validation pairs.

## Run from the build root

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.run_exploratory_matching --accept-assumptions
```

The command prints bounded JSON only. Exit 0 means the selected exploration was evaluated, **not** that pairs necessarily exist or science is verified. Exit 3 means blocked/partially blocked; exit 2 is a sanitized input/execution error. Without `--accept-assumptions`, argument parsing refuses to run.

The original strict command remains available and blocked:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.run_local_matching
```

## Actual local result

Model `m_35e4c0ab33c1469a334ca837`, collection `o_c645f248f801845378f0fdaf`, support `b_b18353b728b66639c7787d55`: **14 rows, 2 exploratory salinity pairs**, 9 outside the horizontal centre envelope, 3 rejected because pressure-error endpoints exceed local/prepared support. No values or thresholds were changed after observing that result.

| Argo source sample index | Stored model indices `(time, depth, latitude, longitude)` | Observation PSS-78 | Model PSS-78 |
| --- | --- | --- | --- |
| 1 | `(0, 3, 0, 5)` | 35.16699981689453 | 35.21378212608397 |
| 2 | `(0, 5, 0, 5)` | 35.16600036621094 | 35.21225620061159 |

Both have a 2,571.325 m horizontal offset and a 27,069 s assumed-midpoint offset. Vertical offsets are about 0.0889 m and 0.5433 m. These are two samples from the same profile location/time, **not two independent profiles or a validation sample size**. No metrics were computed.

The strict command was separately rerun: exit 3, zero pairs, the same nine scientific/policy blockers plus the real-adapter guard. Provider confirmation of time/datum, a scientifically reviewed matching policy and compatible temperature definitions remain work for a verified workflow, not prerequisites for this labelled experiment.

## Verification

Full offline regression on 2026-09-27: **925 passed, 4 skipped, 1,671 warnings in 183.65 seconds**. The four skips are existing Windows symlink-permission tests (OS error 1314), not ignored matching failures. This is a test-suite duration, not a product latency benchmark.

Targeted exploratory tests: 32 passed. Existing execution/kernel tests: 54 passed before the full regression. Ruff lint passed; formatting verified all 114 Python files; `pip check` found no broken requirements. The final real exploratory CLI rerun exited 0 with 14 rows/2 pairs and `comparison_ready=false`; the strict CLI rerun exited 3, blocked with zero pairs. No network acquisition or credential storage occurred.

```powershell
.\ocean-env\Scripts\python.exe -m pytest backend/tests -q --disable-warnings --tb=short
.\ocean-env\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m ruff format --check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m pip check
```
