# Part 4 — source acquisition and scientific observations

Build: `C:/Users/pc/OneDrive/Desktop/ocean_2`. User approved this part on 2026-09-10. This checkpoint implements operator acquisition and observation processing, not model-observation comparison or frontend. Parts 1–3 and the original BIO-ROMS input/prepared product remain intact.

## Implemented boundaries

| Source | Implemented adapter | What success means |
| --- | --- | --- |
| INCOIS BIO-ROMS V2 | Existing checksum-verified local inspection and surface preparation | Existing SST/SSS product remains available; no new version or invented vertical fields. |
| INCOIS GODAS | Recorded HTTPS OPeNDAP endpoint, explicit inspected variable/coordinate names, bounded rectilinear subset; local LAS export import fallback | Acquired NetCDF plus provenance, not automatically a prepared surface/depth/current product. |
| Copernicus | Official `copernicusmarine` toolbox; explicit supported product dataset ID/version, strict-inside region/time/depth subset | Acquired model subset with source identity; no quantity conversion or current-orientation certification. |
| Argo | Official IFREMER ERDDAP via Argopy core expert mode, bounded transfer before scientific loading | Original ERDDAP response plus client-processed NetCDF, both with checksums; not untouched GDAC data. |
| IFREMER gliders | Anonymous FTP, one explicit v2 deployment file, streaming byte/deadline limits; EGO processing through xarray | File acquisition is separate from successful sample/QC normalization and geographic overlap. |

`acquire_dataset` runs provider code in a disposable child process with a 5–180-second deadline, disabled stdin/stdout/stderr, and no credentials in arguments. Network/library work never starts at app construction, health, readiness, or an HTTP request. A socket timeout and child deadline bound different failure modes; library allocations are not an OS memory sandbox. No automatic retries, service monitor, persistent queue, or background job endpoint was added.

Acquisitions publish immutable `data/raw/acquisitions/a_<id>/input.nc` and `manifest.json`. Argo also retains `provider_input.nc`, the original bounded ERDDAP response before client transformations. A fixed private filename keeps path handling simple; the original source basename is recorded in the manifest. The original BIO-ROMS download is unchanged. Successful acquisition has status `acquired_not_prepared`; header inventory alone does not prove rendering or comparison readiness.

Defaults: 64 MiB maximum acquired file, 2 million values, 20,000 Argo rows, 90-second child deadline. Hard request ceilings: 128 MiB/file, 8 million values, 100,000 Argo rows, 180 seconds, 31-day remote subset interval, four model variables, 10,000 axis entries, 32 MiB decoded source chunks, 64 acquisition entries. Whole single-file FTP/local acquisition is not presented as geographic subsetting. Exact request fields/validation live in `backend/app/schemas/acquisition.py`; operator requests may lower the limits.

The official toolbox uses process-only `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`, with missing credentials rejected before import/network. SDK calls get explicit credentials, a private staging credential-directory setting, bounded retries/timeouts and no TLS bypass. Do not send credentials in request JSON, chat, browser configuration, or logs. Source code never enables `verify=False`. For public ERDDAP, a standard certifi CA bundle is used with hostname and certificate verification enabled; this corrected the local default Windows trust-store failure.

## Operator commands

From the build root, install the pinned requirements, then run individual commands only for the source/selection you intend to acquire:

```powershell
.\ocean-env\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\ocean-env\Scripts\python.exe -m scripts.acquire_dataset --list
.\ocean-env\Scripts\python.exe -m scripts.acquire_dataset config/acquisition.argo.example.json
.\ocean-env\Scripts\python.exe -m scripts.acquire_dataset config/acquisition.glider.example.json
```

The Argo example requests 65–75E, 5S–5N, 2019-01-27 through 2019-01-30, 0–10 dbar, at most 1,000 rows/8 MiB/60 seconds. It does not fetch the entire comparison box/archive. The glider example downloads the single Bella file (Antarctic, outside the comparison box); it does not demonstrate Indian Ocean overlap. Re-running a fetch can contact the provider again before reuse is established; use `--list` to inspect already acquired files.

For a GODAS manual export, place the original small NetCDF under this project's `data/raw/incois/godas/2025/`. An operator request has `provider: "local"`, `dataset_id: "incois_godas_2025"` and the project-relative `local_path`; do not include a region/time selection for a byte-preserving file import. The source family is operator-assigned, not proof that arbitrary local bytes came from INCOIS; original retrieval time remains unknown.

For live GODAS, use `provider: "godas"`, the registered yearly dataset ID, inspected `variables`, and `coordinates` containing the actual longitude/latitude/time/depth variable names. Supply `selection` with `region`, timezone-aware `start_time`/`end_time`, `vertical_min`, `vertical_max`, and `vertical_kind: "depth_m"`. Unknown coordinates, unsupported grids, missing variables, or empty intersecting source centres fail explicitly. Do not invent GODAS aliases to make a request look configured.

Copernicus uses the same selection/mapping fields plus `provider: "copernicus"`, registry ID `copernicus_global_multiyear_phy`, and an explicit `provider_dataset_id`/`provider_version`. Daily version `202311` was verified on 2026-09-10; monthly/version changes still need their own catalogue check. `config/acquisition.copernicus.example.json` requests `thetao`, `so`, `uo`, `vo` for 65–66E/1S–0N, Jan29–30 2019, depth `0.49402499198913574`–10 m, with 16 MiB/file, 2 million values and 180-second limits. The lower depth is the actual shallowest model centre: strict-inside rejects a 0 m bound outside source support. `thetao` is potential temperature, not automatically equivalent to observation `TEMP`. [Official product manual](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf), [toolbox Python API](https://toolbox-docs.marine.copernicus.eu/en/stable/python-interface.html).

With the two server-only credential environment variables supplied by a private operator session, run:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.acquire_dataset config/acquisition.copernicus.example.json
```

No credential values belong in this JSON or command. A verification-only `copernicusmarine.login(check_credentials_valid=True)` call does not write a login file; this is distinct from the SDK's ordinary login command. Re-run acquisitions only deliberately; saved manifests/data do not require another login just to inspect them.

Prepare observations from one successful acquisition. The verified local ID is shown below; use the newly returned ID if a future acquisition differs:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.prepare_observations --dataset argo_gdac --acquisition a_d30181bd8998aca81bb33be1 --request config/observations.example.json
```

Alternatively supply `--input data/raw/<source>/<file>.nc` instead of `--acquisition`. Direct local inputs carry `prior_client_filtering_unknown`; the CLI does not claim Argopy expert provenance for an arbitrary file. Acquisition mode checks source identity, the client policy and input checksum/stat before publication. `--synthetic` explicitly labels a fixture; an acquired synthetic input can never be promoted to real. The example observation request uses the comparison box, Jan–Mar 2019 and 0–10 dbar; edit a copy for another actual source window. Do not substitute the Antarctic Bella file and claim overlap.

## Observation science and storage

Versioned `ObservationRequest` selects region, inclusive dates (at most 366 days), pressure bounds, variables including `PRES`, and explicit `raw` or `adjusted` values. No automatic raw/adjusted fallback. Preserve both values, their QC, adjusted errors, data modes, source variable names/units, input checksum, sample index and identity. Argo profile files use `N_PROF/N_LEVELS` and `JULD`; Argopy point outputs use `N_POINTS` and `TIME`.

Policy `core_flags_1_2_no_fallback_v1` requires accepted time/position/selected-pressure QC and per-variable QC. In-range rejected samples remain inspectable with explicit exclusion reasons, not silently removed or zeroed. Flags/modes that cannot establish eligibility do not become good by default. Missing filter coordinates and outside-selection samples have separate counts. This is a conservative core-parameter policy, not complete Argo BGC or EGO scientific certification. Fluorescence calibration remains unevaluated. [Argo QC guidance](https://argo.ucsd.edu/data/how-to-use-argo-files/), [Argopy mode behavior](https://argopy.readthedocs.io/en/latest/user-guide/fetching-argo-data/user_mode.html).

Do not merge different source profiles. Raw Argo file profiles include the source profile index; ambiguous point outputs without an explicit profile identifier remain `ambiguous_points`. Platform/cycle/direction/CONFIG_MISSION alone cannot prove uniqueness. Gliders without verified profile identifiers stay tracks, not one fabricated deployment-wide profile. Sensor coordinates must align with sensor samples; separate GPS arrays are not zipped or interpolated automatically.

Pressure remains dbar, distinct from positive-down depth in metres. Fractional UTC timestamps are preserved. Unsupported calendars, variable units, layout, QC modes or inconsistent coordinate metadata fail clearly. Temperature/salinity definitions are not harmonized and comparison is always disabled. Source declared ranges are interpreted using their packing (including negative scale); raw/adjusted encodings and decoded bounds are retained. Range-invalid science becomes missing; coordinate-range conflicts are explicit errors, not silently repaired dates/positions.

Glider coordinates scan in 4,096-row blocks up to a separate one-million-source-row ceiling, keeping at most 5,000 selected coordinates before reading science. Argo input remains limited to 100,000 rows and 64 MiB conservative decoded input. Both paths bound local source files at 256 MiB, metadata at 2 MiB and source chunks at 16 MiB; unused glider engineering arrays remain lazy. Native-library header/cache allocation still is not an OS process-memory sandbox. `input_samples` counts scanned source samples, not the entire upstream archive; selection metadata is a requested filter, not proof of complete regional/time coverage.

At most 5,000 selected scientific samples become one private collection (16 MiB serialized ceiling). Atomic storage is `data/observations/o_<id>/collection.json` plus a final typed manifest with prepared-file checksum/stat and preparation time. IDs depend on input/selection/processing policy, not display resolution. Repeated identical preparation reuses unchanged output; conflicts are not overwritten. Publication and HTTP reads never alter original inputs.

## Read-only HTTP contracts

| Route | Meaning |
| --- | --- |
| `GET /api/v1/acquisitions` | Available local acquisition manifests/stat identities; no raw NetCDF reads, provider requests or live-health claim. |
| `GET /api/v1/observations` | Bounded local collection catalogue; invalid/missing collection files are not advertised as ready. |
| `GET /api/v1/observations/{collection_id}` | Safe units, selection, QC policy, counts/capabilities and input checksum; no private filename/stat or raw samples. |
| `GET /api/v1/observations/{collection_id}/samples` | Scientific samples, `offset`/`limit` pagination (1–500/page), optional exact `profile_id` filter. |

Observation pages validate the bounded private collection/hash and return original selected samples with QC, not downsampled previews. Each response is capped at 2 MiB; lower page size if necessary. A small page still reads/verifies up to the 16 MiB collection; it is not a constant-time random-access database. The collection catalogue is capped at 32 entries. File identities/limits are trusted-local-input checks, not an authenticated public-upload service.

All public routes use typed OpenAPI schemas, finite numbers or `null`, stable IDs and real/synthetic labels. HTTP errors omit private paths and arbitrary exception details. `/api/v1/datasets` remains the **surface-product** catalogue: other sources can have acquired inputs/observation collections without a surface product. Use the corresponding new catalogues, not repeated calls to a non-existent job endpoint. `/ready` still checks explicitly required real Part-3 surface products only; all-provider readiness is not claimed.

## Verification and live evidence — 2026-09-10

- Environment: Python 3.12.10; Argopy 1.4.0, xarray 2025.9.0, Copernicus toolbox 2.4.1, pandas 3.0.5. Argopy import failed with erddapy 3.3.0 (`_quote_string_constraints`); erddapy 3.2.1 was then installed and provider imports succeeded. This pin is verified for this build, not a universal Python-version remedy. `pip check` passed after dependency resolution.
- GODAS 2025: bounded HTTPS DDS request with a 12-second socket timeout returned `TimeoutError` after 13.02 seconds at 09:15 UTC. Exact live variables remain unverified; a timeout does not invalidate the dataset. No guessed GODAS field download was attempted.
- Copernicus initial checkpoint: both required environment variables were absent, so authenticated access had not been tested. The later credential-authorized follow-up below supersedes that access limitation without changing the earlier test evidence.
- IFREMER Bella: FTP downloaded 45,337,024 bytes as `a_9cbe844e66f3fbb520b0d235`, SHA256 `6c4b0f4087b1599c648f7c504c8fd14cebcaa02d4812fcc98258c260d397ad4b`. Actual header has 235,791 sensor samples, 566 GPS fixes, EGO 1.2, platform Bella, mode R; `FLUORESCENCE_CHLA` units are `count`, not concentration. TIME declares epoch seconds but `valid_max=90000`, while inspected values are about 1.707e9. Inspected TIME/POSITION/PRES QC entries are fill values. Do not override these findings to call the file scientifically ready. Its Antarctic position is outside the project box.
- Argo: verified-certifi TLS, ERDDAP URL encoding and bounded fixed-character decoding were corrected against the real service. Argopy's dropped latitude/longitude units are restored from validated provider metadata. Production acquisition succeeded at 09:31 UTC as `a_d30181bd8998aca81bb33be1`: client output 62,646 bytes, SHA256 `6a6de3db0d8b150783c25b39f99797944eed986eab915b1a6677bc1d9d2e96be`; original ERDDAP response 18,108 bytes, SHA256 `42cbf31dc51e28afb1c3e349723b53b5cf67ac9581145eb89ff83516e61b75cb`.

Real preparation published `o_c645f248f801845378f0fdaf` (21,802-byte private snapshot). All 14 selected rows have core eligible pressure/temperature/salinity and retained raw/adjusted values; they come from floats 1901804 and 2902577 at `2019-01-29T19:31:09Z` and `2019-01-29T22:49:26Z`, pressure 1–10 dbar. Exact comparisons against original provider float32 values passed for 42 raw plus 42 adjusted values. These remain `ambiguous_points`: profile IDs were not invented, depth conversion is absent and `comparison_ready` is false. A common date/box is not proof of scientific model-observation compatibility.

Health, configured readiness, surface catalogue, acquisition inventory, observation catalogue/metadata/sample pages and OpenAPI all returned 200 with actual local inputs in FastAPI TestClient. A five-sample page was 6,848 bytes; all 14 samples were 18,537 bytes. Thirty repeated in-process full-page requests gave nearest-rank p95 0.0171 seconds. This is a small real-page check, not browser latency or a guarantee at maximum limits. Original V2 verification still returned six exact source/served matches; no source file or existing surface product was overwritten. See [performance scope](performance.md).

Final integrated run: **379 passed, 4 skipped, 639 visible warning occurrences**, 383 collected cases, 142.70 seconds. The four filesystem escape tests were skipped because Windows did not grant file-symlink creation (`WinError 1314`), not counted as passed. Ruff lint passes, all 59 Python files pass format checks, and `pip check` reports no broken requirements. All 14 Markdown files passed local-link, fence and final-newline checks.

Warnings remain from Starlette's HTTPX/AnyIO deprecations, netCDF4 array-shape assignment under NumPy 2.5, and xarray's NumPy generic-timedelta usage. They were not hidden with warning filters; the final repeat used pytest's compact warning-summary display. An initial combined run had one failure in the existing default-calendar preparation fixture; its isolated rerun and the complete final rerun passed without changing that processor. No reproducible cause was established, so this is recorded as an intermittent test finding, not a diagnosed/fixed library issue.

Tests include source-family/path/credential guards, transport/size/deadline cases, real installed Argopy preprocessing with mocked transfer through observation normalization, raw/adjusted/QC/range/packing rules, fractional time, sample/profile/GPS alignment, a 100,005-row glider fixture proving bounded coordinate scans, scientific publication/corruption/conflict checks, operator provenance and typed HTTP pages. Network tests are not silently part of the offline suite. Real acquisition and value checks above are additional evidence. No browser/GPU, complete deployment load, full-water-column rendering, model-observation metrics or all-source performance claim is made.

## Copernicus credential-authorized follow-up — 2026-09-10

Verification-only toolbox login returned accepted in 14.098 seconds. Credentials were supplied to disposable processes through stdin/process environment, not command arguments, project configuration, browser code or a saved login file. Provider logs were not exposed. A bounded scan of 75 application/configuration/documentation files and the new acquisition's NetCDF/manifest found no supplied credential values or their direct Base64 representations. This is a scoped leakage check, not a claim about every file on the computer or the chat history. Temporary process state was cleared after completion. Credentials shared in chat should be rotated and future runs configured privately.

The [official daily dataset STAC](https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/GLOBAL_MULTIYEAR_PHY_001_030/cmems_mod_glo_phy_my_0.083deg_P1D-m_202311/dataset.stac.json) and [product data-access page](https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/services) verified version `202311`. STAC advertised 50 negative elevation levels; the installed SDK converts their sign, order and name to positive-down depth, with science rows reordered together. The adapter now explicitly requests `vertical_axis="depth"` and records that transform plus CF mask/scale/time decoding and re-encoding. These steps are not temperature/salinity harmonization or observation pressure-to-depth conversion.

An initial 0–10 m strict-inside request was rejected because 0 m is outside the model-centre support. Error mapping now reports `provider_request_rejected`, not a false no-samples result. Rejected credentials, missing credentials and unreachable authentication service also have separately tested, sanitized error mappings. A larger 65–75E/5S–5N, Jan28–30 attempt did not publish a completed acquisition; its final failure classification was not retained, so no specific transport cause is claimed. The subsequent smaller request succeeded without raising resource ceilings.

Successful acquisition: `a_9e918d43555ffc26d3659e08`, retrieved `2026-09-10T10:39:45.628992Z`, **54,832 bytes**, SHA256 `c92568212fc4b2b46f31162106bc7aced404e1c32d9675267d1d399c5abfb3a3`. The saved file was rehashed successfully and inspected read-only. `input.nc` and `manifest.json` are preserved under the corresponding private acquisition directory. The example JSON reproduces its 65–66E/1S–0N, Jan29–30 selection and version, but a new fetch may return a different content identity if upstream bytes change.

Actual dimensions are `(time=2, depth=8, latitude=13, longitude=13)` for every field: 2,704 values each, 10,816 total. All selected decoded field values were finite, with no masked values in this small selection. This does not establish whole-source mask behavior or independent scientific accuracy.

| Field | Actual source units / standard name | Decoded range in this subset |
| --- | --- | --- |
| `thetao` | `degrees_C` / `sea_water_potential_temperature` | 28.21018–28.79907 |
| `so` | `1e-3` / `sea_water_salinity` | 34.95437–35.39232 |
| `uo` | `m s-1` / `eastward_sea_water_velocity` | −1.06998 to −0.55727 |
| `vo` | `m s-1` / `northward_sea_water_velocity` | −0.12635 to 0.12268 |

Coordinates span exactly 65–66E and −1–0N. The eight model depths are approximately 0.494025, 1.541375, 2.645669, 3.819495, 5.078224, 6.440614, 7.929560 and 9.572997 m; they are not dbar and do not cover a full water column. Actual times are `2019-01-29T00:00:00Z` and `2019-01-30T00:00:00Z`, with stored `hours since 1950-01-01` and `gregorian` calendar. All four fields retain int16 packing, scale/offset/fill/valid-range metadata and `cell_methods="area: mean"`. No time-bounds variable was present. The manual's daily-mean description and actual midnight timestamps must be reconciled explicitly before comparison; no noon shift or temporal bounds were invented.

Acquisition inventory now lists Copernicus alongside the existing Argo/Bella inputs as `acquired_not_prepared`, `comparison_ready: false`. TestClient checks of health, configured surface readiness, acquisition/observation catalogues, the original V2 product metadata and OpenAPI returned 200. Acquisition inventory was 3,530 bytes and excluded private staging paths. There is still no Copernicus prepared model-serving pipeline or depth/current API; this download does not enable those UI controls or mark all sources ready.

Follow-up full suite: **386 passed, 4 Windows symlink skips, 640 warning occurrences**, 390 cases, 200.12 seconds. No failure reproduced in this run. Ruff lint, all 59 Python format checks and `pip check` passed. Seven added cases cover typed errors, explicit depth/provenance, safe example bounds and an installed-SDK packed-data depth/NetCDF roundtrip. The latter enforces socket guards and directly selects the NetCDF backend to avoid unrelated xarray plugin discovery. Its initial development run had triggered Argopy's metadata lookup through backend discovery; the corrected focused rerun passed eight Copernicus cases without that network warning. Existing third-party deprecations remain; the full suite used compact warning-summary display, not warning filters. Prior checkpoint findings above remain historical evidence.

The failed larger attempt left private staging directory `data/raw/acquisitions/.acquire_vcwxfuvw` (an incomplete `input.nc` and its request). An explicitly scoped cleanup was blocked by the execution tool, so it was left unchanged for operator review, never published or served. Do not treat it as an acquired dataset or resume it implicitly. No completed original input or prepared product was deleted or overwritten. No server, scheduled monitor, frontend, comparison job or Git operation was started.

## Remaining work

Finish source-specific live verification/configuration where blocked, identify scientifically usable in-box glider data, and prepare/validate depth/current model products before enabling those controls. Part 5 requires separate permission for quantity conversions, matching/exclusions, model-minus-observation residuals and bias/RMSE; it must use scientific samples and verified overlap, never previews. Frontend remains the last separately approved part.
