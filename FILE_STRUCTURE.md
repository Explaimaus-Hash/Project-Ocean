# Project Ocean File Structure

## All-date surface archive additions

- `scripts/prepare_bio_roms_archive.py` — explicit resumable verified-local SST/SSS preparation in four-source-date batches.
- `scripts/verify_bio_roms_archive.py` — read-only source-axis versus live HTTP archive coverage and native/preview spot-value verification.
- `backend/tests/test_archive_batches.py` — archive planning and resource-bound regressions.
- `docs/BIO_ROMS_ARCHIVE.md` — all-date preparation, source coverage, verification and limitations.

## Current additions — recovered frontend integration

- `frontend/src/features/controls/SourceTimeControl.tsx` — UTC date/time draft, strict calendar and prepared-timestamp membership validation, Apply/error state and available source-time picker.

- `frontend/src/app/` — Next routes, global styles and workspace entry points.
- `frontend/src/components/` — shared workspace shell, controls, timeline and status UI.
- `frontend/src/features/` — globe/scalar layers, observations, analysis, comparison and source inventory.
- `frontend/src/lib/` — bounded client, FastAPI adapter/validators, selection and display models; old demo fixtures are not the live transport.
- `frontend/tests/live-integration.spec.ts` — actual local API/browser regression checks; earlier recovered tests are historical fixtures, not current acceptance evidence.
- `frontend/playwright.live.config.ts` — Edge loopback test configuration, requiring running local servers.
- `frontend/public/` — generated local Cesium/Plotly assets from locked packages.
- `scripts/recover_frontend_source.mjs` — read-only source-map/handoff recovery inventory/export, not a runtime dependency.
- `docs/FRONTEND_RECOVERY_MANIFEST.json` — 99 recovered files with baseline origin/hash, before integration changes.
- `docs/FRONTEND_INTEGRATION.md` — current run instructions, scope, verification and recovery caveats.

These additions supersede earlier no-frontend checkpoint statements below.

## Latest additions — 5.10 local backend verification

- `scripts/verify_comparison.py` — opt-in read-only authenticated replay, saved-snapshot/API consistency checks and 30-request in-process measurement.
- `backend/tests/test_comparison_verification.py` — synthetic verifier tests for paging, preservation, corruption, replay/policy mismatch, HTTP failures and safe CLI output.
- `docs/MILESTONE_5_10.md` — real workflow/loopback evidence, performance scope, regression and remaining capability boundaries.

No production route, dependency, dataset directory or frontend was added. `docs/performance.md` retains the measured backend-only scope.

## Latest additions — 5.9 prepared comparison API

- `backend/app/schemas/comparison_api.py` — public metadata/sample/page/catalogue contracts plus private publication manifest.
- `backend/app/storage/comparisons.py` — bounded prepared-result reads, explicit public projection and immutable operator publication/reuse.
- `backend/app/api/comparisons.py` — read-only comparison catalogue, metadata and filtered sample-page routes.
- `scripts/prepare_comparison.py` — explicit assumption-approved matching/metrics preparation and snapshot publication; no input-report upload.
- `backend/tests/test_comparison_api.py` — storage/publication, privacy, paging, errors, bounds and HTTP isolation tests.
- `data/comparisons/<comparison_id>/` — private `report.json`, public-projection `result.json` and private manifest; no files served directly.
- `docs/MILESTONE_5_9.md` — operator/API contract, real snapshot, limits, verification and next approval.

`main.py` registers the three new routes and lightweight store; startup still performs no filesystem/scientific work. No dependency or frontend was added. Earlier no-API notes below are historical.

## Latest additions — 5.8 exploratory metrics

- `backend/app/schemas/comparison_metrics.py` — private residual/summary/report contracts with finite stable arithmetic and consistency validation.
- `backend/app/comparison/metrics.py` — pure assumption-preserving summaries and an authenticated read-only local execution wrapper.
- `scripts/run_exploratory_metrics.py` — explicit opt-in CLI for bounded residual/count/bias/RMSE JSON; no saved-report input or writes.
- `backend/tests/test_comparison_metrics.py` — arithmetic, empty/partial/blocked outcomes, assurance, tampering, bounds and operator regressions.
- `docs/MILESTONE_5_8.md` — formulas, actual local metrics, limitations, commands, verification and next approval boundary.

No dependency, data directory or HTTP route was added. Earlier “no metrics” notes below refer to earlier checkpoints.

## Latest additions — 5.7 exploratory matching

- `backend/app/comparison/exploratory.py` — separate assumption-labelled shallow salinity matching and authenticated operator adapter.
- `backend/app/schemas/exploratory_matching.py` — immutable assumption version and report contract, distinct from verified results.
- `scripts/run_exploratory_matching.py` — read-only bounded JSON CLI requiring `--accept-assumptions`.
- `backend/tests/test_exploratory_matching.py` — offline QC, identity, support, endpoint, no-fallback, assurance and CLI regressions.
- `docs/MILESTONE_5_7_EXPLORATORY.md` — current scope, primary-source checks, assumptions, actual pairs and verification.
- `backend/app/comparison/execution.py` — shared authenticated input assembly/postchecks plus unchanged strict blocked execution.
- `backend/app/comparison/matching.py` — strict guarded engine and shared numerical candidate selection; no exploratory evidence promotion.

Earlier file/status notes below describe preceding checkpoints. No comparison API, metrics or frontend was added.

## What exists in the build folder

Build root: `C:/Users/pc/OneDrive/Desktop/ocean_2`. Parts 1–4 provide independent health, bounded surface preparation/APIs, explicit source acquisition and scientific observation QC/storage/APIs. Frontend is the final separately approved part. Earlier documentation copies and the older `ocean` project remain untouched.

| File | Purpose |
| --- | --- |
| [README.md](README.md) | First read: purpose, actual implementation status, stack, and working backend run/test commands. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Source facts, component boundaries, data flow, scientific contracts, and decision rationale. |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md) | One-line ownership map for project files and modules. |
| [CONVENTIONS.md](CONVENTIONS.md) | Adopted backend naming/formatting/testing rules and future scientific/frontend patterns. |
| [FRONTEND_IMPLEMENTATION_PROMPT.md](FRONTEND_IMPLEMENTATION_PROMPT.md) | Reusable build prompt for the Earth-style launch, globe explorer, analysis, profiles, and comparison. |
| [AGENTS.md](AGENTS.md) | Build-root boundaries, required context, and the user's permission gate between parts. |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Current location, retained decisions, history references, and implementation boundaries. |
| [BACKEND_DEVELOPMENT_PLAN.md](BACKEND_DEVELOPMENT_PLAN.md) | Ordered backend parts with frontend last and approval required between parts. |
| [docs/CODING_AGENT_HANDOFF_PROMPTS.md](docs/CODING_AGENT_HANDOFF_PROMPTS.md) | Required handoff files and separate approval-gated prompts for remaining5.7 and5.8–5.10. |
| [docs/API_ROUTES.md](docs/API_ROUTES.md) | Verified current route reference with setup, parameters, sample URLs, pagination, errors and explicitly separate planned capabilities. |
| [docs/MILESTONE_1.md](docs/MILESTONE_1.md) | Exact part-1 verification results, dependency warnings, and remaining work. |
| [docs/MILESTONE_2.md](docs/MILESTONE_2.md) | Registry/metadata inspection checks, commands, states, and explicit scientific limitations. |
| [docs/MILESTONE_3.md](docs/MILESTONE_3.md) | Real V2 verification, bounded preparation/API evidence, readiness contract, and remaining scientific limits. |
| [docs/MILESTONE_5_1.md](docs/MILESTONE_5_1.md) | Read-only Copernicus/Argo compatibility audit, actual candidate overlap, metadata discrepancies and gates before comparison. |
| [docs/performance.md](docs/performance.md) | Measured local preparation/API scope and payloads, separate from unmeasured browser targets. |
| [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md) | Original user-provided requirements, not implemented-feature claims. |

The documents above, `.gitignore`, the local `ocean-env` environment, and the files below exist. The 9,248,080,750-byte V2 file has been checksum-verified and inspected. One real SST/SSS selection for January–March 2019 is prepared as `p_7c8210052d41d41259724e2d`; this does not prepare every source variable/date. Part 4 adds observation integration with actual source limitations recorded in docs/MILESTONE_4.md; real comparison and frontend are not implemented; the private synthetic matching kernel is listed below.

| Implemented path | One-line purpose |
| --- | --- |
| `backend/__init__.py` | Importable backend package for the root-based server/test commands. |
| `backend/app/__init__.py` | Application package and API version `0.1.0`. |
| `backend/app/main.py` | No-I/O `create_app` factory, ASGI app, health/product routers, and safe versioned error handlers. |
| `backend/app/config.py` | Validated process-only docs, absolute project root, and explicitly required product IDs; no implicit `.env` reads. |
| `backend/app/api/__init__.py` | Importable router package. |
| `backend/app/api/health.py` | Async `GET /health`, fixed liveness response, and no-store header with no data dependencies. |
| `backend/app/api/products.py` | Typed catalogue, product metadata, bounded frame/time-series routes, and configured `/ready` HTTP 200/503. |
| `backend/app/schemas/__init__.py` | Importable response-schema package. |
| `backend/app/schemas/health.py` | Fixed typed `HealthResponse`, with no readiness or source information. |
| `backend/app/schemas/datasets.py` | Validated registry, versioned inspection reports, and shared bounded report serialization, never ready-data claims. |
| `backend/app/schemas/products.py` | Versioned preparation requests, region/resource limits, scientific metadata, and prepared-product manifests. |
| `backend/app/schemas/product_api.py` | Validated public metadata, frame, time-series, catalogue, readiness, and safe error contracts. |
| `backend/app/ingestion/__init__.py` | Importable operator-only ingestion package, independent of API startup. |
| `backend/app/ingestion/registry.py` | Bounded YAML loading, unique dataset lookup, and project raw-path containment checks. |
| `backend/app/ingestion/incois_bio_roms.py` | Local-file states, explicit metadata inspection, optional streamed MD5, and file-change detection. |
| `backend/app/ingestion/netcdf_metadata.py` | Read-only header inventory with metadata limits, no variable-value reads, and lazy scientific imports. |
| `backend/app/processing/__init__.py` | Importable scientific-processing package; no processing at import. |
| `backend/app/processing/prepare_bio_roms.py` | Operator-only V2 coordinate validation, bounded decoded surface extraction, separate previews, and atomic publication. |
| `backend/app/storage/__init__.py` | Importable storage package. |
| `backend/app/storage/inspection_reports.py` | Bounded atomic JSON report publication outside raw files, only when explicitly requested. |
| `backend/app/storage/product_common.py` | Safe contained paths, bounded configuration/JSON, file identity/access checks, and operator SHA-256 descriptions. |
| `backend/app/storage/products.py` | Read-only prepared-product catalogue/readiness and serialized, bounded NetCDF frame/time-series access. |
| `config/data_sources.yaml` | Public source definitions for V2, GODAS years, Copernicus, Argo, and gliders; published notes are not inspected facts. |
| `config/performance.yaml` | Enforced prototype preparation, axis, cell, chunk/cache, response, manifest, file, and product-count ceilings. |
| `scripts/__init__.py` | Importable operator-command package. |
| `scripts/inspect_dataset.py` | `status` and `inspect` CLI with optional checksum verification/report saving; never downloads data. |
| `scripts/prepare_bio_roms.py` | Thin operator CLI for explicit variables, dates, and region after a saved checksum-verified inspection. |
| `scripts/verify_product.py` | Read-only local API/payload benchmark with optional bounded raw-point comparison; not a browser benchmark. |
| `backend/tests/conftest.py` | Isolate tests from the caller's project settings. |
| `backend/tests/test_health.py` | Verify independent health, headers, developer docs/schema, and no-I/O behavior. |
| `backend/tests/test_config.py` | Verify process settings, product-ID/root validation, malformed flags, and no implicit dotenv loading. |
| `backend/tests/test_startup.py` | Run the isolated import/startup probe from an empty temporary directory. |
| `backend/tests/startup_probe.py` | Reject scientific imports and external networking in a fresh process. |
| `backend/tests/test_netcdf_metadata.py` | Tiny temporary NetCDF header fixtures, scientific metadata preservation, limits, errors, and no-value-read checks. |
| `backend/tests/test_dataset_registry.py` | Registry validation, source preservation, path safety, and bounded configuration reads. |
| `backend/tests/test_local_inspection.py` | Local states, checksum handling, concurrent-change detection, and safe atomic reports using temporary fixtures. |
| `backend/tests/test_inspection_cli.py` | CLI output, exit status, explicit save/checksum flags, and safe errors. |
| `backend/tests/test_preparation.py` | Synthetic axis/calendar/packing/mask fixtures, request limits, idempotence, and failed-publication checks. |
| `backend/tests/test_products.py` | Prepared scientific/preview reads, missing values, file changes/access, safe bounds, and readiness with synthetic fixtures. |
| `backend/tests/test_product_api.py` | Typed HTTP responses, bounded request validation, readiness, safe failures, and product route contracts. |
| `backend/requirements.txt` | Pinned API/scientific/provider runtime, including the verified Argopy/erddapy compatibility selection. |
| `backend/requirements-dev.txt` | Runtime requirements plus pinned pytest, HTTPX, Ruff, and test dependencies. |
| `backend/pyproject.toml` | pytest/Ruff configuration, not a duplicate dependency manifest. |
| `backend/.env.example` | Safe process-environment setting reference; not loaded automatically. |
| `.gitignore` | Exclude secrets, environments, private history, datasets, caches, and logs. |
| `data/raw/incois/bio_roms/v2/` | Preserved checksum-verified original V2 download, never served directly to the browser. |
| `data/metadata/` | Private saved source inspection snapshots, not standalone readiness proofs. |
| `data/processed/<product_id>/` | Native-sample `fields.nc` plus the final `manifest.json` publication marker. |
| `data/cache/<product_id>/` | Separate strided `preview.nc` for display only, never comparison samples. |

## Part-4 additions — implemented

These modules are present, not proposed scaffolding. The [part-4 evidence and operator guide](docs/MILESTONE_4.md) distinguishes acquisition, scientific preparation, offline tests and live-source limitations.

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/acquisition.py` | Validated provider selections, explicit model mappings, deadlines/size ceilings and immutable acquisition manifests. |
| `backend/app/schemas/acquisition_api.py` | Public acquisition inventory without operator input paths, private stats or credentials. |
| `backend/app/ingestion/acquisition.py` | Explicit child-process acquisition, atomic private publication, bounded manifest/stat inventory and local import. |
| `backend/app/ingestion/base.py` | Verified TLS/encoded ERDDAP transfer, before-load budgets, exact rectilinear subsetting and fixed-width NetCDF serialization. |
| `backend/app/ingestion/incois_godas.py` | Recorded GODAS HTTPS OPeNDAP with explicitly inspected variable/coordinate names. |
| `backend/app/ingestion/copernicus.py` | Official toolbox subset with explicit product version, server-only credentials and strict-inside source selection. |
| `backend/app/ingestion/argo.py` | Bounded core expert Argopy access, preserved provider response and recorded client transformations. |
| `backend/app/ingestion/glider.py` | Stream one explicit IFREMER v2 FTP NetCDF with byte limits, preserving original-file provenance. |
| `backend/app/schemas/observations.py` | Scientific sample/QC/raw-adjusted/range/packing/identity contracts, bounded selection and collection invariants. |
| `backend/app/processing/observations.py` | Bounded Argo/EGO coordinate scan and selected science normalization with explicit QC/exclusions. |
| `backend/app/schemas/observation_api.py` | Safe collection metadata, atomic storage manifest and validated native-sample page schemas. |
| `backend/app/storage/observations.py` | Immutable 16 MiB scientific JSON snapshots, hash/stat checks, 32-collection inventory and sample/profile pages. |
| `backend/app/api/acquisitions.py` | Read-only available-acquisition inventory, not live source health or preparation. |
| `backend/app/api/observations.py` | Read-only observation catalogue, metadata and bounded sample pages; no raw reads/provider calls. |
| `scripts/acquire_dataset.py` | Explicit JSON-request acquisition/list CLI and private disposable worker entry. |
| `scripts/prepare_observations.py` | Explicit source/selection normalization and publication with verified acquisition or unknown local-client provenance. |
| `config/acquisition.argo.example.json` | Bounded near-surface January 2019 Indian Ocean Argo request used in live verification. |
| `config/acquisition.copernicus.example.json` | Version-pinned daily model request for four fields, 65–66E/1S–0N, Jan29–30 2019, shallowest model level to 10 m; no credentials. |
| `config/acquisition.glider.example.json` | One-file Bella FTP request; Antarctic acquisition test, not comparison overlap. |
| `config/observations.example.json` | Explicit common-box/date/pressure/core-variable/raw-mode normalization selection. |
| `backend/tests/test_acquisition.py` | Source/transport/limits/SDK/serialization/deadline/publication tests, including actual Argopy preprocessing with mocked transfer. |
| `backend/tests/test_acquisition_api.py` | Safe empty/private-manifest inventory and no HTTP write surface. |
| `backend/tests/test_observations.py` | QC/identity/alignment/empty/time/range/packing/chunk-scan scientific fixtures. |
| `backend/tests/test_observation_api.py` | Immutable storage, corruption/conflict checks, bounded typed pages and private-field exclusion. |
| `backend/tests/test_observation_cli.py` | End-to-end local/acquisition input, provenance/source/hash checks, synthetic mode and safe operator errors. |
| `data/raw/acquisitions/<acquisition_id>/` | Preserved input.nc/manifest.json; original ERDDAP provider_input.nc retained for Argopy. |
| `data/observations/<collection_id>/` | Native scientific collection.json plus final private manifest, separate from surface product directories. |
| `docs/MILESTONE_4.md` | Actual source access/integration evidence, operator commands, QC/limits and remaining dependencies. |

## Part-5.2 additions — contracts only

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/models.py` | Private native-model request, axes, identity, provenance, scientific gates and bounded manifest serialization; no I/O. |
| `backend/tests/test_model_contracts.py` | Offline immutable-contract, invalid-selection, identity and budget tests; no actual preparation. |
| `config/model_preparation.example.json` | Safe local request for implemented operator `scripts.prepare_model`; no provider credentials. |
| [docs/MODEL_PREPARATION_CONTRACT.md](docs/MODEL_PREPARATION_CONTRACT.md) | Canonical schema decisions and mandatory preflight/storage/publication rules for Part 5.3. |
| [docs/MILESTONE_5_2.md](docs/MILESTONE_5_2.md) | Exact contract-checkpoint verification and explicit non-implementation boundaries. |

`data/models/<model_id>/` now contains native scientific `fields.nc`, typed `source_metadata.json` and final `manifest.json`; first created in 5.3. Existing surface/observation storage and readiness are unchanged.

## Part-5.3 additions — implemented

| Path | One-line purpose |
| --- | --- |
| `backend/app/processing/prepare_model.py` | Local Copernicus preflight, packing/masks, native slab extraction, full selected readback, immutable publication/reuse and safe failures. |
| `backend/app/schemas/model_metadata.py` | Bounded dtype/shape-preserving source-attribute snapshot with explicit nonfinite tokens. |
| `scripts/prepare_model.py` | Thin JSON-request operator command; prints a safe result or error without downloads. |
| `backend/tests/test_model_preparation.py` | Synthetic native-grid, masks/packing, limits, corruption/reuse, cleanup/locking and CLI tests. |
| `data/models/<model_id>/` | Private scientific fields, typed source metadata and manifest; not served by existing surface routes. |
| [docs/MILESTONE_5_3.md](docs/MILESTONE_5_3.md) | Actual prepared model identity, readback/integrity evidence, commands, tests and remaining gates. |

## Part-5.4 additions — implemented

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/depth.py` | Immutable pressure provenance, explicit assumptions, aligned conversion/exclusion results, endpoint sensitivity and bounded report serialization. |
| `backend/app/processing/depth.py` | Lazy GSW pressure-depth calculation plus source-preserving observation adapter; no file or network I/O. |
| `scripts/convert_observation_depth.py` | Read-only verified collection-to-JSON depth report with explicit reference evidence and zero-geopotential acknowledgement. |
| `backend/tests/test_depth.py` | Published-reference values, inverse/sign/latitude, QC, uncertainty, source immutability, lazy imports and CLI checks. |
| [docs/MILESTONE_5_4.md](docs/MILESTONE_5_4.md) | Scientific assumptions, operator usage, actual Argo diagnostics, tests and unresolved comparison gates. |

GSW 3.6.23 is added to `backend/requirements.txt`; no data directory, replacement observation collection or API endpoint is introduced in 5.4.

## Part-5.5 additions — implemented

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/quantities.py` | Typed provider/client evidence, adjusted provenance and versioned quantity/exclusion reports. |
| `backend/app/processing/quantities.py` | Pure adjusted A/D selection, conservative range/definition gates and lazy GSW conversions. |
| `backend/app/processing/quantity_audit.py` | Bounded read-only provider-row/hash verification and native-model metadata compatibility adapter. |
| `scripts/audit_quantities.py` | Safe bounded JSON operator report, no source writes or matching. |
| `backend/tests/test_quantities.py` | Selection, scientific references, invalid inputs, metadata gates and source-preservation checks. |
| `backend/tests/test_quantity_audit.py` | Provider row mismatch/read-only fixtures and safe CLI errors. |
| [docs/MILESTONE_5_5.md](docs/MILESTONE_5_5.md) | Policies, real quantity diagnostics, verification and remaining matching gates. |

No new data directory, dependency, API endpoint or frontend component is added.

## Part-5.6 additions — implemented

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/matching_policy.py` | Immutable policy/tolerance/evidence/daily-cell/preflight contracts with deterministic full policy identity. |
| `backend/app/comparison/__init__.py` | Importable private comparison package; 5.7 adds a synthetic kernel, not metrics. |
| `backend/app/comparison/policy.py` | Pure requirements assessment and bounded serialization with blocker recomputation. |
| `backend/app/comparison/preflight.py` | Read-only source-bound eligibility audit, strict D/QC1/error screening and explicit unresolved support. |
| `scripts/check_matching_policy.py` | Safe local YAML preflight command with distinct blocked/input-error exit codes. |
| `config/comparison.yaml` | Real selection identity and intentionally null/unreviewed collocation tolerances; no evidence override. |
| `backend/tests/test_matching_policy.py` | Policy identity, finite limits, UTC/daily bounds, evidence/joint counts and no-I/O/forged-report fixtures. |
| `backend/tests/test_matching_preflight.py` | Strict Argo QC/errors/provenance and safe blocked/error CLI fixtures. |
| [docs/MATCHING_POLICY.md](docs/MATCHING_POLICY.md) | Canonical scientific decisions, synthetic engine behavior and remaining real-adapter requirements. |
| [docs/MILESTONE_5_6.md](docs/MILESTONE_5_6.md) | Actual blocked real-data preflight, implemented boundaries and verification evidence. |

Existing datasets, dependencies, routes and frontend status are unchanged.

## Part-5.7 additions — synthetic-only safe checkpoint

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/matching.py` | Bounded private native-grid/support inputs and versioned pair/exclusion reports, never public HTTP requests. |
| `backend/app/comparison/adjusted_depth.py` | Recomputed adjusted-pressure/error bridge tied to quantity and original sample provenance without source writes. |
| `backend/app/comparison/matching.py` | Deterministic nearest-native synthetic selection with masks/support/tolerances, bounded reports and an explicit real-mode blocker. |
| `backend/tests/test_matching_engine.py` | Synthetic matching, edge-case, exclusion, provenance and resource-bound checks. |
| `backend/tests/test_matching_adjusted_depth.py` | Adjusted-depth bridge identity, error/endpoints, source-preservation and substitution checks. |
| `backend/tests/test_matching_output_contract.py` | Reject contradictory output units/status/counts, duplicate identities, invalid UTC/offsets and unsupported matched errors. |
| [docs/MILESTONE_5_7.md](docs/MILESTONE_5_7.md) | Safe checkpoint scope, verification and unfinished real-input/support integration. |

The historical kernel checkpoint added no new data directory, route, matching CLI, dependency, residual/metric or frontend. The approved continuation below adds a native-field reader and input-audit CLI, not a real pair matcher. Do not pass hand-labelled real snapshots into the kernel.

## Part-5.7 continuation — verified local reader and input audit

| Path | One-line purpose |
| --- | --- |
| `backend/app/schemas/model_reading.py` | Bounded internal native-field snapshot with original axes, values and validity masks, not a scientific-support certificate. |
| `backend/app/comparison/model_reader.py` | Read-only native field verification against manifest, source metadata, headers, axes and pre/post file identity. |
| `backend/app/schemas/matching_local.py` | Typed blocked input-audit report binding native-field verification and adjusted-depth provenance/counts. |
| `backend/app/comparison/local.py` | Source-verified native-field and adjusted-depth audit without kernel calls or source writes. |
| `scripts/audit_matching_inputs.py` | Private bounded operator audit with exit3 for verified-but-blocked inputs and exit2 for verification errors. |
| `backend/tests/test_matching_model_reader.py` | Native reader identity, metadata, axes, masks, limits and tampering regressions. |
| `backend/tests/test_matching_local.py` | Local input audit, provenance/alignment, safe CLI errors and preserved scientific-blocker checks. |
| [docs/MILESTONE_5_7_READER.md](docs/MILESTONE_5_7_READER.md) | Reader continuation scope, actual verification and remaining real-support integration. |
| [docs/MILESTONE_5_7_SUPPORT_EVIDENCE.md](docs/MILESTONE_5_7_SUPPORT_EVIDENCE.md) | Official metadata findings, unresolved science gates, bounded static acquisition proposal and unsent provider clarification. |
| `backend/app/ingestion/static_support.py` | Bounded fixed-source public static chunk acquisition, original read-set preservation, exact grid checks and atomic private publication. |
| `scripts/acquire_static_support.py` | Explicit static acquisition CLI with a killable180-second worker, not an API or matching command. |
| `backend/tests/test_static_support.py` | Offline chunk/metadata/transport/grid/mask/publication/resource-limit regressions. |
| `backend/app/schemas/static_support.py` | Strict private static manifest/snapshot contracts, shapes and explicit depth-index mapping. |
| `backend/app/comparison/static_reader.py` | Read-only saved-object replay, exact model binding and NetCDF interpretation/value verification; no matching. |
| `scripts/inspect_static_support.py` | Compact local static-verification CLI, no download, writes or HTTP route. |
| `backend/tests/test_static_reader.py` | Synthetic offline replay, corruption/rehashed-tampering, binding, read-set and CLI regressions. |
| `backend/app/schemas/spatial_support.py` | Typed candidate/stencil diagnostic rows with physical observation-support fields forced unknown. |
| `backend/app/comparison/spatial_support.py` | Bounded nearest/bracketing mask diagnostics and verified local input wrapper; no real matching. |
| `scripts/audit_spatial_support.py` | Read-only local diagnostic CLI, exit 3 for valid but matching-blocked output. |
| `backend/tests/test_spatial_support.py` | Grid-boundary, dry-nearest, stencil, depth/index, identity, limit and CLI tests. |
| `backend/app/comparison/execution.py` | Verified local input assembly, blocked engine invocation and post-input checks; no writes or real unblocking. |
| `backend/app/schemas/matching_execution.py` | Typed combined blocked execution with separate engine and spatial diagnostics. |
| `scripts/run_local_matching.py` | Operator-only execution CLI; exit 3 for a valid scientifically blocked result. |
| `backend/tests/test_matching_execution.py` | Assembly, no pair search under blockers, identity/change detection, output and CLI regressions. |
| [docs/MILESTONE_5_7_EXECUTION.md](docs/MILESTONE_5_7_EXECUTION.md) | 5.7-C safe integration evidence, commands and remaining scientific requirements. |
| [docs/MILESTONE_5_7_SPATIAL_SUPPORT.md](docs/MILESTONE_5_7_SPATIAL_SUPPORT.md) | 5.7-B implemented diagnostics, real findings, verification and remaining scientific decisions. |
| [docs/MILESTONE_5_7_STATIC_READER.md](docs/MILESTONE_5_7_STATIC_READER.md) | 5.7-A reader verification and next 5.7-B/5.7-C boundaries. |
| `data/raw/static_copernicus/<support_id>/` | Acquired support subset, original partial compressed read set and final manifest; not served or matching-ready. |
| [docs/MILESTONE_5_7_STATIC_ACQUISITION.md](docs/MILESTONE_5_7_STATIC_ACQUISITION.md) | Actual regional static acquisition, limits, tests and remaining support-adapter work. |

No new data directory, dependency, HTTP route, metric or frontend is added. Finite native values do not establish wet/bottom/connectivity support; real kernel mode remains blocked.

## Proposed repository layout — remaining work

The ownership map below is the target layout. Only paths explicitly listed as implemented above exist now; other entries remain planned. Create each remaining directory when its approved implementation is added, not as empty scaffolding.

| Top-level path | One-line purpose |
| --- | --- |
| `backend/` | Python API, source ingestion, scientific processing, comparison, and backend tests. |
| `frontend/` | Next.js/TypeScript browser UI, CesiumJS globe, and Plotly scientific charts. |
| `config/` | Versioned, non-secret source registry and scientific processing policies. |
| `scripts/` | Thin operator commands that call backend ingestion/processing modules. |
| `data/` | Local raw datasets, processed products, and regenerable caches; ignored by Git. |
| `docs/` | Detailed decision records and source inspection notes as the project grows. |
| `ocean-env/` | Local Python 3.12 virtual environment; ignored by Git. |
| `.gitignore` | Exclusions for secrets, environments, raw data, caches, and build artifacts. |

## Backend modules

| Path | One-line purpose |
| --- | --- |
| `backend/app/__init__.py` | Declare the importable backend application package. |
| `backend/app/main.py` | Construct the FastAPI `app`, attach routes, and configure startup behavior. |
| `backend/app/config.py` | Load and validate runtime settings and references to non-secret policy files. |
| `backend/app/api/` | HTTP routing, request validation, and response/error translation. |
| `backend/app/api/health.py` | Independent liveness only; prepared-product readiness lives in `api/products.py`. |
| `backend/app/schemas/` | Versioned internal and API contracts for fields, profiles, provenance, and comparisons. |
| `backend/app/ingestion/base.py` | Implemented bounded verified-HTTPS transfer, metadata/shape guards, fixed-width serialization and model subsetting. |
| `backend/app/ingestion/incois_bio_roms.py` | Register/inspect local Zenodo V2 by default, with LAS exports and future OPeNDAP access as additional inputs. |
| `backend/app/ingestion/incois_godas.py` | Year-specific GODAS access and local-file fallback with inspected variable mappings. |
| `backend/app/ingestion/copernicus.py` | Server-side acquisition through the official Copernicus Marine Toolbox. |
| `backend/app/ingestion/argo.py` | Official Argo access with explicit source-to-client time-name mappings and recorded mode/QC settings. |
| `backend/app/ingestion/glider.py` | IFREMER FTP acquisition and EGO glider metadata/sample alignment. |
| `backend/app/processing/` | QC, coordinate/quantity normalization, scientific subsets, and display downsampling. |
| `backend/app/processing/prepare_bio_roms.py` | Prepare bounded V2 scientific subsets and separate display resolutions using inspected metadata. |
| `backend/app/comparison/` | Model-observation matching, tolerances, exclusions, and comparison diagnostics. |
| `backend/app/storage/` | Implemented inspection/product storage and bounded surface retrieval; scientific observation pages are now implemented; general cache management remains later work. |
| `backend/app/storage/cache.py` | Byte-bounded cache lookup, request deduplication, version-aware keys, and derived-product eviction. |
| `backend/app/jobs/` | Optional persistent preparation-job lifecycle once on-demand background processing is implemented. |
| `backend/tests/` | Offline scientific/contract tests and separately selected live integration checks. |
| `backend/tests/test_health.py` | Current liveness/docs/no-I/O checks; product/readiness behavior is covered by product tests. |
| `backend/tests/fixtures/` | Tiny synthetic or redistributable test datasets with explicit provenance. |
| `backend/requirements.txt` | Pinned runtime through 5.4, including xarray/provider clients, GSW and required transitive dependencies. |
| `backend/requirements-dev.txt` | Development tools and test dependencies, including the runtime requirements. |
| `backend/pyproject.toml` | Shared formatter, linter, and test settings; not a competing dependency list. |
| `backend/.env.example` | Safe example backend settings and credential variable names without real values. |

Add `__init__.py` where needed for importable Python subpackages. Routes depend on processing/comparison services; scientific modules should remain usable from an operator script without starting the API.

Health routing is an exception to scientific-service dependencies: `/health` stays independent of ingestion and processing. FastAPI supplies `/docs` for developer API testing; it does not need a separate frontend page or source adapter. Implemented `/ready` checks only explicitly required real prepared products through bounded manifest/stat/one-byte access checks, not NetCDF parsing or raw-source reads. With no required products configured it returns 503. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Frontend modules

| Path | One-line purpose |
| --- | --- |
| `frontend/src/app/` | Next.js routes, root layout, and page-level loading/error states. |
| `frontend/src/components/` | Reusable controls and layout components shared across features. |
| `frontend/src/features/launch/` | Earth-style startup state, genuine readiness feedback, and initial camera transition. |
| `frontend/src/features/ocean-view/` | Cesium globe, camera, geographic picking, depth slices, and current-vector rendering. |
| `frontend/src/features/volume-view/` | Dedicated bounded ocean-volume renderer if needed, synchronized with the globe selection. |
| `frontend/src/features/analysis/` | Plotly time series, depth profiles, and time-depth or transect sections. |
| `frontend/src/features/observations/` | Argo/glider tracks, selection, and profile inspection. |
| `frontend/src/features/comparison/` | Match selection, difference plots, and scientific match diagnostics. |
| `frontend/src/features/data-sources/` | Provider/product catalogue, capability and coverage details, provenance, and connection states. |
| `frontend/src/features/controls/` | Shared region, time, depth, variable, and colorbar state. |
| `frontend/src/lib/` | API client, response types, and reusable coordinate/display helpers. |
| `frontend/src/lib/dataClient.ts` | Cancel/deduplicate requests, reject stale responses, and manage bounded selection/frame caching. |
| `frontend/src/lib/renderQuality.ts` | Adaptive display detail and declared rendering budgets without changing scientific calculations. |
| `frontend/public/` | Small public static assets; never raw scientific datasets or credentials. |
| `frontend/public/cesium/` | Build-copied Cesium runtime assets/workers; generated from the pinned package and not hand-edited. |
| `frontend/tests/` | Browser flow tests for selection, overlays, profiles, and failure states. |
| `frontend/package.json` | Frontend dependencies and explicit development/build/check scripts. |
| `frontend/package-lock.json` | Reproducible npm dependency resolution used by `npm ci`. |
| `frontend/.env.example` | Documented public API address and other non-secret frontend settings. |

## Configuration and data

| Path | One-line purpose |
| --- | --- |
| `config/data_sources.yaml` | Implemented source identities, public origins, local V2 filename/checksum, and published notes; no invented verified mappings. |
| `config/comparison.yaml` | Product-specific QC choices, compatibility rules, and spatial/time/depth tolerances. |
| `config/performance.yaml` | Implemented hard prototype ceilings; browser/GPU budgets and general cache eviction remain later work. |
| `scripts/prepare_bio_roms.py` | Implemented bounded operator preparation, requiring prior verified V2 inspection. |
| `scripts/inspect_dataset.py` | Implemented explicit local status/header-inspection command; no preparation or provider downloads. |
| `data/raw/` | Preserved acquired inputs, including downloads, manual exports, and client outputs with prior processing recorded. |
| `data/raw/incois/bio_roms/v2/` | Completed, verified V2 original retained unchanged after part-3 preparation. |
| `data/metadata/` | Created on explicit `inspect --save`; private inspection snapshots, not readiness manifests. |
| `data/processed/` | Implemented versioned scientific surface subsets/manifests; normalized observations live separately under data/observations/. |
| `data/cache/` | Implemented strided display previews; general cache management and comparison caches remain later work. |
| `docs/decisions/` | Dated design decisions with reasons and links back to the current architecture. |
| `docs/source_inspections/` | Metadata snapshots and dated access findings for particular products/files. |
| `docs/performance.md` | Local verification environment, prepared selection/payload measurements, and unmeasured browser/cold-cache targets. |

Keep reusable logic in its owning backend/frontend module. Scripts orchestrate it; configuration describes it; datasets do not contain application code. Update this map whenever a meaningful module is added, moved, or removed.
