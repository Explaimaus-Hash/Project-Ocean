# Project Ocean

## All-date surface archive — 2026-09-28

The user approved connecting every actual date in the downloaded BIO-ROMS V2 file to frontend viewing. Current implementation/preparation and verification are tracked in [the archive milestone](docs/BIO_ROMS_ARCHIVE.md). This supersedes earlier three-prepared-timestamp limits/status and no-new-preparation notes only for this local SST/SSS archive. No downloads, source/science-policy changes or comparison recomputation are authorized or implied.

## Current runnable integration — 2026-09-28

Timeline polish: ordinary frame/batch switching keeps a stable two-line caption (displayed source timestamp and available-frame count), without transient Requested/Buffering text. Playback still waits for the real rendered frame; actual errors and Retry remain visible.

Batch-transition follow-up: compatible batches retain the last labelled frame while loading, prefetch one next frame within existing cache limits, and preserve colour settings/scale. Prepared frames now use a short 480ms visual crossfade (skipped for reduced motion), with both timestamps labelled during blending; no intermediate scientific measurements are created. Graph headings and provenance wrap outside the plotting area; concise axis labels prevent overlap. See [verification and limitations](docs/FRONTEND_INTEGRATION.md#batch-transitions-and-graph-layout--2026-09-28).

Source time supports typed/calendar UTC entry plus Apply and the available-time list. The selected BIO-ROMS dataset now exposes all **480 actual source timestamps (1980-01-24 through 2019-12-25)** for SST/SSS across bounded products. Only exact available times are accepted; unavailable dates keep the previous selection. The frontend automatically chooses the owning batch. Analysis point-series charts remain selected-batch scope.

The supplied frontend has been recovered and integrated in `frontend/` with the existing FastAPI backend. See [run/restart instructions and verification scope](docs/FRONTEND_INTEGRATION.md). This is the current status; the dated checkpoints below are historical, including their earlier no-frontend/approval statements.

Working scope: Cesium globe, prepared BIO-ROMS SST/SSS, source timestamps/color controls, point time-series plots, 14 preserved Argo samples, source/acquisition inventory and the saved exploratory comparison (2 pairs/14 evaluated rows). No demo fallback. Unsupported scientific depth/current/volume/profile layers remain disabled. Original `Desktop/frontend` is unchanged. This is local integration, not production deployment or strict scientific validation.

Current checkpoint: approved [5.10 local backend verification](docs/MILESTONE_5_10.md). Fresh comparison replay matches the existing exploratory snapshot; six bounded BIO-ROMS raw samples match API output; all 13 application paths were checked over temporary loopback HTTP. No new dataset, science-policy change, frontend or deployment. Full regression evidence and remaining source/capability limits are in the milestone; older next-5.10/status paragraphs below are historical.

Read-only acceptance command (development dependencies required):

```powershell
.\ocean-env\Scripts\python.exe -m scripts.verify_comparison c_0abd2057c5bc5c41fcf49109 --accept-assumptions --page-size 5
```

This verifies an already prepared result, never creates/repairs one. It retains exploratory labels and blocked strict science; exit 0 means local consistency, not scientific readiness. After 5.10 acceptance, the next separately approved part is frontend real-payload/capability compatibility and the Earth-style shell; unsupported depth/current/profile/source features remain explicit.

Current milestone: [5.9 prepared comparison API](docs/MILESTONE_5_9.md) adds three read-only routes for saved exploratory summaries and paginated matched/excluded samples. Run `.\ocean-env\Scripts\python.exe -m scripts.prepare_comparison --accept-assumptions` explicitly to prepare/reuse a snapshot, then start/restart the backend. The existing real snapshot is `c_0abd2057c5bc5c41fcf49109` (2 pairs/14 rows). [Route guide](docs/API_ROUTES.md#comparison-api--part-59). HTTP never runs matching/downloads; strict science remains blocked. Next approval is 5.10; frontend is still last. Earlier no-comparison-API statements below are historical.

5.9 verification (2026-09-27): **1,003 tests passed, 4 Windows symlink skips**; project-configured lint, formatting and dependency checks passed. See the milestone for warnings, fixture/publication failure history and precise limits. Frontend and 5.10 remain unstarted.

Historical 5.8 checkpoint (2026-09-27): [exploratory salinity metrics](docs/MILESTONE_5_8.md) added model-minus-observation residuals, valid/excluded counts, bias and RMSE. Actual selection: 2 assumption-labelled pairs from 14 rows; bias +0.046519 and RMSE 0.046520 PSS-78. These are descriptive sample statistics, not independent validation. Strict verified mode remains blocked. The comparison API was added subsequently in 5.9; frontend remains unimplemented.

Run the read-only experiment from this build folder:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.run_exploratory_metrics --accept-assumptions
```

The bounded JSON retains the full matching evidence, assumptions, original strict blockers and exclusions. `comparison_ready` stays false; empty matches yield null metrics. This CLI reruns authenticated matching without writes or downloads. `scripts.run_exploratory_matching` remains the pair-only command, and `scripts.run_local_matching` the strict blocked path. See [5.8 usage/limits](docs/MILESTONE_5_8.md) and [5.7 assumptions/source citations](docs/MILESTONE_5_7_EXPLORATORY.md).

Build folder: `C:\Users\pc\OneDrive\Desktop\ocean_2`. Backend first; frontend last. Work proceeds one approved part at a time, with a short completion summary and permission before the next part. See [BACKEND_DEVELOPMENT_PLAN.md](BACKEND_DEVELOPMENT_PLAN.md).

Project Ocean is a planned browser-based, interactive 3D ocean data visualization system for INCOIS use. It brings INCOIS and Copernicus ocean model fields together with Argo float and IFREMER glider observations, and supports comparison where location, depth, time, and scientific variable overlap.

## Start here

Read these files in order:

1. [README.md](README.md): purpose, status, stack, and setup.
2. [ARCHITECTURE.md](ARCHITECTURE.md): components, data flow, source details, and design decisions with reasons.
3. [FILE_STRUCTURE.md](FILE_STRUCTURE.md): where each module belongs.
4. [CONVENTIONS.md](CONVENTIONS.md): naming, scientific data rules, and implementation patterns.

Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for carried-over decisions. Keep [FRONTEND_IMPLEMENTATION_PROMPT.md](FRONTEND_IMPLEMENTATION_PROMPT.md) for the final, separately approved frontend part; it is not the next coding task.

For another coding agent, use [the handoff file list and checkpoint prompts](docs/CODING_AGENT_HANDOFF_PROMPTS.md). It starts with read-only onboarding and requires fresh approval before each remaining5.7 checkpoint and Parts5.8–5.10; sharing the prompts is not implementation approval.

For implemented endpoints, parameters, ready-to-open examples, pagination and errors, read the [API Route Guide](docs/API_ROUTES.md). It separates today's working routes from planned comparison/depth capabilities.

## Current status

2026-09-26 evidence update: human Copernicus support confirmed the EOS-80 potential-temperature framework, but exact midnight-label intervals and the observation/model depth relationship remain unresolved; temperature scale/reference pressure also remains unconfirmed. A concrete follow-up was sent and verified. See the [reply assessment](docs/MILESTONE_5_7_EXECUTION.md#human-reply-assessment--2026-09-26). This does not enable real matching or complete 5.7; 5.8 has not started.

Latest: [5.7-C guarded local execution](docs/MILESTONE_5_7_EXECUTION.md) connects verified model fields, Argo quantities/adjusted depths and static diagnostics to the engine. Run `.\ocean-env\Scripts\python.exe -m scripts.run_local_matching`; exit 3 means a valid **blocked** report. Salinity and temperature were checked locally; neither produces real pairs while scientific support remains unresolved. This is integration scaffolding with enforced gates, not completion of all 5.7.

Latest continuation: [5.7-B candidate-bound spatial diagnostics](docs/MILESTONE_5_7_SPATIAL_SUPPORT.md) implemented. The verified real audit reports 5 inside/9 outside Argo rows, nearest-cell and surrounding-grid masks, full-mask wet-depth coordinates and separate bottom metadata. It does not certify observation wetness/connectivity or produce pairs. Remaining 5.7-B scientific decisions precede 5.7-C integration.

Run `.\ocean-env\Scripts\python.exe -m scripts.audit_spatial_support` for this local read-only diagnostic. Exit 3 means a valid blocked diagnostic, not a failure or completed comparison. No new download is needed.

Preceding 5.7-A: [verified offline static-support reader](docs/MILESTONE_5_7_STATIC_READER.md) replays 59 original source objects and verifies 8,450 mask values, exact model binding and subset metadata without downloading or changing inputs. It is reused by 5.7-B; real matching remains disabled.

To inspect the saved support locally, run `.\ocean-env\Scripts\python.exe -m scripts.inspect_static_support` from the build root. Exit 0 means verified static inputs only; `comparison_ready` remains false. The existing matching audit still reports unresolved scientific gates.

Part 5.7 now includes a **verified local input reader/audit** alongside the synthetic matching kernel and adjusted-pressure depth bridge. The audit verifies native model fields and adjusted-depth alignment but does not search real pairs; unresolved time/wet/bottom/connectivity/vertical-reference evidence keeps real matching disabled. No metrics, comparison API or frontend were added. [Current checkpoint](docs/MILESTONE_5_7_READER.md), [earlier kernel evidence](docs/MILESTONE_5_7.md). Ask permission to continue remaining 5.7 before moving to 5.8.

Part 5.1's [scientific audit](docs/MILESTONE_5_1.md) identified five horizontal candidates, not pairs. Parts 5.4–5.5 subsequently added separate depth/quantity diagnostics; 5.6 preserves remaining scientific gates without altering raw collections or model products.

Parts 1–4 now provide independent health, bounded BIO-ROMS surface preparation/APIs, operator-only GODAS/Copernicus/Argo/glider acquisition, and QC-preserving observation normalization/storage/APIs. The real V2 SST/SSS product remains available. Source-by-source live results and limits are in [docs/MILESTONE_4.md](docs/MILESTONE_4.md); [part 3](docs/MILESTONE_3.md) and earlier milestone files preserve their historical checkpoints.

Python 3.12.10 and `ocean-env` contain pinned scientific/provider dependencies. Bella FTP acquisition has now been repeated successfully here, but its time-range metadata conflict prevents scientific readiness. GODAS still timed out. Copernicus authentication and a 54,832-byte four-field model subset succeeded in the 2026-09-10 follow-up, using temporary process credentials without a saved login file. A separate native scientific product is now prepared in 5.3; model-serving APIs remain unimplemented. Do not confuse accepted authentication or a small download with every provider/selection being ready.

Health, `/ready`, dataset/product discovery, bounded surface frames, and scientific grid-cell time series can run now. Registry entries preserve all four source families; acquisition and observation catalogues are separate from prepared surface products. Scientific comparison, prepared depth/volume/current serving, and frontend remain later work. Health/startup and offline tests need no downloaded ocean dataset or provider credentials.

The completed local V2 is 9,248,080,750 bytes and matches the published MD5. Actual fields include SST, SSS, MLD, DIC, CHL, NO3, three pCO2 products, and deviant uncertainty, all on TIME/LAT/LON without a vertical dimension. The first prepared selection contains SST/SSS for the three source timestamps in January–March 2019. Original source bytes are unchanged. Backend measurements exist; browser/globe performance is not yet measured.

## Required capabilities

- Interactive 3D volumetric views, depth slices, and current vectors.
- Time animation and customizable colorbars with variable names and units.
- Argo and glider overlays with click-to-inspect profiles.
- Model-versus-observation comparisons with explicit matching tolerances.
- Modular ingestion, browser deployment, and later support for CTD, BGC observations, moorings, HF radar, and ADCP.

The common comparison region is longitude **30°E–120°E**, latitude **30°S–30°N**. It is a project selection box; individual datasets can cover different areas and periods. Integration of all four source families does not imply that every dataset has a common comparison window.

## Tech stack

| Layer | Technology | Status |
| --- | --- | --- |
| Scientific runtime | Python 3.12 in `ocean-env` | Preserved project preference |
| Local metadata inspection | netCDF4 1.7.4, NumPy 2.5.3, PyYAML 6.0.3 | Installed/pinned; header-only CLI tested with tiny synthetic files |
| Surface preparation | netCDF4 + NumPy + cftime | Bounded frame-wise processing, source masks/packing and actual time decoding implemented |
| Scientific/source extensions | xarray 2025.9.0, pandas 3.0.5, pydap 3.5.10 | Installed/pinned; bounded operator adapters, not startup imports |
| Copernicus access | Official `copernicusmarine` 2.4.1 | Acquisition verified; small native model prepared in 5.3; API serving/comparison pending |
| Argo access | Argopy 1.4.0, erddapy 3.2.1 | Expert core acquisition with provider-response preservation and QC-aware normalization |
| Glider access | Standard-library `ftplib`, followed by xarray | Real Bella download repeated; metadata/QC constraints remain explicit |
| Scientific conversions | GSW 3.6.23 / TEOS-10 | Pressure-depth and adjusted Argo quantity modules/read-only reports implemented; real model temperature compatibility remains blocked |
| Backend API | FastAPI 0.141.1 + Uvicorn 0.52.4 | Health, configured readiness, catalogue, metadata, surface frames and point time series |
| API settings and schema | Pydantic / pydantic-settings | Typed versioned request/response contracts; process-only settings |
| Backend tests and formatting | pytest, HTTPX, Ruff | Installed and configured; pinned in development requirements |
| Browser application | Next.js, React, TypeScript | Frontend build baseline; not implemented |
| Main geographic renderer | CesiumJS | Selected for the requested Google Earth-style globe; not implemented |
| Scientific charts | Plotly.js with its React integration | Selected frontend baseline; not implemented |
| Dedicated volume renderer | Optional Three.js | Add only if a volume prototype establishes a need; not the main globe |
| Storage | Immutable acquired inputs, surface scientific/previews, observation JSON snapshots and typed manifests | Local bounded storage; no database or persistent job queue |

The frontend direction remains a Google Earth-style CesiumJS globe with Next.js/React/TypeScript and Plotly charts, built last. The current FastAPI data routes serve prepared surface data only; a successful health response never establishes dataset readiness or vertical capability.

## Data sources

| Source | Role | Access and current knowledge |
| --- | --- | --- |
| INCOIS BIO-ROMS | Physical/biogeochemical model products | Local V2 checksum/header/axes verified; SST/SSS January–March 2019 prepared. Other fields are confirmed but not prepared in this checkpoint. |
| INCOIS GODAS | Physical ocean model | Yearly 2022–2025 endpoints recorded; inspect actual variables and coordinates before integration. |
| Copernicus Marine | Physical ocean model | Product `GLOBAL_MULTIYEAR_PHY_001_030`; use the official toolbox and verify the selected dataset/version. |
| Argo Global | In-situ float profiles | Official Argo GDAC/services; Argopy is the access client. Historical and recent observations are available, subject to coverage. |
| IFREMER Gliders | In-situ tracks and profiles | Real Bella FTP file acquired; conflicting TIME valid range and missing QC are not overridden. |

Exact endpoints, sample metadata, and test limitations are retained in [ARCHITECTURE.md](ARCHITECTURE.md).

BIO-ROMS variable availability is not limited by the corrected-pCO₂ filename. The authors' [v2 product description](https://zenodo.org/records/14614739) documents the additional fields and recommends v2 over the deprecated v1. Published product metadata is verified; the exact contents/version exposed by the recorded LAS endpoint remain uninspected.

## Prepare the Python environment now

Open Windows PowerShell in the confirmed build folder. The environment already exists on this machine; reuse it. On a fresh copy only, run `py -3.12 -m venv ocean-env` first. Run commands one at a time after the previous succeeds; explicit paths prevent installation into global Python:

```powershell
Set-Location -LiteralPath 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe --version
.\ocean-env\Scripts\python.exe -m pip install -r .\backend\requirements-dev.txt
.\ocean-env\Scripts\python.exe -m pip check
```

Expect Python 3.12.x. Activation is optional. Development requirements include runtime requirements plus pytest, HTTPX, and Ruff. A runtime-only installation can use `backend/requirements.txt`. Part 2 adds netCDF4, NumPy, cftime, and PyYAML for explicit local inspection; scientific/provider modules are not imported by API startup. Part 4 installs the provider clients and xarray together; they are loaded only by explicit data operations. Standard-library `ftplib` requires no separate installation.

Runtime and development dependencies are pinned separately for this Windows/Python-3.12 build. Before later scientific integration, resolve those packages together and verify imports and tiny NetCDF reads; do not independently upgrade xarray past the selected Argopy constraints. [Argopy installation documentation](https://argopy.readthedocs.io/en/latest/install.html).

Part 3 keeps direct netCDF4 frame/chunk-cache control for the inspected V2 surface input. Part 4 adds lazy xarray/provider adapters without replacing that processor or moving ingestion into the API. Synthetic tests and live-source checks remain separately documented.

The `_quote_string_constraints` import error reproduced here with Python 3.12, Argopy 1.4.0 and erddapy 3.3.0. Pinning erddapy 3.2.1 restored imports in this build; Python 3.12 alone is not the complete fix. Keep xarray within Argopy's selected compatibility range and rerun tests before upgrades.

## Credentials and local data

Copernicus authentication belongs in the server environment. The toolbox reads `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`. Website visitors should not run `copernicusmarine login`. Keep credentials out of Git, logs, and all `NEXT_PUBLIC_*` variables. [Official toolbox environment variables](https://toolbox-docs.marine.copernicus.eu/en/stable/usage/environment-variables.html).

The installed toolbox also has its own login command, but this application's adapter deliberately requires the two process environment variables and does not rely on saved account files or interactive prompts. Supply them through a local server/operator session or deployment secret configuration; never include values in request JSON or browser code. [Official toolbox credential documentation](https://toolbox-docs.marine.copernicus.eu/en/stable/usage/environment-variables.html).

Preserve the completed V2 file under `data/raw/incois/bio_roms/v2/`; its final filename and published checksum are configured in `config/data_sources.yaml`. A normal Zenodo download retrieves the complete file; later selected-region extraction happens on the backend. Part 4 adds explicit local LAS-export imports and GODAS OPeNDAP acquisition; the existing BIO-ROMS LAS endpoint still needs its own live metadata/version check. Keep all raw datasets outside the frontend's public directory.

## Inspect local inputs

From the build root, list configured input states without reading their file contents or contacting providers:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.inspect_dataset status
```

`status` intentionally checks final-path existence/locality only. It now reports this completed V2 as `uninspected` for that request; it does not reuse saved findings or describe prepared products. Before download completion it returned `unavailable` / `file_missing`. Partial filenames remain ignored. Remote entries in this local-only inspector report `not_configured` / `local_inspection_not_applicable`, not a failed provider connection or a missing acquisition adapter. Use the HTTP catalogue below for prepared-product availability.

The completed, verified input is at:

```text
C:\Users\pc\OneDrive\Desktop\ocean_2\data\raw\incois\bio_roms\v2\pCO2-Corrected_INCOIS-BIO-ROMS_v2.nc
```

The following command has already verified this download and saved `data/metadata/incois_bio_roms_v2.json`. Repeat it only when re-verification is needed. `--verify-checksum` reads the complete file sequentially in 1 MiB blocks and can take time; header inspection itself does not read variable arrays. `--save` writes or replaces this dataset's private inspection report.

```powershell
.\ocean-env\Scripts\python.exe -m scripts.inspect_dataset inspect incois_bio_roms_v2 --verify-checksum --save
```

Successful inspection returns `not_prepared`, never `ready`: names, dimensions, units, calendars, packing/fill/QC attributes, and coordinate hints are inventoried, but no axis values, actual coverage, QC decisions, or rendering capabilities are validated. Omitting `--verify-checksum` leaves `checksum_status: not_checked`; omitting `--save` prints JSON only. Inspection returns exit code 0 on metadata success or 2 on missing/invalid/unsupported input. `status` exits 0 when the registry is valid, even when data is unavailable, and does not reuse saved reports as current readiness. See [part-2 limits and checks](docs/MILESTONE_2.md).

## Prepare a bounded selection

The first real product is already prepared. This repeatable command validates the saved verified inspection against the current source stat identity, then reuses an unchanged matching product or creates a new immutable selection:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_bio_roms --variables SST SSS --west 30 --east 120 --south -30 --north 30 --start 2019-01-01 --end 2019-03-31
```

Current product ID: `p_7c8210052d41d41259724e2d`. Actual timestamps: `2019-01-29T00:00:00Z`, `2019-02-28T00:00:00Z`, `2019-03-30T00:00:00Z`—not invented month-start timestamps. Scientific shape is `3 × 756 × 1081`; the separate display preview uses stride 8 (`95 × 136` per frame). Raw resolution is preserved in the scientific product.

Outputs are `data/processed/<product_id>/fields.nc`, its private `manifest.json`, and `data/cache/<product_id>/preview.nc`. The current compressed scientific file is 10,093,402 bytes; the separate preview file is 233,615 bytes. Neither is directly served as a public static file. Requests use the APIs below.

Change dates/variables/bounds for another selection. Limits allow at most 4 variables, 12 source timestamps, a 366-day span, and 8 million selected variable-values per job; larger work must be split explicitly. Inverted/dateline bounds, unsupported grids/units/calendars, stale inspection, and selections with no samples fail clearly. The operator does not silently reduce scientific resolution, redownload data, overwrite conflicting products, or run at API startup. See [processing limits](docs/MILESTONE_3.md).

## Local BIO-ROMS data and smooth interaction

The [recommended V2 file](https://zenodo.org/records/14614739) is approximately 9.2 GB and already covers the regional box 30°E–120°E, 30°S–30°N. For that full box, reduce the requested dates/variables and display resolution; for a smaller box, also crop geographically. File size on disk is not the browser download size.

Prepare data once: verify the file, inspect metadata, select a small starting period and variables, and create scientific subsets plus lightweight display products. Read bounded portions instead of loading the complete dataset into RAM. The globe opens independently, and each layer loads when requested. Repeated selections use caches; a small nearby-frame buffer supports animation. Large analysis/export preparation runs outside interactive API handlers.

Maps can show a labeled preview and then refine its detail. Click inspection and comparison use the scientific samples, with units, QC, and source identity preserved. A slower network or device may reduce display detail without changing the scientific result. See [ARCHITECTURE.md](ARCHITECTURE.md) for the canonical processing rules and measurable UX targets.

## Run the backend now

From the build root, after installing the requirements above:

```powershell
$env:OCEAN_REQUIRED_PRODUCT_IDS = '["p_7c8210052d41d41259724e2d"]'
.\ocean-env\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend/app
```

Open [health](http://127.0.0.1:8000/health) or [developer API docs](http://127.0.0.1:8000/docs). The root `/` has no page. Stop the server with Ctrl+C. If port 8000 is already occupied, use a different free port and update the browser URL; do not kill an unrelated process. Uvicorn is used directly to keep this first runtime small. [Official manual-server guidance](https://fastapi.tiangolo.com/deployment/manually/).

Use `/docs` for the typed request/response contracts or open the [dataset catalogue](http://127.0.0.1:8000/api/v1/datasets). For the current product:

- [SST preview frame](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/frame?variable=SST&time_index=0).
- [Scientific SST time series at 70E, 0N](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/timeseries?variable=SST&longitude=70&latitude=0).
- [Small scientific SST frame](http://127.0.0.1:8000/api/v1/products/p_7c8210052d41d41259724e2d/frame?variable=SST&time_index=0&quality=scientific&west=60&east=61&south=0&north=1).

Frames contain actual axes/time/units, masks represented by `null`, source/processing identity, and display-policy labels. Scientific frames are limited to 65,536 cells; the complete comparison-box frame must use preview or a smaller scientific region. Point series use the nearest grid cell in actual prepared support without jumping to another wet cell; this is not model-observation matching. Missing cells remain missing. Region filters return only intersecting prepared cell centres, with actual returned axes visible.

Run checks from the same project root:

```powershell
.\ocean-env\Scripts\python.exe -m pytest -c .\backend\pyproject.toml
.\ocean-env\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m ruff format --check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m pip check
```

Development-only, read-only real-product verification and 30 repeated in-process API measurements:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.verify_product p_7c8210052d41d41259724e2d --check-raw
```

This compares a bounded point series with the original source and does not modify files. It is not a browser benchmark. See [measured results and limitations](docs/performance.md).

There is no frontend or Node.js requirement yet. Next.js/Cesium/Plotly setup, explicit permitted CORS origins, and browser API configuration will be added in the final frontend part. No wildcard CORS policy has been enabled.

### Configuration

`OCEAN_DOCS_ENABLED` defaults to `true`. Set `$env:OCEAN_DOCS_ENABLED = 'false'` before starting the server to disable `/docs`, its OAuth redirect, and `/openapi.json` together; `/health` remains enabled. Restore `true` and restart to re-enable developer docs. `/redoc` is not enabled. Debug mode is off.

Settings read the process environment only: `backend/.env.example` is a safe reference, not an automatically loaded file. Application construction reads no `.env`, source credentials, or dataset files; prepared-data reads happen only in their explicit requests. The default Swagger HTML uses external CDN assets, so its interactive browser UI needs internet unless assets are self-hosted later; `/health`, `/openapi.json`, and in-process tests do not require upstream services.

`OCEAN_PROJECT_ROOT` optionally selects an absolute trusted project root; otherwise the application's own folder is used. `OCEAN_REQUIRED_PRODUCT_IDS` is a JSON list of up to 16 unique prepared product IDs. The default empty list makes `/ready` return 503 (`required_products_not_configured`), even if files exist. The run example explicitly requires the verified real starting product. No process settings are persisted by the code.

## Simple backend health check

The backend has a plain JSON health endpoint; no separate styled health page is needed:

| Route | Purpose |
| --- | --- |
| `GET /health` | Implemented: HTTP 200 liveness JSON with `Cache-Control: no-store`. |
| `GET /ready` | Implemented: 200 only when configured required real products have valid bounded manifests and unchanged readable local output files; otherwise 503. |
| `/docs`, `/openapi.json` | Implemented developer docs/schema, enabled by default; not data-readiness checks. |

Actual `/health` response:

```json
{
  "status": "ok",
  "service": "Project Ocean Backend"
}
```

`/health` does not contact providers, open files, or start processing. `/ready` uses bounded manifest/stat/one-byte output-access checks, not raw-file reads, checksum scans, NetCDF decoding, or provider requests. Optional source outages are not global readiness requirements. Startup performs none of this data work. The full contract is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Source acquisition and observations

### Prepare or verify the local native model

From the build root, using the existing Python environment:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_model --request config/model_preparation.example.json
```

This operator command uses the already downloaded acquisition; no credentials or network are needed. The current request produces/reuses `m_35e4c0ab33c1469a334ca837` in `data/models/`, preserving native scientific values and source metadata. Reuse verifies hashes and source readback; it is not a cheap API request. No model-serving route or comparison is enabled. See [5.3 evidence/limits](docs/MILESTONE_5_3.md).

### Read-only pressure-derived depths

After installing updated runtime requirements into `ocean-env`, this command prints a separate JSON report; it does not save or overwrite data:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.convert_observation_depth --collection-id o_c645f248f801845378f0fdaf --reference-evidence "Argo PRES sea-pressure definition; provider audit in docs/MILESTONE_5_1.md" --assume-zero-geopotential
```

The explicit assumption uses zero dynamic height and surface geopotential. Current raw pressure selection is preserved; adjusted errors remain recorded but are not applied to raw pressures. Pressure-only endpoint ranges are not complete uncertainty or confidence intervals. Model vertical compatibility and matching remain later work; quantity diagnostics are now available through the separate 5.5 command. [Scope, tests and results](docs/MILESTONE_5_4.md).

### Read-only adjusted quantity diagnostics

```powershell
.\ocean-env\Scripts\python.exe -m scripts.audit_quantities --collection-id o_c645f248f801845378f0fdaf --acquisition-id a_d30181bd8998aca81bb33be1 --model-id m_35e4c0ab33c1469a334ca837
```

This separate operator report verifies saved provider rows and selects adjusted A/D values without rewriting the raw collection. It derives supported observation quantities, preserves errors/QC, and blocks unresolved model temperature definitions. No matches, model field reads, provider login, API or frontend are involved. [5.5 policies and results](docs/MILESTONE_5_5.md).

### Read-only matching-policy preflight

```powershell
.\ocean-env\Scripts\python.exe -m scripts.check_matching_policy
```

This reads `config/comparison.yaml` and verifies the existing local inputs; it does not search for pairs or write data. Current real data returns **exit3 / blocked** for unresolved reviewed limits and scientific support evidence, not no-overlap. Exit2 is an input/verification error; exit0 would mean policy requirements satisfied only. All collocation limits remain intentionally unset until justified for this selection. [Canonical policy](docs/MATCHING_POLICY.md), [5.6 evidence](docs/MILESTONE_5_6.md).

### Read-only native matching-input audit

```powershell
.\ocean-env\Scripts\python.exe -m scripts.audit_matching_inputs
```

This additional operator audit verifies prepared native field values/masks, axes and file identity, then checks adjusted observation-depth alignment without rewriting sources or calling the matching engine. Current real salinity output is `inputs_verified_matching_blocked`: 2,704 finite native values, 14 converted central depths, 12 evaluated pressure-error endpoint ranges and nine remaining blockers. **Exit3** means verification completed but matching is still blocked; **exit2** means input verification failed. A missing-value mask is not wet/bottom/coastline evidence, and adjusted-depth alignment is not model-datum compatibility. The original policy preflight above stays unchanged. [Reader scope and verification](docs/MILESTONE_5_7_READER.md).

### Existing source and observation workflow

Part 4 adds explicit acquisition and observation preparation commands, with safe JSON examples in `config/`. Follow [the operator guide and live-source limitations](docs/MILESTONE_4.md). Inspect `/api/v1/acquisitions` for acquired inputs and `/api/v1/observations` for scientific collections. Metadata and paged samples use `/api/v1/observations/{collection_id}` and its `/samples` route; at most 500 samples and 2 MiB per response, with raw/adjusted values and QC retained. Nothing downloads from an HTTP request, startup or health.

Real Argo collection `o_c645f248f801845378f0fdaf` now serves 14 January 29, 2019 near-surface points from two floats, with exact raw/adjusted-value checks against the preserved provider response. [Open the local scientific sample page](http://127.0.0.1:8000/api/v1/observations/o_c645f248f801845378f0fdaf/samples?limit=100) after starting the backend. These points are not claimed as uniquely identified profiles or completed model-observation comparisons.

Latest part-4 follow-up verification: 386 tests passed, four Windows symlink-permission tests skipped; Ruff/format and dependency checks pass. Known third-party warnings and the earlier intermittent preparation-test finding are retained in the [verification record](docs/MILESTONE_4.md), not described as guarantees of error-free production behavior.

Copernicus acquisition `a_9e918d43555ffc26d3659e08` contains `thetao`, `so`, `uo`, `vo` over 65–66E/1S–0N, Jan29–30 2019, at eight actual model depths from approximately 0.494 to 9.573 m. Each field is `2 × 8 × 13 × 13`; this is a tiny verified selection, not the entire comparison box or full water column. Use the [bounded operator example](config/acquisition.copernicus.example.json) with privately supplied process credentials. Do not infer observation compatibility or new depth/current APIs from this acquired input. The failed earlier attempt's private staging residue and access limits are documented in the milestone.

A downloaded file is not automatically ready data: each model selection needs a supported preparation pipeline (the small Copernicus selection now has one), and observations must pass metadata/alignment rules. Missing or rejected QC is visible. Browser profiles require an actual profile ID; ambiguous points remain points. Quantity diagnostics are implemented in 5.5; 5.7's synthetic matching kernel does not enable real comparison.

## Next part — frontend remains permission-gated

The user approved **5.10 local backend verification**; use its latest milestone for results. Next, ask before **Part 6 frontend**, starting with real API payload/capability compatibility. Do not infer support for missing depth/current routes, usable glider data or independent scientific comparison. The older 5.7 instructions below describe preceding checkpoints and do not request a repeated build or download.

The [bounded static acquisition](docs/MILESTONE_5_7_STATIC_ACQUISITION.md) is complete for65–66E/1S–0N. Next: verify/read that saved support snapshot and integrate explicit mask/bottom/connectivity evidence without changing time/reference/tolerance gates. No provider clarification has been sent. Further5.7 work requires approval.

Continue **5.7 — verified scientific support and real integration** only after permission; the local reader/audit is not completion of the full matching integration. Real collocation limits, daily-time support, masks, vertical reference and model temperature compatibility remain gates. The adjusted-depth bridge does not establish a shared model datum. Metrics (5.8), comparison API (5.9), end-to-end verification (5.10) and frontend remain later, separately approved work.

Before calling a feature complete, demonstrate it with metadata and QC preserved, bounded browser payloads, and meaningful empty/error states. Record precisely what was tested and whether the data was local, cached, synthetic, or fetched live.
