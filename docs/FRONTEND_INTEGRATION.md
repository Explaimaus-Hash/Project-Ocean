# Recovered frontend + local backend integration

Latest follow-up: [all-date BIO-ROMS archive](BIO_ROMS_ARCHIVE.md) supersedes the three-date UI limit below. The 480 actual source dates are mapped across bounded SST/SSS products; see that milestone for completion evidence. Original integration/recovery evidence below remains historical.

Verified 2026-09-28. This is the current implementation checkpoint; earlier no-frontend/ask-before-frontend notes are historical. The user explicitly approved integrating the supplied UI and running it.

## Batch transitions and graph layout — 2026-09-28

Bottom-timeline follow-up: removed transient Requested/Buffering caption rows during normal switching. The displayed timestamp and available-frame count retain stable geometry, including while the next product metadata is pending. Playback still waits internally and aria-busy exposes in-progress state; metadata/frame errors still stop playback and show the error/Retry controls. This is visual stability, not removal of real loading time.

Timeline verification: typecheck, lint and production build passed; **16 live tests passed in 1.0 minute** on 2026-09-28. A deliberately blocked next batch preserved exactly equal caption/playback bounding boxes at 1440, 760 and 390px viewport widths, with no Requested/Buffering caption text. A separate failed-metadata test confirmed visible error/Retry and retention of the old displayed timestamp. Desktop/mobile timeline screenshots were visually inspected. The updated production frontend is running locally on port 4317.

User-requested polish keeps the last successfully displayed, correctly timestamp-labelled scalar layer visible while a compatible batch loads. Palette, manual limits and stable colour range no longer reset at batch boundaries. Actual requests retain product ID/local-index identity. One next source frame is prefetched after the active frame loads, with cancellation and the existing three-frame / 6MiB cache; this is not an archive-wide download. Errors retain explicit status, not a synthetic replacement. Incompatible dataset/variable/region changes still clear the old selection.

Follow-up requested by the user: ready rasters now use a **480ms smoothstep visual crossfade**, rather than a hard replacement. Both source timestamps are labelled during blending and the new displayed timestamp commits at completion. This blends display opacity only, never numerical measurements. At most two scalar layers coexist; rapid replacements finish the prior transition and release its old layer/callback. App reduced-animation and browser reduced-motion preferences bypass the fade. Slow server responses can still delay advancement; this is not a guarantee of constant playback FPS.

Charts now place their full heading, units, location and source-time range in wrapping HTML above the graph. Axis labels use concise variable names with units, automatic margins, and no redundant single-series legend. PNG export retains source metadata and restores the compact on-screen layout afterwards. The point series still covers the selected batch only.

Verification: frontend typecheck, lint and production build passed. The final live browser suite passed **13 tests in 32.8 seconds**, including a deliberately blocked next-batch response (previous timestamp/scale retained, then correct new frame), all-date selection, graph layout at 1440, 1024 and 760px viewports, and PNG download with on-screen title restoration. Wide/narrow screenshots and the exported PNG were visually inspected. This is functional local verification, not a concurrent-user performance benchmark.

Crossfade follow-up verification: typecheck, lint and production build passed; the expanded live suite passed **15 tests in 53.1 seconds** on 2026-09-28. Additional checks observe the transition state and both-endpoint disclosure, final timestamp completion, rapid date scrubbing across batches, switching to salinity, and absence of any blending state under browser reduced motion. Prior delayed-response, colour-scale, graph-layout and PNG-export checks still pass. The rebuilt local frontend was restarted on port 4317. These tests verify transition behavior, not measured GPU frame rate or a zero-latency promise.

## Run / restart

Build root: `C:\Users\pc\OneDrive\Desktop\ocean_2`. Use two PowerShell terminals. No provider login or new download is needed for the existing prepared selection.

Terminal 1 — existing Python 3.12 environment and FastAPI:

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2'
$env:OCEAN_REQUIRED_PRODUCT_IDS='["p_7c8210052d41d41259724e2d"]'
.\ocean-env\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — Node/npm and frontend:

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2\frontend'
# Only after a clean install / changed lockfile:
npm.cmd ci
# Build once, and again after source/config changes:
npm.cmd run build
npm.cmd run start -- --hostname 127.0.0.1 --port 4317
```

Open [Project Ocean](http://127.0.0.1:4317/explorer). Backend [health](http://127.0.0.1:8000/health) and [surface readiness](http://127.0.0.1:8000/ready) are separate. An unconfigured/missing required surface product can return readiness 503 while health remains OK. This does not certify all sources or scientific comparison readiness.

For editing, stop the frontend with Ctrl+C and use `npm.cmd run dev -- --hostname 127.0.0.1 --port 4317` instead of production start. Do not run both on the same port. Stop only these owned processes; do not kill unrelated Node/Python processes. Local servers were left running at handoff, but must be restarted after shutdown.

Default backend origin is `http://127.0.0.1:8000`. If changing it, set server-only `OCEAN_BACKEND_URL` before building and starting Next. It must be an HTTP(S) origin without credentials/path/query. The browser uses same-origin `/backend/health`, `/backend/ready`, `/backend/api/v1/*`; provider credentials are never browser environment variables. No CORS workaround was required.

## Implemented scope

Source-time follow-up: TIME · SOURCE UTC accepts a manually typed or calendar-selected date/time with explicit Apply (or Enter). Exact membership is checked against current prepared product metadata in UTC. Invalid/empty/missing timestamps show an error and keep the prior frame. The available-source-time dropdown remains for discovery; switching product or timeline time resets the draft. This does not expose all dates in the raw archive—additional dates require separate operator preparation.

| Screen | Actual connected behavior |
| --- | --- |
| Explorer | Cesium geographic globe, existing BIO-ROMS V2 SST/SSS preview, 3 source timestamps, scalar/color controls, Argo points and grid-cell inspection infrastructure |
| Analysis | Backend source-grid-cell time series with actual coordinate/distance/units; Plotly chart and existing bounded exports |
| Profiles | 14 preserved Argo samples, QC/raw-adjusted provenance and sample selection; zero identified profiles is explicit, not a reconstructed vertical profile |
| Comparison | Existing immutable exploratory Copernicus salinity/Argo result: 2 pairs, 12 excluded, 14 evaluated; summary, assumptions/blockers, filtered pagination and current-page matched scatter |
| Data Sources | Four source families retained in registry, separate surface-preparation and acquisition states, selected product variable metadata |

Comparison selection is fixed by its saved snapshot; changing Explorer's product/time does not recompute it. Its statistics cover the full snapshot, not only the current filtered page. No browser request initiates downloads, matching, preparation or publication.

No synthetic fallback is used after live request failures. DataClient validates bounded responses; a dedicated adapter maps actual backend wire fields to UI presentation types. Rejected variable QC becomes a non-rendered null while original source fields remain in inspector provenance. Scientific units and false comparison-readiness/independence flags are preserved.

## Recovery provenance

Original input `C:\Users\pc\OneDrive\Desktop\frontend` had cached build/dependencies/config/assets but no ordinary source directories. It was not modified. The new project frontend was recovered from:

- 71 project TS/TSX sources in development bundle source maps;
- 2 CSS files extracted from development CSS;
- 18 historical handoff files (including older tests and missing modules);
- 8 original config/script files.

The [99-file baseline manifest](FRONTEND_RECOVERY_MANIFEST.json) records origin, sizes and SHA-256 before integration changes. `scripts/recover_frontend_source.mjs` inventories/exports source text without executing bundled app code. Three missing route wrappers and live adapter/comparison/tests were then implemented locally. Clean dependencies were installed from the lockfile; Cesium/Plotly assets were regenerated. Existing demo fixtures/older components remain for reference but are not the active data transport/comparison page.

Exact latest-original source/design parity cannot be guaranteed: source maps are a development snapshot, and some fallback modules came from an older Part 6 handoff. In particular the source inventory uses the recovered simpler implementation.

## Verification evidence

Source-time follow-up verification (2026-09-28): typecheck, lint and production build passed; expanded live suite **9 passed in 32.5 seconds** against the restarted production server. New checks cover exact UTC membership, invalid calendar dates/leap dates, missing/sub-frame times, empty input, valid Apply, no frame request after invalid Apply, dropdown/timeline synchronization and disabling after switching to an unprepared dataset. The time-control screenshot was visually inspected. The seven-test results below describe the preceding integration checkpoint.

Windows, Node 24.20.0, Next 16.3.5, Edge with software-WebGL fallback enabled. Both services bound to loopback. Tests use actual prepared local inputs, not provider-network access.

- `npm.cmd run typecheck` and `npm.cmd run lint`: passed.
- `npm.cmd run build`: passed; all workspace routes generated.
- `npm.cmd exec playwright test -- --config playwright.live.config.ts`: **7 passed in 19.6 seconds against the production build**.
- Coverage: real health/readiness/catalogue/product/frame/time-series/acquisition/observation/comparison contracts; omitted readiness reason; QC rejection/provenance/mismatched selection; visible globe/frame; tab navigation and retained SSS choice; comparison all/excluded/matched rows; backend failure without demo substitution; profiles/source inventory.
- Explorer and comparison screenshots inspected locally. Tab-navigation Plotly resize/unmount rejection was fixed; tested navigation reports no page errors.
- Earlier 5-test development run passed after fixing readiness mapping, badge locator and resize handling. Historical recovered demo suites were not run as live acceptance and are not claimed to pass.
- Backend prior 5.10 regression: 1,021 passed / 4 Windows skips / 1,835 warnings; no backend Python code or science policy changed in this integration.

Tests require both servers running, the existing prepared IDs and installed Edge. They are local integration checks, not portable offline fixture tests. Screenshots/results are ignored generated files under `frontend/test-results/`.

## Remaining limits

Strict scientific matching remains blocked; comparison is explicitly assumption-based, not independent validation. Served depth slices, vectors and volume are unavailable; corresponding UI controls remain disabled. Copernicus acquisition/native scientific preparation does not imply general current/depth serving. GODAS connectivity and glider metadata/region issues remain documented source limits. The BIO-ROMS V2 input is surface-only despite the 3D geographic globe.

No production hosting/authentication, multiuser load, sustained memory/GPU/animation benchmark, exhaustive export/accessibility/mobile acceptance or all-source/all-region scientific integration was established. A working globe does not complete every problem-statement capability. Further backend capabilities and deployment are separate tasks.
