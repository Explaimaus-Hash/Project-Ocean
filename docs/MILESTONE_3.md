# Part 3 — verified V2 surface preparation and data APIs

Checkpoint: 2026-09-10, Windows 11 / Python 3.12.10, `C:/Users/pc/OneDrive/Desktop/ocean_2`. The user approved this part after completing the download. Frontend remains last and part 4 needs separate permission.

## Real source verified

The original `data/raw/incois/bio_roms/v2/pCO2-Corrected_INCOIS-BIO-ROMS_v2.nc` is 9,248,080,750 bytes. Streamed MD5 matches the registered published V2 checksum `78b7c0fbaa00db58a31563bb442a693b`; its read-only header report is saved in `data/metadata/incois_bio_roms_v2.json`. This is now an actual local verification, superseding the historical missing-file state in part 2. Raw bytes were never modified by this work.

Actual inspected axes:

| Axis | Samples | First / last |
| --- | --- | --- |
| LAT | 756 | -29.996871948242188 / 29.977840423583984 degrees north |
| LON | 1,081 | 30 / 120 degrees east |
| TIME | 480 | 1980-01-24T00:00:00Z / 2019-12-25T00:00:00Z |

All three are finite, one-dimensional and strictly increasing. TIME uses `days since 1980-01-24 00:00:00`, `proleptic_gregorian`. Latitude spacing is not assumed uniform; actual timestamps, not fabricated month starts or averaging bounds, are retained.

| Confirmed fields | Source units, preserved verbatim |
| --- | --- |
| SST | `deg C` |
| SSS | `PSU` |
| MLD | `m` |
| DIC, NO3 | `milimole/m3` |
| CHL | `kg/m3` |
| pCO2_Int, pCO2_Clim, pCO2_Original, Deviant_uncertainty | `micro atm` |

Every listed field is `(TIME, LAT, LON)`. No depth dimension/current components exist in this file. MLD is a scalar mixed-layer-depth field, not water-column observations. Source metadata uses nonstandard capitalization/spelling and embeds an older record DOI; both metadata and V2 checksum identity are preserved. No scientific quantity harmonization, full CF compliance, or comparison suitability is claimed.

## Implemented preparation

The thin operator command calls reusable backend processing, not API startup:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_bio_roms --variables SST SSS --west 30 --east 120 --south -30 --north 30 --start 2019-01-01 --end 2019-03-31
```

A saved verified inspection must match source/registry identity and current file size/mtime. The adapter rejects unsupported scalar names/units, calendars/grids, QC/ancillary metadata, missing/nonmonotonic axes, no-overlap and excessive requests. A box intersects actual cell centres; no extrapolation or silent scientific downsampling occurs.

Source masking/packing is decoded into float64 scientific samples, nonfinite values remain missing, and original attributes/encoding remain private provenance. Scale/offset/packed valid-range metadata is not re-applied to already decoded output. Time semantics stay source-timestamp-only because bounds/cell methods are not supplied. Direct netCDF4 keeps frame/chunk-cache control explicit without adding xarray/Dask to this small adapter. xarray remains a later provider/analysis option. [netCDF4 API](https://unidata.github.io/netcdf4-python/).

Deterministic IDs include source MD5, selection, data mode, resource policy, and processing version `surface_1`. Private temporary outputs are completed and checksummed; cache publishes first, then the processed directory plus manifest as the final availability marker. Unchanged output is reused; conflicts are rejected without overwriting files. A crash between publications may leave an unreferenced cache requiring operator review, not a selectable product.

### Current real product

`p_7c8210052d41d41259724e2d` contains SST and SSS for:

- 2019-01-29T00:00:00Z
- 2019-02-28T00:00:00Z
- 2019-03-30T00:00:00Z

Scientific shape: `3 × 756 × 1081`. Independent preview stride: 8, shape `3 × 95 × 136`. Scientific file: 10,093,402 bytes; preview file: 233,615 bytes. These compressed sizes are not the decoded in-memory array sizes or total project disk usage.

Private outputs:

- `data/processed/p_7c8210052d41d41259724e2d/fields.nc`
- `data/processed/p_7c8210052d41d41259724e2d/manifest.json`
- `data/cache/p_7c8210052d41d41259724e2d/preview.nc`

No other V2 variable/date range was prepared in this checkpoint. Source masks are handled, but observational QC, temperature/salinity harmonization and model-observation matching remain later work. `comparison_ready`, `volume`, `depth_profiles`, and `currents` are explicitly false.

## Implemented HTTP contracts

| Route | Contract |
| --- | --- |
| `/health` | Unchanged fixed liveness JSON, no file/network/scientific work. |
| `/ready` | Explicit required real-product checks; 200 ready / 503 not_ready. |
| `/api/v1/datasets` | All source families, their prepared selections, honest absent-adapter states. |
| `/api/v1/products/{product_id}` | Safe typed public selection/coordinates/times/variables/provenance/capabilities. |
| `/api/v1/products/{product_id}/frame` | One variable/time index, preview or bounded scientific region. |
| `/api/v1/products/{product_id}/timeseries` | Native scientific grid-cell samples at an in-support point. |

All science/readiness/errors carry schema version 1 and no-store headers. Pydantic response models are documented in OpenAPI and validated before publication; invalid internal payloads yield sanitized errors. Parameters require safe identities, finite coordinates, nonnegative time indices, known quality, and all four ordered region bounds or none. Missing matrices use JSON null, not zero. Responses retain shape/axis order, actual time/location, units, source identity, quality mode and processing policy.

Point series choose the nearest axis cell without searching for another wet cell. The requested and actual point plus distance are returned, and out-of-support points fail. This is inspection, not interpolation or model-observation matching. Preview requests return labelled strided source cells, while scientific requests retain native samples.

Readiness defaults to 503 until `OCEAN_REQUIRED_PRODUCT_IDS` is configured; no dataset is silently made required. It validates bounded manifests, prepared-file stat identities and one-byte read access, without raw-file reads, NetCDF parsing, hashing, or provider requests. A synthetic product does not satisfy real-data readiness. Optional source failures cannot make an otherwise valid required selection unavailable. Startup only constructs services; it loads no configuration files or scientific libraries.

## Enforced limits and remaining resource constraints

`config/performance.yaml` has schema-validated ceilings; values may be lowered but not increased beyond tested hard ceilings without changing code/tests:

| Boundary | Current limit |
| --- | --- |
| Operator selection | 4 variables, 366-day span, 12 actual source times, 8,000,000 variable-values |
| Axis length | 10,000 values per axis |
| Decompressed source chunk | 32 MiB |
| Configured field chunk cache | 16 MiB per variable |
| Preview / scientific frame | 16,384 / 65,536 cells |
| Scientific point series | Up to the 12 prepared timestamps |
| Serialized API response | 2 MiB, including metadata |
| Manifest | 512 KiB |
| Each prepared NetCDF file | 128 MiB |
| Product capacity | 64 directory entries per prepared/cache parent; leftovers count |
| Required readiness products | 16, explicitly configured |
| Simultaneous NetCDF reads | One per API process; overload returns 503 busy |

These bound logical work, chunks, products and responses, not total native-process RSS or task duration. NetCDF headers, decompression and compression can allocate internally; only trusted local operator inputs are supported. Locks do not coordinate separate API worker processes or independent operator jobs. Multiple-worker deployments, malicious uploads, cold-disk job memory/latency, total disk quota/eviction, and browser/GPU behavior are not validated here. No HTTP preparation worker, queue, arbitrary upload or unbounded export exists.

## Verification evidence

Verification distinguishes small synthetic fixtures from actual source access. Tests cover source checksum-report identity/staleness, units/calendar/axis rejection, packed masks/no double-decoding, missing values, selection ceilings, atomic/idempotent products, typed responses, no-I/O health/startup, invalid/tampered/unreadable products, and no wet-neighbour substitution.

Final combined run: **251 passed, 4 skipped, 199 warning instances** (255 collected). The warnings come from the three dependency deprecation categories described below, many repeated by fixture writes. Ruff lint passed and all 38 Python files passed format checking; `pip check` found no broken requirements. The Windows symlink skips remain explicit limitations.

Real verification used `scripts.verify_product` with the current product and `--check-raw`: six finite SST/SSS point samples (three times each) exactly matched original decoded raw-source values. Thirty repeated API preview responses were identical. This is a bounded sample check, not a checksum of every decoded scientific value. The original file remains unchanged and the saved verified input identity still matches.

A temporary Uvicorn server on loopback port 8013 returned 200 for health, configured readiness, developer docs/schema, catalogue, product metadata, SST preview and SSS point series. An oversized full-resolution regional frame returned 413. The test server was stopped after checks; use the README command to start the backend yourself. No remote provider connection was made by these checks. In-process measurements are in [performance.md](performance.md); browser targets remain unmeasured.

Known warnings are not suppressed: existing Starlette/HTTPX and AnyIO deprecations, plus netCDF4 writes triggering NumPy 2.5's deprecated array-shape assignment. The pinned stack passes current checks, but future compatible library upgrades must resolve these warnings before they become errors. Four actual symlink tests remain skipped because Windows lacks symlink-creation privilege (error 1314); do not label them passing. Other path validation tests pass.

## Next part

Part 4 requires permission: remaining INCOIS/GODAS, Copernicus, official Argo/Argopy and IFREMER glider ingestion with source-specific evidence. Comparisons require later quantity/QC/time-depth-location compatibility work. Frontend is last. No Git operations, external acquisition, or frontend implementation occurred in this part.
