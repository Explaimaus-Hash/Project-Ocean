# Part 5.3 — native model preparation

Completed 10 September 2026 in `C:/Users/pc/OneDrive/Desktop/ocean_2` after explicit approval. Only this checkpoint was implemented; Part 5.4 and later work need separate permission. Frontend remains last.

## Outcome

The existing small Copernicus acquisition is now a verified, immutable native scientific product. It is **not comparison-ready or exposed by a new API**. Existing INCOIS surface products, Argo collections, glider inputs, source acquisition records and `/ready` behavior are unchanged.

| Item | Verified result |
| --- | --- |
| Acquisition | `a_9e918d43555ffc26d3659e08` |
| Prepared model | `m_35e4c0ab33c1469a334ca837` |
| Provider dataset/version | `cmems_mod_glo_phy_my_0.083deg_P1D-m`, `202311` |
| Fields | `thetao`, `so`, `uo`, `vo`; original units/definitions retained |
| Per-field shape | 2 times × 8 depths × 13 latitudes × 13 longitudes |
| Actual region | 65–66E, 1S–0N; not the full Project Ocean comparison box |
| Actual time labels | January 29 and 30, 2019, both 00:00 UTC; no noon shift |
| Actual depth range | 0.49402499198913574–9.572997093200684 m, positive down |
| Scientific values | 2,704 finite values per field; 10,816 total; no masked cells in this small source selection |
| `fields.nc` | 66,533 bytes, decoded float64, native resolution |
| `source_metadata.json` | 7,043 bytes, typed acquired-source attributes |
| `manifest.json` | 4,939 bytes, scientific identity and file hashes/stat records |

Files are private under `data/models/m_35e4c0ab33c1469a334ca837/`. The source input remains 54,832 bytes with SHA256 `c92568212fc4b2b46f31162106bc7aced404e1c32d9675267d1d399c5abfb3a3`. File hashes are recorded in the actual private manifest; nothing is copied to frontend/public.

## Implemented code

- [prepare_model.py](../backend/app/processing/prepare_model.py): contained/local input paths, acquisition/manifest hash validation, bounded metadata/coordinate preflight, exact native selection, slab processing, output readback, publication and reuse.
- [model_metadata.py](../backend/app/schemas/model_metadata.py): bounded typed source-attribute snapshots. Original dtype and array shape distinguish text from numeric `NaN`/`+Inf`/`-Inf` tokens.
- [operator command](../scripts/prepare_model.py): validated JSON request and safe result/errors; no provider download or HTTP service.
- [34 new fixture tests](../backend/tests/test_model_preparation.py): real NetCDF fixtures in temporary test folders with scientific values and failure assertions.

The [5.2 contract](MODEL_PREPARATION_CONTRACT.md) remains the canonical scientific/storage boundary. Existing schemas are reused without migrating old surface/observation products.

## Run or reuse

Run in Windows PowerShell from the build root:

```powershell
Set-Location -LiteralPath 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.prepare_model --request config/model_preparation.example.json
```

The saved request uses existing local bytes. No Copernicus login, network, new package, server or browser is needed. The command prints a bounded summary with model ID, shape, output bytes and false comparison/serving flags. Errors exit with code 2 and safe codes; they do not echo input JSON, credentials or private diagnostic traces.

Running the same request validates the full scientific identity, source/output hashes and source metadata, and re-reads all selected slabs before reuse. It does not rewrite a matching product. A conflicting/incomplete/corrupt destination is rejected, not repaired or overwritten. Changing the selection or scientific identity yields a different model ID.

This is an operator processing task, not an interactive HTTP call. Existing `/api/v1/acquisitions` remains acquisition-stage inventory and does not join derived models; its immutable `acquired_not_prepared` records are therefore not updated by preparation. No `/api/v1/models` endpoint exists.

## Validation and scientific handling

The processor requires the registered Copernicus source/dataset, recorded provider version and exact inspected coordinate mappings. Inputs must be completed local acquisition files under this project; symlink/junction escapes and cloud placeholders are rejected. Input/manifest hashes and stats are checked before use and again before publication/reuse return.

Only increasing 1D rectilinear time/depth/latitude/longitude axes and numeric `(time, depth, latitude, longitude)` fields are supported. Unsupported groups/custom types, calendars, coordinate definitions, sigma/staggered layouts, QC/bounds/ancillary declarations and incompatible units fail explicitly. Actual coverage comes from coordinate values, not inherited global dates or `z_max`.

Raw-domain packing is decoded exactly once into float64. `_FillValue`, `missing_value`, default NetCDF fill values, declared valid bounds and nonfinite values become per-variable missing masks. Valid-range attributes must have the native variable dtype; ambiguous domain/unsigned encodings are rejected, not guessed. Negative scale factors are tested. Active packed scale/offset/range attributes are not copied onto decoded output.

Scientific reads/writes are bounded variable/time/depth slabs, not a full raw-dataset materialization. Configured limits are inherited from `config/performance.yaml`; selected depths are capped at 64. Source chunk limits, per-variable cache limits, selected scalar counts, file sizes and metadata byte limits are enforced. These bounds are not a hard OS memory sandbox or a browser-performance guarantee. The NetCDF library can allocate internal header/attribute memory before a check returns, so inputs remain trusted local operator artifacts, not arbitrary public uploads.

Private source metadata retains global/variable attributes with dtype, shape and bounded values, including inherited coverage discrepancies. Client/version/transformation provenance stays in the scientific identity; it does not falsely claim an untouched provider source. Metadata names suggesting credentials/tokens are rejected. No historical chat/account material was read or copied.

Publish only after files close, every selected slab passes readback, hashes are recorded and the bounded manifest validates. A short exclusive `.publish.lock` protects cooperating writers around the non-replacing directory publication. Another process's lock is never removed. Failed known temporary outputs are cleaned; unrelated raw/staging directories are untouched. A crash can leave a private stage/lock requiring explicit operator review. This does not claim durability against power loss or protection from adversarial concurrent filesystem mutation.

## Verification actually run

| Check | Result |
| --- | --- |
| New native-model fixture tests | 34 passed, 324 warnings, 4.30 seconds in the initial targeted run |
| Full final offline suite | 462 passed, 4 Windows symlink-permission skips, 964 warnings, 187.15 seconds |
| Lint | Ruff passed across backend and scripts |
| Formatting/dependencies | All 65 Python files passed format checking; `pip check` found no broken requirements |
| Markdown handoff | All 19 root/docs Markdown files passed local-link, code-fence and final-newline checks |
| Real source vs prepared output | All 10,816 decoded field values equal using an independent NetCDF automatic-decoding read; source time/depth arrays also equal |
| Real repeat-run reuse | Same model/manifest returned; all three output files and the raw input kept identical hashes, sizes and mtimes |
| Metadata integrity | Typed snapshot validates; scientific/snapshot file hashes and stat records match the manifest |
| Network boundary | Fixture runs and independent real verification blocked socket connections; no live provider access or credentials used |
| Publication state | No `.prepare_*` residue or `.publish.lock` remained after successful real preparation/reuse |

Tests cover masks versus zero, per-variable mask separation, smaller native selections/source indices, unsupported calendars/axes/units/groups/metadata, ambiguous packing, budgets, no overlap, changed source, corrupted output, failed write/readback/rename cleanup, foreign lock preservation and safe CLI failures.

Most warnings are existing NumPy/xarray/NetCDF array-shape or timedelta deprecations, plus Starlette/HTTPX/AnyIO warnings. New fixtures and the model writer also encounter the NumPy shape deprecation; one intentionally invalid `valid_min` fixture emits a casting warning. Four Windows symlink tests remain skipped because the OS denies test symlink creation. No guarantee of zero future errors or production readiness is implied.

The independent raw check deliberately reads the complete *small* 10,816-value selection, not the 9.2 GB BIO-ROMS file. V2/Argo/glider inputs were not rehashed in this checkpoint and were not written. Full-suite results include existing health/startup tests; provider modules remain out of app construction and health.

## Unresolved gates and next step

The [5.1 audit](MILESTONE_5_1.md) still applies: midnight/noon averaging semantics, model temperature scale/reference, observation pressure/depth/reference/uncertainty, adjusted D-mode selection, wet-domain support and matching tolerances are unresolved. Finite cells do not establish bathymetry or coastline connectivity. No converted temperatures, observation depths, matched pairs, metrics, current rendering or volume API are claimed.

Next, after permission: **5.4 — latitude-aware pressure-to-depth conversion**, retaining original pressure, uncertainty and vertical-reference provenance. Do not begin quantity harmonization, matching, new APIs or frontend without their own checkpoint approvals.
