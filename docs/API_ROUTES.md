# Project Ocean · API Route Guide

## All-date BIO-ROMS archive follow-up

See [archive scope/evidence](BIO_ROMS_ARCHIVE.md). Existing product GET routes now serve the prepared SST/SSS archive in four-timestamp products. Catalogue capacity is 128; ready summaries add optional `region` (emitted for current products). The frontend merges compatible products by actual timestamp and requests the correct product-local `time_index`; do not send the 0–479 global timeline index to an individual product. A product metadata/point-series response still covers only that bounded product, not all 480 archive dates. HTTP never prepares data. Old three-date product links remain valid.

5.10 verification update: all **13 existing application paths** passed a temporary local Uvicorn/HTTP smoke check. No new route was added. [Acceptance evidence and remaining limits](MILESTONE_5_10.md) distinguish actual socket checks from in-process tests, scientific readiness and browser performance. The read-only `scripts.verify_comparison` command rechecks saved comparison consistency; it is not an HTTP endpoint.

Current backend continuation (2026-09-27): [5.9 prepared comparison API](MILESTONE_5_9.md) adds three read-only routes over explicitly saved exploratory results. Run `scripts.prepare_comparison --accept-assumptions` as an operator; HTTP never invokes matching or downloads. See [comparison usage](#comparison-api--part-59). Private evidence/file records are not public request/response contracts. Older checkpoint notes below are historical.

**Comparison-route verification:** 27 September 2026 · **Application:** 0.1.0 · **Status:** 13 read-only application paths, including prepared exploratory comparisons; no frontend or live HTTP processing.

> All 13 application routes are read-only GET endpoints. Existing observation data/capabilities are unchanged. Separate comparison snapshots retain derived depths, explicit assumptions and `comparison_ready=false`. Strict verified comparison, model-depth/current serving and frontend remain unimplemented.

Part 5.5 adds the private read-only `scripts.audit_quantities` command, not an endpoint. Adjusted quantity diagnostics preserve the existing raw collection and its API responses; real model temperature compatibility remains blocked. See [verification and usage](MILESTONE_5_5.md).

Part 5.6 adds `scripts.check_matching_policy`, still not an HTTP route. It reports unmet scientific requirements as blocked, with overlap not evaluated and zero matched pairs; changing limits alone cannot resolve missing support evidence. [Policy and exit codes](MATCHING_POLICY.md). Existing 10 application routes are unchanged.

Part 5.7 adds private in-memory synthetic matching, an adjusted-depth bridge, a verified native-field reader and `scripts.audit_matching_inputs`. This new read-only operator CLI verifies inputs and adjusted-depth alignment, but never calls the matching kernel: exit3 reports `inputs_verified_matching_blocked`, zero pairs and overlap not evaluated; exit2 reports verification failure. There is no pair-matching CLI or comparison HTTP route. Scientific-support verification and real-kernel integration remain unfinished, so real mode is blocked. Do not expose internal file hashes/support evidence as a browser request contract. [Historical kernel checkpoint](MILESTONE_5_7.md), [current reader continuation](MILESTONE_5_7_READER.md).

| Local base URL | Interactive API explorer | Machine-readable contract |
| --- | --- | --- |
| `http://127.0.0.1:8000` | [Open Swagger /docs](http://127.0.0.1:8000/docs) | [Open /openapi.json](http://127.0.0.1:8000/openapi.json) |

## Contents

1. [Start and test](#start-and-test)
2. [Route directory](#route-directory)
3. [Which ID belongs where?](#which-id-belongs-where)
4. [Health and readiness](#health-and-readiness)
5. [Datasets and surface products](#datasets-and-surface-products)
6. [Acquisitions](#acquisitions)
7. [Observations and pagination](#observations-and-pagination)
8. [Errors and limits](#errors-and-limits)
9. [Comparison API](#comparison-api--part-59)
10. [Planned capabilities—not routes yet](#planned-capabilitiesnot-routes-yet)
11. [Verification and maintenance](#verification-and-maintenance)

---

## Start and test

Run these commands in Windows PowerShell, one at a time. Reuse the existing project environment.

```powershell
Set-Location -LiteralPath 'C:\Users\pc\OneDrive\Desktop\ocean_2'
$env:OCEAN_REQUIRED_PRODUCT_IDS = '["p_7c8210052d41d41259724e2d"]'
.\ocean-env\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend/app
```

Keep that terminal running. Open another PowerShell terminal for requests:

```powershell
$baseUri = 'http://127.0.0.1:8000'
$productId = 'p_7c8210052d41d41259724e2d'
$collectionId = 'o_c645f248f801845378f0fdaf'

Invoke-RestMethod -Uri "$baseUri/health"
Invoke-RestMethod -Uri "$baseUri/api/v1/datasets" | ConvertTo-Json -Depth 10
```

For raw HTTP headers and JSON, use `curl.exe`, not PowerShell's possible `curl` alias:

```powershell
curl.exe -i 'http://127.0.0.1:8000/ready'
```

In Swagger: expand a route → **Try it out** → enter parameters → **Execute**. Press Ctrl+C in the server terminal when finished. If port 8000 is occupied, choose another free port and update the URLs; do not stop an unrelated process.

**Access boundary:** these API routes currently have no application authentication layer. Copernicus credentials are only for operator ingestion; do not send them to these endpoints. Keep this development server on loopback. Public deployment needs separate security review, HTTPS and configured access controls. CORS is not configured yet, so a separate browser frontend origin is not automatically allowed.

## Route directory

All paths are relative to the base URL. `{...}` means substitute an ID; do not type the braces.

| Group | Method | Implemented path | What it returns |
| --- | --- | --- | --- |
| Service | GET | `/health` | API liveness only |
| Service | GET | `/ready` | Availability of explicitly required local surface products |
| Discovery | GET | `/api/v1/datasets` | Registered datasets and prepared surface-product summaries |
| Surface | GET | `/api/v1/products/{product_id}` | Product metadata, axes, times, units and capabilities |
| Surface | GET | `/api/v1/products/{product_id}/frame` | One variable/time frame: preview or bounded scientific cells |
| Surface | GET | `/api/v1/products/{product_id}/timeseries` | Native grid-cell values across prepared timestamps |
| Inputs | GET | `/api/v1/acquisitions` | Local acquired-input inventory and safe provenance |
| Observations | GET | `/api/v1/observations` | Local prepared observation collections |
| Observations | GET | `/api/v1/observations/{collection_id}` | Collection metadata, QC, counts and capabilities |
| Observations | GET | `/api/v1/observations/{collection_id}/samples` | Paged scientific samples with raw/adjusted values and QC |
| Comparisons | GET | `/api/v1/comparisons` | Prepared exploratory snapshots or unavailable entries |
| Comparisons | GET | `/api/v1/comparisons/{comparison_id}` | Source IDs, assumptions, counts, bias/RMSE and scientific limitations |
| Comparisons | GET | `/api/v1/comparisons/{comparison_id}/samples` | Paged pairs/exclusions, coordinates, candidate offsets/errors and residuals |

Developer pages are separate from these 13 application routes:

| Method | Path | Availability |
| --- | --- | --- |
| GET | `/docs` | Swagger HTML, enabled by default |
| GET | `/openapi.json` | Generated API schemas, enabled by default |
| GET | `/docs/oauth2-redirect` | Swagger helper page; not an implemented login/authentication API |

Setting `$env:OCEAN_DOCS_ENABLED = 'false'` before server startup disables all three developer paths. Restart after changing settings. Swagger HTML uses external CDN assets by default; receiving its HTML does not prove the interactive browser page works offline. There is no root `/` page and no `/redoc` page.

## Which ID belongs where?

| ID type | Example in this project | Use it for |
| --- | --- | --- |
| Registry dataset ID | `incois_bio_roms_v2` | Find its entry in `/api/v1/datasets`; it is not a product ID |
| Prepared surface product ID | `p_7c8210052d41d41259724e2d` | `/api/v1/products/{product_id}` and its frame/time-series routes |
| Acquisition ID | `a_9e918d43555ffc26d3659e08` | Identify an entry in `/api/v1/acquisitions`; no individual acquisition HTTP route exists |
| Observation collection ID | `o_c645f248f801845378f0fdaf` | Observation metadata and sample pages |
| Prepared comparison ID | `c_0abd2057c5bc5c41fcf49109` | Comparison metadata and matched/excluded sample pages |
| Profile ID, when proven | `r_` followed by 24 lowercase hexadecimal characters | Optional sample-page filter; use an actual returned ID only |

The current Argo collection has **no verified profile IDs**. Do not substitute its float number, cycle number or sample ID for `profile_id`.

| Current local data | Available stage | Browser/API consequence |
| --- | --- | --- |
| INCOIS V2 SST/SSS, Jan–Mar 2019 | Prepared surface product | Metadata, frames and point time series work |
| Argo, 14 near-surface points on Jan29 2019 | Prepared scientific observation collection | Metadata and sample pages work; comparison remains false |
| Copernicus, four fields, Jan29–30 2019 | Acquired input plus private native model `m_35e4c0ab33c1469a334ca837` | Acquisition inventory stays acquisition-stage only; no model field/depth/current serving yet |
| IFREMER Bella | Acquired input; normalization rejected inconsistent TIME metadata | Inventory entry, not a ready observation layer |
| INCOIS GODAS | Registered source; live acquisition unresolved | Registration does not establish available data |

These are local snapshot findings. Use the catalogues to discover current IDs instead of hard-coding them into future frontend components.

---

## Health and readiness

### GET /health

[Open health](http://127.0.0.1:8000/health)

No parameters. Expected HTTP `200`:

```json
{
  "status": "ok",
  "service": "Project Ocean Backend"
}
```

This checks only that the API responds. It performs no dataset reads, provider requests or ingestion. Unlike the versioned data responses, health has no `schema_version` field.

### GET /ready

[Open readiness](http://127.0.0.1:8000/ready)

No request parameters. Configuration comes from the server's process environment, not URL parameters.

| HTTP | Meaning |
| --- | --- |
| `200` | Every configured required real surface product passes local readiness checks |
| `503` | Requirements are unset, or a required product is unavailable/invalid |

Actual response when `OCEAN_REQUIRED_PRODUCT_IDS` is unset/empty:

```json
{
  "schema_version": 1,
  "status": "not_ready",
  "reason_code": "required_products_not_configured",
  "checks": []
}
```

With requirements configured, inspect `checks[].product_id`, `status` and `reason_code`. Checks concern bounded manifests/file access—not live source connectivity, raw NetCDF processing, observation comparison or full-project readiness. `/health` can correctly return 200 while `/ready` returns 503.

## Datasets and surface products

### GET /api/v1/datasets

[Open dataset catalogue](http://127.0.0.1:8000/api/v1/datasets)

No parameters. Response schema: `CatalogueResponse`.

- `datasets[]`: source/dataset ID, title, role, public origin, status, reason and linked product IDs.
- `products[]`: prepared-product summaries, or unavailable-product reason codes.

A source's `not_prepared` here means no available **surface product**. Argo observations or a Copernicus acquisition can exist in their separate catalogues without appearing as a ready surface product. This endpoint does not contact providers.

### GET /api/v1/products/{product_id}

[Open current V2 metadata](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d)

Required path parameter: `product_id`, an actual prepared product identifier. No query parameters. Response schema: `MetadataResponse`.

Read `variables`, `times`, `latitude`, `longitude`, `selection`, `preview_stride`, `capabilities`, `data_mode`, `qc_policy` and `temporal_support` before requesting frames. `ready_scope` is `prepared_surface_selection`, not comparison readiness.

Current V2 product variables are case-sensitive `SST` and `SSS`. Its zero-based time indices are:

| time_index | Actual UTC timestamp |
| --- | --- |
| 0 | `2019-01-29T00:00:00Z` |
| 1 | `2019-02-28T00:00:00Z` |
| 2 | `2019-03-30T00:00:00Z` |

Use the returned `times` array for other products. Do not assume month-start dates or use an observation/acquisition ID in this route.

### GET /api/v1/products/{product_id}/frame

One scalar variable at one prepared time. Response schema: `FrameResponse`.

| Query parameter | Required? | Allowed values / behavior |
| --- | --- | --- |
| `variable` | Yes | Exact prepared source name, currently `SST` or `SSS` for the example product |
| `time_index` | Yes | Integer ≥0 and within the product's actual `times` array |
| `quality` | No | `preview` (default) or `scientific` |
| `west` | As a set | −180 ≤ value <180 |
| `east` | As a set | −180 < value ≤180 |
| `south` | As a set | −90 ≤ value ≤90 |
| `north` | As a set | −90 ≤ value ≤90 |

Supply **all four bounds or none**. Require `west < east` and `south < north`; wrapping/dateline selections are unsupported. Bounds select intersecting prepared source-cell centres, not new interpolated coordinates.

**Preview:** [open SST preview, time 0](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/frame?variable=SST&time_index=0).

```powershell
Invoke-RestMethod -Uri "$baseUri/api/v1/products/$productId/frame?variable=SST&time_index=0"
```

**Scientific:** [open native cells in 60–61E, 0–1N](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/frame?variable=SST&time_index=0&quality=scientific&west=60&east=61&south=0&north=1).

```powershell
Invoke-RestMethod -Uri "$baseUri/api/v1/products/$productId/frame?variable=SST&time_index=0&quality=scientific&west=60&east=61&south=0&north=1"
```

| Output field | How to interpret it |
| --- | --- |
| `dimensions`, `shape` | Axis order is `["latitude", "longitude"]`; shape is `[rows, columns]` |
| `values[row][column]` | Value at the corresponding latitude/longitude; missing is JSON `null` |
| `time`, `time_index`, `variable`, `units` | Actual returned frame identity and quantity units |
| `quality`, `display_only`, `sampling`, `stride` | Whether this is a display preview or native scientific sample grid |
| `valid_count`, `missing_count` | Explicit valid/missing cell counts |
| `requested_region` | Requested bounds, or null; returned axes show actual coverage |

Verified examples: preview shape **95×136**, 170,898 JSON bytes; small scientific shape **12×13**, 4,409 bytes. These are observed payload sizes, not browser speed guarantees.

Preview limit: 16,384 cells. Scientific frame limit: 65,536 cells. A full-box scientific request for this product returns `413 cell_limit`; choose preview or a smaller region. Both variants are bounded by a 2 MiB response limit.

This route has no depth selector, date-range preparation, volume rendering or current-vector support. `scientific` means native samples—not scientifically harmonized model-observation comparison.

### GET /api/v1/products/{product_id}/timeseries

[Open SST series at 70E, 0N](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/timeseries?variable=SST&longitude=70&latitude=0)

| Query parameter | Required? | Constraint |
| --- | --- | --- |
| `variable` | Yes | Exact prepared variable name |
| `longitude` | Yes | Finite value in [−180,180), also inside actual product support |
| `latitude` | Yes | Finite value in [−90,90], also inside actual product support |

```powershell
Invoke-RestMethod -Uri "$baseUri/api/v1/products/$productId/timeseries?variable=SST&longitude=70&latitude=0" | ConvertTo-Json -Depth 8
```

Response schema: `TimeseriesResponse`. Read aligned `times[]`/`values[]`, `requested_point`, `sample_point`, `sample_indices` and `distance_m`.

The series uses the nearest axis-grid cell across the prepared timestamps, without interpolation or a search for another wet cell. Missing values stay null. It returns `display_only: false` and `comparison_result: false`. No time-range/depth/profile query filters exist here.

## Acquisitions

### GET /api/v1/acquisitions

[Open acquired-input inventory](http://127.0.0.1:8000/api/v1/acquisitions)

No parameters. Response schema: `AcquisitionCatalogueResponse`.

The top-level `scope` is `locally_available_acquisitions_not_live_access`. Each `acquisitions[]` entry includes IDs, provider/dataset version, public origin, safe selection/variable information, input checksum/size, retrieval time, client transformations and transport. Private filenames/stat records and credentials are not exposed.

Acquisition records remain `acquired_not_prepared` with `comparison_ready: false`: this inventory does not join downstream products. Part 5.3's separate model does not rewrite raw acquisition manifests. FTP/local file imports may have `selection: null`; that is not evidence that no data exists.

There is no `GET /api/v1/acquisitions/{acquisition_id}`, HTTP download trigger, login endpoint or job submission endpoint. Ingestion is an explicit operator CLI workflow documented in [Part 4](MILESTONE_4.md); viewing this inventory does not start a download.

## Observations and pagination

### GET /api/v1/observations

[Open observation catalogue](http://127.0.0.1:8000/api/v1/observations)

No parameters. Response schema: `ObservationCatalogueResponse`.

Read `collections[]`: each entry has a collection ID and status; ready entries include metadata, unavailable ones include a reason code. A collection being ready means local scientific samples are available, not comparison-ready. Maximum catalogue size is 32 collections.

### GET /api/v1/observations/{collection_id}

[Open current Argo metadata](http://127.0.0.1:8000/api/v1/observations/o_c645f248f801845378f0fdaf)

Required path parameter: `collection_id`, matching `o_` plus 24 lowercase hexadecimal characters. No query parameters. Response schema: `ObservationMetadataResponse`.

Read `variables`, `counts`, `selection.value_mode`, `qc_policy`, source time units/calendar, `client_processing`, `warnings` and `capabilities`. The example collection contains PRES/TEMP/PSAL, retains raw and adjusted values, but currently selects **raw**. It has 14 samples, profiles disabled and pressure-to-depth conversion disabled.

Part 5.1 found these are delayed-mode observations; raw QC eligibility must not be mistaken for an approved comparison policy. [Scientific audit and unresolved gates](MILESTONE_5_1.md).

### GET /api/v1/observations/{collection_id}/samples

[Open first five Argo samples](http://127.0.0.1:8000/api/v1/observations/o_c645f248f801845378f0fdaf/samples?limit=5)

| Query parameter | Required? | Default | Constraint |
| --- | --- | --- | --- |
| `offset` | No | 0 | Integer 0–5,000 |
| `limit` | No | 100 | Integer 1–500; response must still fit 2 MiB |
| `profile_id` | No | Omitted | Actual `r_` +24 lowercase hexadecimal ID present in this collection |

```powershell
$page = Invoke-RestMethod -Uri "$baseUri/api/v1/observations/$collectionId/samples?offset=0&limit=5"
$page | ConvertTo-Json -Depth 12
```

Response schema: `ObservationPageResponse`. Top-level fields include `collection_id`, `source_id`, `dataset_id`, `data_mode`, `profile_id`, `offset`, `limit`, `total`, `next_offset`, `samples`, `display_only: false` and `comparison_result: false`.

Each sample preserves its ID/source indices, float/cycle/direction where present, time, longitude/latitude, pressure, depth when genuinely available, coordinate QC and per-variable values. Under `values.PRES`, `values.TEMP` and `values.PSAL`, inspect raw/adjusted values and QC, adjusted error, data mode, selected kind/value, eligibility and exclusions. Missing numeric values use null; missing depth is not zero metres.

**Pagination uses the returned `next_offset`, not a page number:**

| Example request, limit=5 | Returned samples | total | next_offset |
| --- | --- | --- | --- |
| offset=0 | 5 | 14 | 5 |
| offset=10 | 4 | 14 | null |
| offset=14 | 0 | 14 | null |

An empty page past the end is HTTP 200, not a provider failure. A well-formed but absent profile ID returns 404; the present Argo collection has no usable profile filter. With a real profile filter, `total` describes that filtered selection.

Sample pages return native scientific observations, not display-downsampled points. A small page can still validate/read the bounded underlying JSON collection; constant-time database paging is not promised. No region/date/variable/depth re-selection parameters are implemented on this endpoint.

## Errors and limits

### Application error body

For handled application errors and invalid parameters:

```json
{
  "schema_version": 1,
  "error": {
    "code": "invalid_request",
    "message": "Request parameters are invalid."
  }
}
```

Data responses and handled application errors use `schema_version: 1`. Health is the exception. Application routes/handled errors set `Cache-Control: no-store`; developer HTML/OpenAPI pages do not currently set that header. A `/ready` 503 uses its **readiness response schema**, not the general error envelope. Framework unknown-route/method errors may instead return `{"detail":"Not Found"}` or similar.

| HTTP | Example code / cause | What to do |
| --- | --- | --- |
| 404 | `not_prepared`: unknown/unavailable product; `profile_not_found`: absent profile | Rediscover actual IDs/capabilities; no automatic preparation is triggered |
| 409 | Changed/invalid local scientific product or collection | Operator checks provenance/files; do not treat as an empty dataset |
| 413 | `cell_limit` or `response_limit` | Smaller bbox/page or preview quality |
| 422 | `invalid_request`: missing/invalid parameter | Check required fields and bounds |
| 422 | `invalid_selection`: unavailable time index; `no_overlap`: point outside prepared support | Read metadata and use actual supported coordinates/times |
| 500 | Response contract/internal validation error | Inspect local backend diagnostics; do not expose private traces |
| 503 | `busy` or local configuration/storage unavailable | Retry boundedly for busy reads; fix configuration/storage for persistent errors |

Codes are examples, not an exhaustive list or proof every declared error is reachable on every route. Concurrent prepared NetCDF reads use a non-blocking per-process lock and can return `503 busy`; no background queue is implied.

| Limit | Current scope |
| --- | --- |
| 2 MiB | Serialized scientific/data JSON response |
| 16,384 cells | One scalar preview frame |
| 65,536 cells | One scientific surface frame |
| Up to 12 timestamps | Prepared surface product/time series; actual example has 3 |
| 1–500 samples | Observation page size |
| Up to 5,000 samples | One prepared observation collection |
| 32 / 64 entries | Observation collection / acquisition inventories |

Common mistakes:

- Omitting `time_index` from a frame request: it is required, with no default.
- Using `thetao` with the V2 SST/SSS product: variables belong to their actual prepared product.
- Sending only two bbox bounds: all four are required together.
- Passing a dataset/acquisition ID where a product ID is expected.
- Assuming HTTP 200, QC1 or `ready` means scientifically valid comparison.
- Adding undocumented query parameters: they may be ignored; this does not implement new filtering. Use only the listed contract.

## Comparison API — Part 5.9

Prepare explicitly from the project root, then start/restart the backend:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_comparison --accept-assumptions
```

The saved result is a historical snapshot, not a live source check. Preparation/reuse performs authenticated matching outside HTTP; no comparison POST/job/download endpoint exists.

- [Catalogue](http://127.0.0.1:8000/api/v1/comparisons): `ComparisonCatalogue`, up to 32 entries. `prepared_snapshot` means locally prepared availability, not scientifically verified readiness. Missing/corrupt entries retain a reason code.
- [Summary](http://127.0.0.1:8000/api/v1/comparisons/c_0abd2057c5bc5c41fcf49109): `ComparisonMetadata`, including preparation time, source IDs/dataset version, assumptions, blockers, counts and sample-weighted metrics.
- [Samples](http://127.0.0.1:8000/api/v1/comparisons/c_0abd2057c5bc5c41fcf49109/samples): `ComparisonPage`, including metadata and scientific rows. `offset` is 0–5000 (default 0); `limit` is 1–500 (default 100); optional `matched=true|false` filters before pagination.

For this snapshot, `?matched=true` returns 2 rows and `?matched=false` returns 12 exclusions. The unfiltered total is 14. `total` describes the filter; `metadata.summary` always describes all selected observations. Follow `next_offset`, which is null on the last page. Offsets beyond the total return an empty page.

Every page retains assumptions/limitations and false verification/independence flags. Unmatched residuals and zero-pair bias/RMSE are null, not zero. Status may be `blocked` or `partially_blocked` even with HTTP 200: the server successfully returned that scientific outcome. Private report/file hashes/stat records/reference text are omitted; an assumption identity is intentionally public. Full rows do not claim proven profile identities.

Missing comparison: 404; invalid ID/query: sanitized 422; changed/corrupt prepared result: 409; oversized response: 413; unavailable/over-capacity catalogue: 503. Service responses use `no-store` and at most 2 MiB JSON. No raw-source or private-report reads occur in handlers. See [full storage/verification contract](MILESTONE_5_9.md).

## Planned capabilities—not routes yet

| Capability | Current state / intended milestone |
| --- | --- |
| Copernicus model preparation | 5.2 contracts and 5.3 operator implementation complete; no model-serving route |
| Pressure/depth and quantity conversions | 5.4 read-only pressure-depth report complete; 5.5 adjusted quantity diagnostics complete, model temperature gate blocked; no HTTP routes |
| Strict scientifically verified comparison | Still blocked on unresolved scientific evidence; exploratory matching/metrics and prepared-result routes are separately implemented |
| End-to-end comparison acceptance | Planned 5.10 |
| Browser/globe frontend | Final, separately approved milestone |
| Depth slices, current vectors, volumes, exports or persistent preparation jobs | No current HTTP contract; do not invent endpoint paths |

`/api/v1/comparisons` is now implemented. The singular `/api/v1/comparison` alias remains absent. There are no application POST/PUT/PATCH/DELETE endpoints or raw-NetCDF HTTP download routes.

## Verification and maintenance

Current comparison verification is in [5.9](MILESTONE_5_9.md): new route schemas/OpenAPI, real saved-result pagination, 200/404/422 behavior and privacy/storage tests. OpenAPI contains 13 application paths. The following 10-route smoke record describes the earlier September 10 checkpoint, not the complete current route set.

This guide was checked against the current router code, response schemas and generated OpenAPI, rather than copied from the future frontend prompt. A read-only local TestClient smoke check exercised all 10 application routes, preview/scientific frames, first/final/empty sample pages and developer pages: **16 successful GET requests**. Additional checks observed seven application validation/missing-resource failures, three missing paths, unconfigured readiness 503 and all three developer paths returning 404 when disabled. Existing Starlette HTTPX deprecation warning remained visible.

This verifies local handler behavior and the listed payload examples—not a running network server, live provider availability, browser rendering, production security or the full test suite. No backend implementation, credentials, dataset contents or milestone approval was changed to create this guide.

Source-of-truth files:

- [Application factory and error handlers](../backend/app/main.py).
- [Comparison routes](../backend/app/api/comparisons.py), [public schemas](../backend/app/schemas/comparison_api.py), [prepared store](../backend/app/storage/comparisons.py).
- [Health route](../backend/app/api/health.py), [surface/readiness routes](../backend/app/api/products.py), [observation routes](../backend/app/api/observations.py), [acquisition inventory](../backend/app/api/acquisitions.py).
- [Surface response schemas](../backend/app/schemas/product_api.py), [observation response schemas](../backend/app/schemas/observation_api.py), [acquisition response schemas](../backend/app/schemas/acquisition_api.py).
- [Architecture](../ARCHITECTURE.md), [checkpoint order](../BACKEND_DEVELOPMENT_PLAN.md), [Part-5.1 audit](MILESTONE_5_1.md).

Update this guide whenever a route, parameter, response shape, limit or readiness meaning changes. After 5.9–5.10, add only the comparison routes that were actually implemented and verified. Generated `/openapi.json` remains the exact machine-readable API contract.
