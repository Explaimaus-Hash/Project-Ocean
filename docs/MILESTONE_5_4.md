# Part 5.4 — pressure-to-depth conversion

10 September 2026 · Project root `C:/Users/pc/OneDrive/Desktop/ocean_2` · Approved checkpoint: 5.4 only.

## Outcome

Implemented latitude-aware pressure-derived depths using pinned GSW 3.6.23, typed source/provenance and QC/exclusion contracts, pressure-error endpoint evaluation, and a read-only operator report. The existing Argo collection was checked successfully without changing its raw selection, source depths, samples, flags or bytes. No model matching, quantity conversion, API route or frontend was introduced.

| Added/updated file | Responsibility |
| --- | --- |
| [schemas/depth.py](../backend/app/schemas/depth.py) | Explicit reference/assumption contracts, immutable sample inputs/results, pressure-only sensitivity and report provenance. |
| [processing/depth.py](../backend/app/processing/depth.py) | Lazy GSW calculation, per-sample rejection reasons and source-preserving observation adapter; no file/network I/O. |
| [convert_observation_depth.py](../scripts/convert_observation_depth.py) | Verify a bounded saved collection, check pressure units/hash, print a separate JSON report; no saved output or source rewrite. |
| [test_depth.py](../backend/tests/test_depth.py) | 50 tests for numerical references, sign/latitude, exclusions, uncertainty, immutability, imports and CLI boundaries. |
| [requirements.txt](../backend/requirements.txt) | Add `gsw==3.6.23`; existing dependencies remain pinned and were not upgraded. |

## Scientific definition and explicit assumptions

The implementation calculates `depth_m = -gsw.z_from_p(pressure_dbar, latitude, 0, 0)`. GSW uses sea pressure in dbar and latitude; its returned height is upward-positive. The project keeps depth positive downward and does not subtract atmospheric pressure again from an already sea-pressure input. [Official TEOS-10 reference](https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html).

Requests must explicitly acknowledge zero dynamic height and zero sea-surface geopotential, and supply evidence that input pressure is referenced to the sea surface. These are assumptions, not measured corrections. The Python function exposes both optional geopotential terms; this first project contract does not support nonzero values. [Official GSW-Python definition](https://teos-10.github.io/GSW-Python/conversions.html#gsw.conversions.z_from_p).

This is a pressure-derived depth estimate under the stated assumptions, **not an ellipsoid height or verified common model datum**. No latitude, dynamic-height or surface-geopotential uncertainty budget has been established. Existing supplied glider depths are retained as source values, not overwritten or declared equivalent to the estimate.

The prototype accepts 0–12,000 dbar and latitude −90–90 degrees for calculation. These are application bounds, not proof of accuracy across every water mass, pressure or GSW thermodynamic validity region. Unsupported negative/large pressures and out-of-range latitude are retained as rejected rows, not silently clipped. Nonfinite input numbers fail schema validation; missing values are explicit nulls.

## QC, sample identity and source selection

Each result keeps the original sample ID, selected pressure/name/kind, data mode, latitude, time/position/pressure flags, source eligibility and supplied source depth. Time, position and selected-pressure QC must each be 1 or 2, and existing source eligibility must pass. Rejections retain identity and a reason without inventing zero depth. The batch limit is 5,000 unique samples; a rejected row does not shift the alignment of later results.

`pressure_input` follows the collection's existing raw/adjusted selection. It does not choose adjusted values, fall back to raw, change the existing QC policy or alter D/A-mode data. A raw D-mode calculation can be useful as a diagnostic but is not certified for model comparison. The eventual adjusted-data choice remains Part 5.5.

The operator checks whether the selected pressure variable uses `dbar`, `decibar` or `decibars`. Other units fail; there is no implicit Pa/bar/metre conversion. Reference evidence is supplied by the trusted operator; a unit label alone does not prove a pressure datum, and the command does not browse/validate the evidence text automatically.

## Uncertainty handling

The source's adjusted-pressure error is retained independently even when raw pressure is selected. It is applied only to a selected adjusted pressure; raw pressure requires its own explicit raw error input, otherwise uncertainty remains unknown. The collection adapter does not invent an unavailable raw error.

When an applicable error `e` is available, calculate pressure endpoints `p−e` and `p+e`, then convert them independently at the same latitude. This is **pressure-error endpoint sensitivity**, not a confidence interval, a selected matching tolerance, or a complete depth uncertainty. Zero supplied error is distinguishable from missing error. Total depth uncertainty stays null because other contributions are not quantified.

If either endpoint lies outside the supported pressure domain, retain its actual pressure value and mark endpoint depths unavailable. Do not clamp it to the sea surface or drop one side to imply a complete interval. The central valid depth may still be reported. Source uncertainty fields are never discarded to make a match pass.

## Read-only operator usage

Use the existing project environment. On another machine, install the updated pinned runtime/development requirements first. No new credentials are needed.

```powershell
Set-Location -LiteralPath 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.convert_observation_depth --collection-id o_c645f248f801845378f0fdaf --reference-evidence "Argo PRES sea-pressure definition; provider audit in docs/MILESTONE_5_1.md" --assume-zero-geopotential
```

The command prints JSON to the terminal and exits 0 on report success. Invalid inputs/units, missing or changed collections, unavailable/mismatched GSW or invalid numerical output fail with safe errors. A successful report can include rejected samples; inspect each result's status. The command creates no data directory, result file, background task or server.

The report contains method/processing/GSW version, source collection ID/hash and data mode, reference evidence, explicit assumptions, original pressure provenance, computed depths, exclusions and sensitivity states. Serialization is capped at 16 MiB. This operator-sized limit does not change the existing 2 MiB HTTP response ceiling; no new HTTP endpoint exists.

## Actual Argo verification

Collection `o_c645f248f801845378f0fdaf` retained SHA256 `e77f2e92760b95ac820cab36839fcdc84d6df363dc25d837d05ba1eb06c9f078`. Its 14 selected raw pressures produced 14 converted results and no numerical/QC rejections under this diagnostic policy. Source-reference evidence came from the earlier [provider audit](MILESTONE_5_1.md); [Argo PRES vocabulary](https://vocab.nerc.ac.uk/collection/R03/current/PRES/) identifies the pressure parameter.

For the first five points at latitude −0.994°, values below are rounded only for documentation; calculations retain source precision:

| Raw pressure (dbar) | Derived depth (m) |
| --- | --- |
| 2.8 | 2.784599 |
| 4 | 3.977987 |
| 6 | 5.966952 |
| 8 | 7.955897 |
| 10 | 9.944823 |

All 14 rows retain the approximately 2.4 dbar adjusted error, but none applies it to the selected raw pressure. Their applicable pressure-error status is therefore `missing_error`, not zero. The report was 10,781 UTF-8 bytes for the exact evidence text used in verification; that size depends on evidence text and is not a general payload/performance guarantee.

The collection and its manifest, plus the existing prepared model's manifest, kept identical SHA256/size/mtime before and after the read-only CLI check. No new observation collection was published and existing `depth_m`/capability flags are unchanged. Large raw files were neither rewritten nor rehashed in this checkpoint.

These are **14 conversions, not 14 matches**. Nine observations remain outside the small model's horizontal box. Even the five horizontal candidates still require adjusted-data policy, model-datum/vertical support, uncertainty treatment and time/quantity compatibility. Conversion does not resolve those gates.

## Verification record

- Installed only the binary GSW 3.6.23 wheel into `ocean-env`, without upgrading other dependencies; dependency consistency passed.
- Initial new conversion plus health/startup checks: 56 passed, 2 existing warnings, 2.75 seconds.
- After CLI cases and stronger result invariants: 50 depth-specific tests passed in 1.56 seconds.
- Final full regression: **512 passed, 4 Windows symlink-permission skips, 964 warnings, 202.21 seconds**. This includes the final CLI cases and result invariants. The earlier intermediate full run also passed (510 tests), before the two CLI cases were added.
- Final Ruff lint passed; all 69 Python files passed formatting checks. `pip check` found no broken requirements.
- All 20 root/docs Markdown files passed local-link, code-fence and final-newline checks.
- Published TEOS-10 example depths at latitude 4° and pressures 10–1,000 dbar matched within 1e-9 m. Inverse pressure checks, zero/sign behavior, latitude dependence and hemisphere symmetry passed.
- Other tests exercise missing/invalid/QC-rejected rows, exact sample alignment, nonfinite inputs/library output, raw versus adjusted error handling, out-of-domain endpoints without clamping, unchanged source objects, explicit assumptions, report round trips, unsupported CLI units and lazy imports.
- Synthetic conversion tests and real verification prohibited socket connections. The independent startup probe still forbids GSW/scientific imports even though GSW is now installed.

Known warnings are the existing Starlette/HTTPX/AnyIO and NumPy/xarray/NetCDF deprecations, including the earlier model-preparation fixture warnings. Windows symlink tests need privileges absent here. Passing tests do not establish ocean-wide accuracy, full uncertainty, model validation or production/browser readiness.

## Next — permission required

**5.5: quantity compatibility.** Resolve source temperature/salinity definitions, explicit adjusted D-mode selection and supported conversions while keeping unresolved cases rejected. Model temperature scale, time averaging, local wet/vertical support, matching/metrics/API and frontend remain later separately approved work.
