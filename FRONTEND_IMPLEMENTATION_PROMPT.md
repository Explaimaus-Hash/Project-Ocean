# Project Ocean — Frontend Implementation Prompt

## Current implementation override — 2026-09-28

The supplied frontend has now been recovered and integrated at `frontend/` by explicit user request. Read [the integration milestone](docs/FRONTEND_INTEGRATION.md) before further work; do not rebuild a competing UI or follow older no-frontend authorization notes below. Preserve recovered design, real backend transport, capability gates, source metadata and exploratory comparison labels. Missing depth/current/profile/source support is not permission to fabricate data.

Latest backend contract: [5.9 comparison API](docs/MILESTONE_5_9.md) now exposes saved exploratory summaries and matched/excluded sample pages under `/api/v1/comparisons`; use [the route guide](docs/API_ROUTES.md#comparison-api--part-59). Results require explicit operator preparation and are historical snapshots, not live source status. Preserve assumption badges, preparation time, partial/blocked states, units, full-selection versus filtered counts, null metrics and exclusion reasons. Do not download private files, trigger processing from the browser or claim independent validation. Earlier no-route statements below are historical. Frontend is still not authorized by this documentation update.

Backend context update (2026-09-27): [5.8 exploratory metrics](docs/MILESTONE_5_8.md) adds operator-only residuals/counts/bias/RMSE over [5.7 assumption-labelled matching](docs/MILESTONE_5_7_EXPLORATORY.md); there is still no comparison HTTP route. Future UI must preserve assurance, units, sample counts, exclusions/partial states and null empty metrics. Never call these independent validation, invent profile counts or consume private operator files directly. Frontend remains the last separately approved milestone; this update does not authorize it.

This prompt is reserved for the final, separately approved frontend part. Do not execute it during backend milestones. The user requires permission after each completed part. When frontend work is authorized, build the application described below and verify its interactions in `C:/Users/pc/OneDrive/Desktop/ocean_2`.

## 1. Context and objective

Project Ocean is a browser-native interactive 3D ocean data visualization system for INCOIS use. It combines numerical model outputs from INCOIS and Copernicus Marine with in-situ Argo float and IFREMER glider observations in one environment. Required capabilities include 3D volumetric and depth-slice views, current vectors, time animation, observation overlays, click-to-inspect profiles, customizable colorbars, modular ingestion, and web deployment.

Read the accompanying `README.md`, `ARCHITECTURE.md`, `FILE_STRUCTURE.md`, and `CONVENTIONS.md` before implementation. Preserve their scientific and source decisions. This prompt adds the requested Google Earth-style visual direction and the frontend behavior. Inspect any existing code before selecting compatible dependency versions or changing its structure.

The default working box is longitude 30°E–120°E and latitude 30°S–30°N. It is a comparison selection, not the full extent of every dataset. All four source families stay in scope. Select a valid date/depth range from actual metadata; do not assume common coverage.

Prioritize smooth interaction, visual clarity and scientific correctness. Parts 1–4 provide independent health/readiness, real prepared V2 SST/SSS surface APIs, operator source acquisition and QC-preserving observation storage/APIs. Source-by-source live limitations are in [docs/MILESTONE_4.md](docs/MILESTONE_4.md); acquired data is not automatically scientifically ready. Comparison/depth-current serving and frontend remain incomplete. Reinspect current capabilities when this final part is separately authorized.

## 2. Frontend stack

- Next.js App Router, React, and TypeScript for the application shell and panels.
- CesiumJS as the main 3D Earth/globe engine, with client-only initialization and explicitly configured worker/static assets.
- Plotly.js with its React integration for interactive scientific graphs; load graph code when needed.
- A shared, typed selection store for active tab, model/observation sources, variable, region, time range/current time, depth, render mode, and selected profile. Use the existing state solution if present; otherwise start with a focused React context/reducer.
- CSS Modules and shared design tokens for styling, unless the existing repository already has a consistent styling system.
- Python 3.12 and FastAPI provide the backend. Part-3 surface processing uses bounded direct-netCDF4 reads; part-4 adapters use bounded xarray processing outside HTTP requests. Browser requests use a typed adapter against the implemented, versioned API contracts rather than opening scientific files.

CesiumJS owns the main globe and camera. First prototype the ocean volume using bounded data and Cesium-compatible rendering. Add a dedicated Three.js volume view only if the prototype shows it is needed; synchronize its selection with the globe and document geographic/local coordinates. Do not assume full ocean volume rendering comes ready-made with a basemap.

Pin compatible package versions and preserve lockfiles. Provide Windows PowerShell setup/run instructions using the project environment's explicit Python executable and `npm.cmd` where appropriate.

## 3. Google Earth-style launch and first screen

The requested appearance is a Google Earth-like launch/loading screen that becomes a globe explorer. No reference screenshot has been supplied; use the visual direction below as the baseline and make it easy to refine later.

Start with a full-window Earth against near-black space. Show realistic licensed Earth imagery where configured, subtle atmospheric glow, restrained stars, and small Project Ocean branding. Keep the Earth as the dominant visual element. Use a clean sans-serif typeface, quiet controls, and smooth camera motion. Avoid a separate marketing landing page or a grid of dashboard cards as the first screen.

Show genuine loading states such as “Preparing globe” and “Loading selected layers.” Do not display invented percentages or a fixed delay after the application is ready. When the base globe is usable, reveal the interface and make a smooth, interruptible camera flight toward the Indian Ocean. Scientific layers can finish independently. Respect reduced-motion preferences and offer retry when a provider fails. If imagery is unavailable, show a usable basic globe with a clear status message.

Neither downloading V2 nor preparing scientific subsets belongs in the launch sequence. Start from a prepared small selection when available. Load a lightweight labeled preview first, then refine it after interaction settles. Lazy-load chart and optional volume modules. Keep camera controls and tabs usable while a particular layer is loading or has failed.

The explorer must allow rotate, pan, zoom, tilt, north reset, and reset-to-region. Add a coordinate readout and visible imagery attribution. Use Project Ocean branding and its own icons/assets; enable Google imagery only through an explicitly configured supported integration.

## 4. Main workspace layout

Use the full viewport for the globe with lightweight panels around it:

- A compact top bar with Project Ocean title, selected region, active dataset context, and data mode/status.
- A narrow left navigation rail with labeled or tooltip-accessible tabs: Explorer, Analysis, Profiles, Comparison, and Data Sources.
- A collapsible left panel for the selected tab's filters and layers.
- A right inspector for clicked points, profiles, match details, or product metadata.
- A bottom timeline with start/end selection, play/pause, previous/next frame, playback speed, and the actual displayed timestamp.
- Compact camera controls, depth control, and variable/colorbar legend placed so they do not cover the timeline or inspector.

Use dark neutral surfaces, subtle borders, modest panel transparency, and ocean-blue/cyan accents. Prioritize readable labels, units, and scientific plots. Keep the interface usable at common laptop sizes; collapse panels into drawers on narrow screens. Support keyboard navigation, visible focus, tooltips, and reduced motion.

Switching tabs must retain the region, time, depth, layer selection, and selected observation. Analysis/comparison may expand into a split view while preserving the geographic context and a clear return to Explorer. Avoid repeatedly recreating the main globe during tab changes.

## 5. Explorer tab

Provide model and observation layer groups with individual visibility and opacity controls. Model options include verified INCOIS products and Copernicus datasets. Observation options include Argo locations/profiles and glider tracks. Show source names and dataset identity rather than silently merging products.

Let users select an available variable, time, and depth; draw or enter a region; and switch between supported surface, depth-slice, volume, and vector views. Only enable a view when the selected dataset contains the needed dimensions/variables. Current vectors must use verified component orientation and units; a horizontal current product does not imply a vertical velocity component.

Provide color palette selection, manual/automatic value limits, opacity, and a reset control. Keep color limits stable during animation unless automatic scaling is explicitly selected. Mark missing cells and unavailable frames clearly. If imagery hides subsurface content, use an appropriate translucent/clipped view or the dedicated volume view.

Offer Preview/Balanced/High display detail with sensible automatic adaptation. These settings adjust display resolution, vector density, and effects only. Show actual resolution and whether refinement is pending. A prior frame retained during an update must keep its prior timestamp/source labels; reject late responses that no longer match the active request. Buffer only nearby frames, and pause with a clear buffering state when a frame is unavailable.

Clicking a model point opens its value, location, actual time/depth, units, source, and an available vertical profile. Clicking an Argo float or glider sample opens its observation inspector and linked profile graph. Keep pressure/depth information visible. A track is sampled data; avoid displaying unsampled space as measured coverage.

## 6. Analysis tab and graphs

Provide analysis tied to the shared selection:

- Time-series plots at a selected location/depth, with clear averaging or nearest-sample semantics.
- Vertical profiles with variable values on the horizontal axis and depth increasing downward on the vertical axis; pressure-based plots must explicitly label dbar.
- Time-depth heatmaps when the selected product supports them.
- Distance-depth transect sections when a path and suitable gridded data are available; otherwise show why the operation is unavailable.

Every graph needs a title, quantity/units, source, selection context, hover values, and sensible missing-data behavior. Link chart selection to the globe where meaningful. Add reset zoom and export controls for bounded plotted data and images, including provenance and any demo label. Clearly specify weighting and sample counts for any aggregation; do not silently average unequal-area grid cells as an area mean.

## 7. Profiles tab

Support searching/filtering the prepared observations by platform, deployment or float/cycle, date, region, and available parameter. Retain Argo direction and any separate source-profile identity. Display a results list alongside a map/track context and selected profile.

For a selected profile, show temperature and salinity against depth or pressure. Show chlorophyll and other BGC parameters only when available and interpretable. Include QC, raw/adjusted selection, data mode, source time/location, and provenance. Missing values remain missing. Keep glider sensor samples aligned with their own time/position rather than assuming GPS fixes and sensor arrays share row order.

## 8. Comparison tab

The primary workflow compares a selected INCOIS or Copernicus model variable against Argo or glider observations. Include a model-versus-model option only after the required observation comparison works and its spatial/temporal alignment is explicit.

Provide selectors for model dataset, observation collection, compatible variable, region, time/depth range, QC policy, and horizontal/time/depth matching tolerances. Show discovered overlap and unmatched reasons before presenting results. Tolerance defaults must come from a documented product policy; do not invent scientifically authoritative thresholds.

Display matched model/observation profile overlays, paired time series when supported, a model-versus-observation scatter plot with a 1:1 reference line, a residual plot, and a table of matched pairs. Use model minus observation consistently for the residual. Show valid pair count, mean bias, and RMSE; correlation is optional and must handle insufficient or constant data correctly.

Compute statistics only from valid matched scientific samples. Matching must respect wet/bottom masks, coastlines, local depth support, and time support. Preserve actual spatial/time/depth offsets. Do not calculate comparisons from display-downsampled grids. Account for model averaging periods and possible assimilation of the observations when describing results.

## 9. Data Sources tab and settings

Show INCOIS BIO-ROMS, INCOIS GODAS, Copernicus, Argo, and IFREMER gliders with their role, dataset IDs, inspected variables/units, coverage, acquisition time, cache status, provenance, and prepared-data availability. Distinguish “not configured,” “not yet checked,” “no data in selection,” “timed out,” “cached,” and “available.” Do not infer live health from a recorded endpoint.

Show local BIO-ROMS V2 as its own registered input, with version, checksum verification, available fields, and preparation state. Reading this input must not trigger a live OPeNDAP health check. Support choosing other prepared INCOIS inputs through an operator-controlled backend workflow. Ordinary browser users should not enter source-service passwords or trigger unbounded downloads. Keep display settings, animation preferences, and vertical exaggeration in a compact settings drawer.

JSON inspection reports are private operator snapshots, not browser responses or prepared-data manifests. Do not fetch raw files, YAML configuration, `data/metadata/`, or prepared `.nc` files directly from the browser. Use the implemented public contracts below for validated safe metadata and bounded data. Distinguish published claims from inspected evidence; a header containing a depth-like name never enables a profile/volume by itself.

Keep backend connectivity separate from dataset availability. Implemented `GET /health` returns HTTP 200 with `{"status":"ok","service":"Project Ocean Backend"}` and `Cache-Control: no-store`; it performs no source access or processing. Show a compact backend indicator if useful, without a health tab or globe-startup gate. `/ready` is implemented and returns 503 by default until an operator configures `OCEAN_REQUIRED_PRODUCT_IDS` as an explicit JSON list. It returns 200 only when those real prepared products pass bounded manifest/stat/one-byte read-access checks; no NetCDF parsing, raw reads, provider calls, or heavy hashes occur. Synthetic products cannot satisfy real-data readiness. This is not a global source-health or arbitrary-selection guarantee. Source/layer responses remain authoritative for selected data. `/docs` is optional developer tooling; `OCEAN_DOCS_ENABLED=false` disables docs/schema without disabling data routes or health.

### Implemented backend connection points

Read `/openapi.json` and current `backend/app/schemas/{product_api,observation_api,acquisition_api}.py` before coding the adapter. Current routes are:

| Route | Current behavior |
| --- | --- |
| `GET /api/v1/datasets` | All registered source families with ready prepared selections or honest not-prepared/not-configured states; no provider fetch. |
| `GET /api/v1/products/{product_id}` | Safe metadata, actual axes/times, units, provenance, selection, preview stride, and capabilities. |
| `GET /api/v1/products/{product_id}/frame` | One variable and `time_index`, `quality=preview` or `scientific`, with optional complete `west/east/south/north` bounds. |
| `GET /api/v1/products/{product_id}/timeseries` | Scientific nearest-axis grid-cell series at requested `longitude/latitude`, with actual sample point and distance. |
| `GET /api/v1/acquisitions` | Local acquired-source provenance; acquired_not_prepared is not layer readiness. |
| `GET /api/v1/observations` | Available scientific observation collections and source-specific capabilities. |
| `GET /api/v1/observations/{collection_id}` | Selection, source, variable units, QC/range policy, counts and input checksum. |
| `GET /api/v1/observations/{collection_id}/samples` | offset/limit pages, at most 500 samples, optional exact profile_id; no client-side scientific filtering/matching. |

Responses use `schema_version: 1`, source/product identities, explicit real/synthetic mode, units, and `null` missing values. Errors use a stable `error.code` and safe message. Handle 413 by reducing the request, 422 by correcting unsupported/no-overlap selections, and `busy`/503 by bounded retry/cancellation. There is no HTTP download/preparation queue. Missing products cannot be made ready by repeatedly polling a fictitious job.

Current preview frames are strided source samples, labelled `display_only: true`; scientific frames retain native samples but are limited to 65,536 cells, so a whole regional scientific frame is deliberately rejected. Preview frames are capped at 16,384 cells, and JSON responses at 2 MiB. The time-series route uses scientific data with no wet-neighbour search and is not an observation comparison. Do not present Preview/Balanced/High as three existing backend levels: map UI choices only to implemented quality/bounds options until additional levels are actually added.

## 10. Scientific and source constraints

Preserve these facts and boundaries throughout implementation:

- The verified local BIO-ROMS V2 has 480 timestamps, 756 latitudes, and 1,081 longitudes. Its fields are `SST`, `SSS`, `MLD`, `DIC`, `CHL`, `NO3`, `pCO2_Int`, `pCO2_Clim`, `pCO2_Original`, and `Deviant_uncertainty`; it has no vertical profile or current-component variables. This corrects the historical pCO₂-only interpretation. Only SST/SSS January–March 2019 is prepared at this checkpoint; other fields need explicit bounded operator preparation before browser use. The recorded LAS ID is `d272905813`; its live variable names and hosted version still need separate inspection. The authors recommend the [published v2 product](https://zenodo.org/records/14614739).
- Recorded GODAS IDs are 2025 `cbbdd5ab07`, 2024 `1bb8b13c5b`, 2023 `eeb330b387`, and 2022 `fe1698c540`. Exact variables remain unconfirmed. Use the full recorded URLs in the architecture rather than constructing new guesses.
- Prior INCOIS requests timed out. Use prepared local Zenodo V2 as the BIO-ROMS default; retain OPeNDAP and LAS-export adapters as additional access paths. Keep TLS verification enabled and distinguish access failures from invalid data.
- Copernicus product is `GLOBAL_MULTIYEAR_PHY_001_030`; daily dataset version `202311` and authentication were verified on 2026-09-10. Recheck the catalogue before selecting another revision. Aliases are `thetao`, `so`, `uo`, and `vo`; the SDK converts elevation into positive-down model depth, not observation pressure. Authentication/acquisition does not enable prepared depth/current UI controls: use the actual serving capabilities and [part-4 evidence](docs/MILESTONE_4.md).
- Official Argo data comes from GDAC/services; Argopy is the client. Raw profile time uses `JULD`, while Argopy may expose `TIME`. Record client filtering, QC, and adjusted-value handling.
- IFREMER Bella acquisition was repeated successfully in part 4, but normalization rejects conflicting declared TIME bounds and sampled QC is missing. The Antarctic sample is outside the comparison box; do not present it as a scientifically ready Indian Ocean layer.
- Pressure in dbar is separate from depth in metres. Temperature/salinity definitions must be compatible before comparison; GSW conversions require the correct inputs and reference conditions. Raw fluorescence is not automatically calibrated chlorophyll concentration.

Do not send full raw NetCDF files to the browser. Use surface APIs and separate scientific observation pages. Part-4 observations preserve selected raw/adjusted values, source/QC/range provenance and exclusions; they do not harmonize quantities or implement comparison. Treat ambiguous Argo points as points and gliders without proven profile IDs as tracks. Never infer depth from pressure, calibrated concentration from fluorescence counts, valid metadata from a completed download, or full water columns from V2 surface fields. Source credentials stay server-side.

## 11. Implementation and evidence requirements

### Local BIO-ROMS V2 pipeline

Use the [recommended V2 product](https://zenodo.org/records/14614739), approximately 9.2 GB. Its published region already matches the project box; it is not a global-ocean download. A normal download retrieves the complete file before local subsetting. Do not choose deprecated V1 just to reduce file size, and do not assume cropping to the same full box saves space.

The original 9,248,080,750-byte file is already preserved under `data/raw/incois/bio_roms/v2/`, with published MD5 `78b7c0fbaa00db58a31563bb442a693b` verified. Preparation retains scientific-resolution subsets in `data/processed/` and separate previews in `data/cache/`; a final validated manifest makes a product visible. Reuse the operator pipeline rather than reimplementing acquisition/preparation in the frontend. Prepare only needed variables/dates/regions. Dask/Zarr are now provider-toolbox dependencies, but no additional V2 Zarr cache was created; the bounded surface processor still uses netCDF4. Do not load the full file into browser memory or materialize it all on backend startup.

The current real demonstration product is `p_7c8210052d41d41259724e2d`: SST and SSS, requested 2019-01-01 through 2019-03-31 over the common region. The actual timestamps are 2019-01-29, 2019-02-28, and 2019-03-30; show these returned times, not invented month starts. Its scientific grid is `3 × 756 × 1081`, and each stride-8 preview is `95 × 136`. Scientific and preview files are 10,093,402 and 233,615 bytes respectively; on-disk sizes are not HTTP payload sizes. Discover products through the catalogue instead of treating this example ID as a permanent hard-coded global default. Consult [part-3 evidence](docs/MILESTONE_3.md) and [measurement scope](docs/performance.md).

Make the first real frontend BIO-ROMS demonstration a surface field plus the existing scientific grid-cell time-series route. Current capabilities enable surface/time series but explicitly disable depth profiles, volumes, currents, and scientific comparison. Use a separately verified depth-resolved model product for later depth slices/volumes. Surface temperature, salinity, or mixed-layer depth alone must not be presented as a full vertical dataset.

### Responsive requests and evidence

Implement the frontend with typed API contracts and connect existing backend endpoints where available. If source services or backend functions are unavailable, use a deterministic, explicitly selected demo mode with small fixtures for UI verification. Keep “Demo data” visible on the globe, graphs, comparison statistics, and exports. Never silently substitute fixtures after a live request fails.

Every visible control must perform its documented action or explain why the capability is unavailable. Separate a UI-complete demo from verified live integration in the handoff. True ocean volume rendering remains a required feature: prototype it, report any limitations explicitly, and do not relabel a flat plane or decorative particles as a volumetric implementation.

Bound requests, cache derived products, cancel outdated requests, debounce rapid selection changes, and dispose viewer/chart/GPU resources on unmount. Handle unsupported browser graphics and lost graphics contexts with a useful recovery state. Keep the usable shell responsive when one source is slow.

Enforce configured memory, payload, concurrency, and cache budgets on the server and browser. Deduplicate requests and limit prefetch. Heavy analyses and exports must run outside interactive handlers; show an explicit unprepared state until an operator job or real persistent worker can fulfill them. A queued/running status must correspond to actual work. Reuse processed scientific samples for inspection, metrics, and export even when a map/chart displays reduced detail.

Use the canonical numerical targets in `ARCHITECTURE.md` for input feedback, warm globe startup, cached frame latency, frame rate, and scalar-preview transfer size. Measure cold/warm performance, p95 repeated interactions, decoded memory, and frame drops on a documented reference device/network. Keep limits in `config/performance.yaml` and measurements in `docs/performance.md`. Report any missed targets and tune display detail or processing before claiming a smooth experience.

Use provider imagery with appropriate configuration and attribution. A basic working globe and demo must not require paid Google imagery. If Google Photorealistic 3D Tiles are later configured, follow the provider's documented access, billing, and attribution requirements. Ocean measurements and bathymetry require their own verified data sources and vertical references.

## 12. Acceptance and handoff

Verify these flows in a real browser:

1. Startup transitions from the Earth-style loading view to an interactive Indian Ocean globe; reduced motion and provider failure also work.
2. Rotate/zoom/tilt/reset and region, source, variable, depth, and time controls update the appropriate layers without resetting unrelated state.
3. Argo and glider selections open linked inspectors and profiles with units, QC, and provenance.
4. Analysis graphs reflect the selected data; missing data and unsupported requests are handled honestly.
5. Comparison produces correct results on a small fixture with known pairs and expected bias/RMSE; no-overlap and incompatible-variable cases explain the exclusion.
6. Volume/slice/vector capabilities have working demonstrations appropriate to the supplied data, with actual implementation limitations documented.
7. Tabs share selection state; narrow layouts, keyboard focus, credits, and loading/error states remain usable.
8. Frontend type checks, lint, and production build pass; focused scientific/API tests pass for any backend logic added.
9. Rapid slider/tab changes and deliberately delayed responses never apply stale data under new labels; repeated playback and navigation do not cause unbounded memory growth.
10. Prepared local V2 remains viewable with the INCOIS/Zenodo source connection unavailable; basemap connectivity is tested separately. Cold/warm performance and payload/memory measurements meet the documented targets or have explicit remaining issues.
11. Backend-online and dataset-ready states remain distinct. A source outage does not imply API failure, and health/readiness delays do not block globe navigation. Verify `/health` independently of datasets and the implemented `/ready` HTTP 200/503 contract, including unset requirements, synthetic products, and changed/missing local products without upstream provider calls.

Deliver runnable code, dependency manifests/lockfiles, safe configuration examples, setup instructions, and screenshots of the launch, Explorer, Analysis, and Comparison views. Update the four documentation files to match actual implementation. Report precisely which features were tested with real data, cached data, or demo fixtures, and identify remaining integrations without claiming they are finished.

## Reference documentation

- [CesiumJS globe and geospatial capabilities](https://cesium.com/learn/cesiumjs-learn/)
- [Cesium globe translucency](https://cesium.com/learn/cesiumjs/ref-doc/GlobeTranslucency.html)
- [Plotly React integration](https://plotly.com/javascript/react/)
- [Google 3D Tiles renderer integration](https://developers.google.com/maps/documentation/tile/use-renderer)
- [Google Map Tiles usage and billing](https://developers.google.com/maps/documentation/tile/usage-and-billing)

## Current matching checkpoint — synthetic kernel and verified local inputs

The [matching policy](docs/MATCHING_POLICY.md) and [5.6 preflight](docs/MILESTONE_5_6.md) exist only as backend/operator work. Part 5.7 provides a private synthetic matching kernel, adjusted-depth bridge and verified local native-field/input audit. The audit never calls the kernel and returns `inputs_verified_matching_blocked`, zero pairs and overlap not evaluated; finite-value masks and adjusted-depth alignment do not establish wet-domain support or a shared vertical datum. Scientific-support verification and real-kernel integration remain unfinished; there is no comparison route or real pair result. [Historical kernel checkpoint](docs/MILESTONE_5_7.md), [reader continuation](docs/MILESTONE_5_7_READER.md). Synthetic reports remain `comparison_ready=false` and must never be relabelled real. The current real selection is blocked by unresolved limits/time/masks/depth-reference evidence; the UI must not present that as no-overlap, zero difference, loading forever or a successful comparison. Preserve quantity diagnostics, verified inputs and verified matches as separate states. Private operator reports are not browser data contracts. Frontend remains the final separately approved part.

## Current backend quantity checkpoint — 5.5

Read [the 5.5 implementation record](docs/MILESTONE_5_5.md) before frontend implementation. Adjusted quantity diagnostics now exist only as private operator reports, not HTTP endpoints or matched comparisons. Never display a computed observation potential temperature as a valid `thetao` comparison while model scale/reference remain unresolved. Keep source collection values and derived quantities separately labelled, preserve QC/error provenance, and never infer matching readiness from a conversion. Frontend is still last and requires separate approval.
