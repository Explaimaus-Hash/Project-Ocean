# All-date BIO-ROMS surface archive

User-approved scope (2026-09-28): expose every actual source timestamp from the already downloaded BIO-ROMS V2 in the frontend. No new acquisition, scientific comparison assumption or raw-file change.

## Source and bounded design

The inspected source axis contains **480 timestamps**, from **1980-01-24T00:00:00Z** to **2019-12-25T00:00:00Z**. Preserve these exact labels: monthly data does not imply every calendar date or month-start samples.

The selected variables remain SST and SSS, over 30–120E / 30S–30N, clipped to native cell centres. An explicit operator command prepares 120 immutable products of four timestamps each. The previous three-date product remains untouched. Every batch retains original masks, units and native scientific resolution, plus a separate stride-8 display preview.

Only catalogue capacity is raised from 64 to **128**, including private leftovers. Per-product 8,000,000 variable-values, 12 maximum timestamps, 128MiB files, 16MiB variable chunk-cache, 32MiB decompressed source chunk, frame-cell and 2MiB response ceilings stay unchanged. Data is not collected into a whole-archive array. Source chunks span 80 times; bounded spatial tiles read a selected batch together to avoid repeatedly decompressing those chunks. A decoded output tile is capped at 12 × 256 × 256 float64 values (6MiB), separate from library/cache memory. This is not a hard process-RSS guarantee.

The dataset catalogue now includes each product's selected region. Frontend grouping requires the same dataset, mode, variable set and exact region. Duplicate timestamp labels resolve deterministically to one original product. Date input and timeline expose the union; frame requests retain the product-local index. Metadata/frame caches and cancellation remain bounded. No new HTTP processing or provider I/O was introduced.

The Analysis point time-series graph currently covers the selected prepared batch and says so. This task does not concatenate all 480 values into a full-history analysis plot. The saved Copernicus/Argo comparison remains a fixed, assumption-labelled historical snapshot.

## Commands

Run explicitly from `C:\Users\pc\OneDrive\Desktop\ocean_2`:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_bio_roms_archive
```

The command revalidates the saved source inspection, checks at least 8GiB free space, reads the real time axis, prints each completed batch and safely reuses unchanged batches if rerun. Conflicting products are rejected, never overwritten. It does not run on server startup. Previously prepared batches remain usable if an operator job stops; the UI shows only completed batches after a catalogue reload.

With FastAPI running on loopback port 8000:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.verify_bio_roms_archive
```

This verifier checks complete source-date coverage, requests SST/SSS preview frames for every timestamp, and compares a representative preview grid cell and a native scientific point against the raw source for each variable/time. It checks original size/mtime before/after, not a new full-file checksum or every ocean grid cell.

Restart/run instructions remain in [frontend integration](FRONTEND_INTEGRATION.md). Readiness still checks the explicitly configured existing required product; it does not certify every archive batch or all four sources. The archive verifier provides separate coverage evidence.

## Preparation / verification record

Preparation completed: **120 four-date products**, plus the preserved original product (121 total), expose **480 unique source dates**. Scientific and preview NetCDF files together occupy **1,634,764,976 bytes**, including the original product; catalogue JSON is **58,457 bytes**. No unfinished staging directories remain in active processed/cache catalogues. The frontend production build is running locally and shows all 480 available times.

Final browser suite: **11 passed in 30.9 seconds**, including early/middle/last dates, cross-batch changes, invalid date rejection, timeline synchronization and matching the displayed colorbar to 2019-12-25. The final globe screenshot was inspected. An earlier archive browser test failed because Playwright rejected a redundant zero-seconds datetime-local fill; using the browser-normalized minute form fixed the test, without relaxing application validation.

Final real HTTP verifier **passed in 52.76 seconds**: all 480 dates, **960 preview frames**, **960 exact preview-point comparisons** and **960 exact native-point comparisons** against raw SST/SSS; raw size/mtime unchanged. Both endpoints and the source axis were checked, not every spatial grid value. The deterministic timeline used 121 products because the preserved original product owns some overlapping dates.

An earlier verifier run collided with a browser scientific read and received the documented 503 `busy`; the verifier now retries only that explicit transient code, at most four retries, without changing the server's single-reader guard. A later attempted run found servers stopped after session turnover; both local services were restarted as hidden processes with logs under `logs/`. Connection failures and other API errors still fail verification. Functional timing above is a sequential warm/local verification duration, not a concurrency or browser performance guarantee.

Completed code checks: backend regression **1,026 passed / 4 Windows symlink skips / 1,833 warnings in 298.62s**, concurrent with archive preparation. An additional catalogue 128/129 boundary test was then added; the four-test archive module passed separately. Ruff lint/format, dependency check, frontend typecheck/lint/production build passed. Ten live frontend checks passed before final full-archive acceptance, including valid/invalid time entry and rejection of incompatible region/field/synthetic batch grouping. Saved exploratory comparison replay passed again with its published files/policy unchanged (2 pairs/14 rows).

The first unoptimized preparation was stopped after nine complete batches. Two interrupted private staging files (32,959-byte scientific and 20,311-byte preview) were preserved under `data/interrupted-preparation-20260928/`, outside active catalogues. Completed products and original source were not removed or overwritten.

## Boundaries

Subsequent UI polish: [batch transitions and graph layout](FRONTEND_INTEGRATION.md#batch-transitions-and-graph-layout--2026-09-28) documents stable labelled frames/colour scale, bounded one-frame prefetch, wrapped chart metadata and additional delayed-response/responsive checks. This supersedes the 11-test frontend checkpoint above; archive preparation and scientific verification are unchanged.

All-date access here means BIO-ROMS SST/SSS surface data, not newly served CHL/pCO2/other variables, GODAS, all Copernicus dates, or a vertical/current product. No inferred daily data, temporal interpolation, pressure/depth conversion or comparison-readiness promotion exists. Globe rendering is geographic 3D, not proof of volumetric ocean data. Full-archive interactive load/concurrent-user performance is not established by local functional tests.
