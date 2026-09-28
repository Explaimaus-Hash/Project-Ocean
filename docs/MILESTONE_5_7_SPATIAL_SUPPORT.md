# Part 5.7-B — candidate-bound spatial diagnostics

Implemented on 2026-09-17. The supported **coding/diagnostic checkpoint is complete**, but 5.7-B's scientific decisions and the full 5.7 real matching path are not complete. This is not 5.7-C integration or permission to start metrics/API/frontend.

## Implemented rules and boundaries

`backend/app/comparison/spatial_support.py` adds a pure, bounded position diagnostic and an operator-only verified local wrapper. Typed rows live in `backend/app/schemas/spatial_support.py`. `scripts.audit_spatial_support` is a read-only CLI. No existing matching configuration, engine guard, acquisition, startup or API behavior changes.

For each collection position:

1. Require the inclusive prepared horizontal centre envelope. Outside points receive no candidate or stencil; there is no half-cell extrapolation or longitude wrapping.
2. Select the geographically nearest native centre using the existing mean-sphere great-circle metric and lowest native latitude/longitude indices for ties. Selection happens before looking at masks. A dry nearest cell is retained, never replaced by a farther wet cell.
3. Build the Cartesian set of bracketing native centres: one node at an exact centre, two on a grid line, otherwise four. These are diagnostic sampling nodes, **not established cell polygons or an interpolated coastline**. Report all-wet/all-dry/mixed surface masks and whether the selected candidate belongs to this set.
4. For candidate/stencil columns, report each prepared level's mask using the verified model-depth mapping. Derive shallowest/deepest wet coordinate values from all 50 source mask levels, not from `deptho_lev`. Reject noncontiguous wet columns. Distinguish model-acquisition indices from global static-source indices.
5. Retain geoid-described `deptho` separately and `deptho_lev` uninterpreted. No comparison of pressure-derived depth/error endpoints with bathymetry is authorized by these diagnostics. The eight-level prepared science extent is not expanded to the complete static column.

`observation_wet`, `coastline_connected` and `observation_bottom_supported` are always null. Even an all-wet four-node rectangle cannot certify absence of a sub-grid island/coastline or depth-dependent connection. Mixed/dry nodes identify model-grid concerns, not a factual claim that the observation instrument is on land. No graph search, alternate ocean path or wet-cell fallback is invented. These facts can inform a later explicitly reviewed grid-resolution support policy; they cannot be copied into `ObservationSupport` as verified booleans.

The local wrapper runs existing model/Argo/adjusted-input verification, reads the verified static snapshot and binds the exact model axes, model manifest, collection identity/canonical hash and data mode. It rechecks both input chains after calculation. The output retains policy/model/static/collection fingerprints and original sample IDs/indices. It includes **all collection positions**, not only QC-accepted or temporally/depth-matched rows. Existing QC, quantity, error-endpoint and time gates still apply in future matching.

Limits: 5,000 positions, one million horizontal candidate checks, cached columns within the 25×25 grid, at most four stencil nodes per row, incremental and final 1 MiB output checks. Reader limits from 5.7-A remain in force. Split oversized selections; do not decimate scientific samples. These are algorithm/data limits, not an OS memory or disk-time sandbox. Pure in-memory calculations do not authenticate caller-provided files; real use must go through the verified wrapper. No new dependencies.

## Command and actual local result

From the Desktop build root:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.audit_spatial_support
```

Defaults reuse `config/comparison.yaml` and static support `b_b18353b728b66639c7787d55`. Optional `--policy` and `--support-id` select other compatible contained local inputs. Exit 3 means valid diagnostics with real matching still blocked; exit 2 is a sanitized input/verification failure. No raw files are written, downloaded or served.

Actual run: exit 3, empty stderr, 16,959-byte JSON. Of 14 Argo sample rows, **5 are inside and 9 outside** the prepared centre envelope. The five inside rows share the same reported position; these are not five distinct profiles. Their nearest centre is about 2,571.325 m away, model indices `(0,5)` versus global static indices `(948,2945)`. All four bracketing surface nodes and all eight prepared levels at that candidate are wet in this saved mask.

Candidate full-mask depth coordinates span approximately 0.494–3,992.484 m; `deptho` is 4,121 m and `deptho_lev` is 46. The prepared scientific field remains only approximately 0.494–9.573 m deep. These separate numbers do not establish a shared observation/model datum, bottom-index convention, physical connectivity or additional scientific field coverage. All nine salinity blockers remain; zero pairs, overlap not evaluated, `comparison_ready=false`.

## Scientific decision register — still blocking

The primary references were revisited; no new version-specific resolution was established. This is a bounded follow-up, not a claim that no evidence exists elsewhere.

| Decision | Verified evidence and required next step |
| --- | --- |
| Grid observation support / connectivity | Candidate and bracketing masks are now verified for the saved input. A scientific reviewer must approve a resolution-limited rule and its limitations, or specify suitable shoreline/cell-geometry evidence. All-wet nodes alone remain diagnostic. |
| Daily label-to-interval mapping | PUM issue 1.7 describes full UTC-day means centred at noon; retained version202311 labels are midnight without time bounds. Obtain an exact version-specific label rule; do not shift labels from the generic statement. |
| Vertical datum and bottom | Static `deptho` is described relative to the geoid, while the pressure-depth diagnostic uses specified GSW assumptions. Obtain a defensible reference transformation/compatibility assessment and retain uncertainty; do not compare metre values merely because units match. |
| Temperature definition | Saved metadata does not establish the required temperature scale/reference-pressure compatibility. Keep temperature exclusions until version-specific evidence is established; salinity diagnostics do not resolve them. |
| Tolerances | Horizontal/depth/time settings remain null/unreviewed. A reviewer must choose selection-specific limits and rationale. The observed 2,571 m offset is an outcome, not a justified default. |

The product is distributed on a regular grid interpolated from its computational grid. Its PUM identifies potential temperature and describes daily averaging, but these statements do not independently resolve the missing version-specific contracts above. [Official PUM, introduction and §2(c–d)](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf).

GSW's pressure-height function accepts dynamic-height anomaly and sea-surface geopotential inputs. Using its diagnostic depth without a verified reference relationship is not evidence of compatibility with model/geoid bathymetry. [GSW pressure-to-height documentation](https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html).

Tolerance review options, **not applied defaults**: an explicitly reviewed zero-offset baseline asks for exact coincidence and would exclude these five horizontal candidates; a nonzero representativeness window requires a use-case/grid/time/uncertainty rationale independent of whether it produces pairs. Temporal midpoint offsets cannot be validated until exact intervals are resolved. Vertical tolerance is separate from pressure-error endpoint containment and the shallow prepared science extent. Neither option can override missing support evidence.

The existing [provider clarification draft](MILESTONE_5_7_SUPPORT_EVIDENCE.md#provider-clarification-draft--not-sent) remains unsent. Sending it, acquiring another source or accepting a new scientific support approximation needs an explicit decision; none was done here.

## Verification

New targeted suite: **27 passed, 24 existing NumPy/NetCDF shape warnings**. Coverage includes exact-centre/edge/four-node selection, outside boundaries, dry-nearest no-fallback, mixed/all-dry stencils, full-mask versus bottom-index distinction, hole rejection, native/static index separation, tie rules, identity/work/output budgets, invalid positions, no support promotion, local-wrapper binding/postchecks and safe CLI failures.

Full regression passed **875 tests, 4 Windows symlink-permission skips, 1,578 warnings in 265.12 seconds**. This includes the 27 new diagnostic tests; counts overlap and must not be added. Warnings remain existing NumPy/NetCDF/xarray/Starlette deprecations and the intentionally invalid-range fixture; no failing test remains in the final run.

Ruff lint and format passed for 106 Python files; `pip check` reports no broken requirements. All 30 maintained Markdown files passed local-link, fence and final-newline validation. Verification used `ocean-env/Scripts/python.exe`, pytest with `backend/pyproject.toml`, and the real CLI above. The real run is separate from synthetic fixture evidence; no browser/production-performance claim is made.

## Next step requiring approval

Later update: the user explicitly approved [5.7-C guarded execution plumbing](MILESTONE_5_7_EXECUTION.md). It now invokes the engine but preserves every unresolved scientific gate. This does not resolve the decisions in this document or authorize real pair search.

Finish the remaining 5.7-B scientific decisions above before real 5.7-C integration. Start with version-specific provider evidence and review of the grid-resolution support rule/tolerances; do not implement an assumption as a verified fact. Do not repeat the same generic metadata research indefinitely. The user must authorize provider contact or another evidence source if needed. Parts 5.8–5.10 and frontend remain later.
