# Part 2 — local registry and metadata inspection

Checkpoint: 2026-09-10, Windows / Python 3.12.10, in `C:/Users/pc/OneDrive/Desktop/ocean_2`. The user approved this part while the BIO-ROMS V2 download was still pending. Frontend remains last; part 3 needs separate permission.

## Implemented

- A bounded, schema-validated YAML registry preserves local BIO-ROMS V2, GODAS 2022–2025, Copernicus, Argo, and IFREMER gliders. Published descriptions are not inspected local facts.
- A local adapter checks the configured final `.nc` path under project `data/raw/`, reports unavailable/invalid/uninspected inputs, and ignores differently named partial downloads. Remote adapter entries remain `not_configured` / `adapter_not_implemented`; they are not contacted.
- Read-only netCDF4 header inspection inventories actual root dimensions/unlimited flags, variables, shapes/types/chunking, global/variable attributes, units, calendars, fill/packing/QC declarations, and evidence-labelled coordinate candidates. It does not read variable or axis values.
- Optional MD5 verification streams all bytes in 1 MiB blocks. Optional JSON report saving is atomic, bounded, and outside raw files. File size/mtime checks detect ordinary changes during inspection; they are not immutable snapshots.
- API startup and `/health` remain independent of registry loading, NetCDF inspection, and scientific imports. No new HTTP endpoint or startup job was added.

## Commands and outcomes

Run from the project root with the existing environment:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.inspect_dataset status
```

`status` loads configuration and checks final-path filesystem information only; it neither opens raw content nor consults saved inspection reports. Exit code 0 means the registry/status request succeeded, not that datasets are ready.

Only after the download finishes, use:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.inspect_dataset inspect incois_bio_roms_v2 --verify-checksum --save
```

The configured destination is `data/raw/incois/bio_roms/v2/pCO2-Corrected_INCOIS-BIO-ROMS_v2.nc`. Do not rename a `.crdownload` or another partial file to this name. Offline/recall placeholders are unavailable; a completed input must actually be local.

`--verify-checksum` is optional and can take time because it reads the full file. The registered expected MD5 is `78b7c0fbaa00db58a31563bb442a693b`, from the [authors' V2 record](https://zenodo.org/records/14614739). This checks integrity against published bytes, not source authenticity. Without the flag, checksum status stays `not_checked`.

`--save` creates `data/metadata/` if needed and replaces only `data/metadata/<dataset_id>.json` through a temporary file and atomic publication. Without this flag, no report is written. Reports include source/version/origin, UTC inspection time, local relative path, stat identity, checksum outcome, header findings, and `prepared: false`. Inspection time is not a known acquisition time. Metadata may contain private original attributes; reports are operator-only, Git-ignored, and not browser assets. A saved snapshot does not prove the current file is unchanged.

The adapter checks the complete wrapped report with the same serializer/byte budget as storage before declaring inspection success. Metadata-limit failure is `unsupported`, not successful-but-unsavable inspection. If header inspection fails after hashing, the adapter rechecks file identity and clears the checksum result when the file changed or disappeared.

| Status | Meaning |
| --- | --- |
| `not_configured` | Registered remote source has no implemented acquisition adapter yet. |
| `unavailable` | Final local file is missing/inaccessible/non-local, or inspection dependencies are unavailable. |
| `uninspected` | A nonempty local file has not been inspected by this request, or it changed during inspection. |
| `invalid` | Empty/corrupt input, unsafe input path, or checksum mismatch. |
| `unsupported` | The file uses unsupported metadata/types/groups or exceeds prototype metadata limits. |
| `not_prepared` | Header inspection succeeded; no scientific data has been prepared. |

Inspection exits 0 only for `not_prepared`; other results and safe operator errors exit 2. No state is called `ready`. A checksum mismatch stops before header inspection. Future preparation must separately require input integrity and scientific validation.

## Scientific and resource boundaries

Coordinate hints are not coordinate validation. Coverage is limited to declared global attributes labelled `verification: not_computed`; axis ordering/ranges, true dates, temporal averaging support, and depth/vector/render capabilities remain unverified. `capability_status` is `not_evaluated`. QC/mask declarations are preserved, not applied. Nonfinite attribute values serialize as JSON `null` with an explicit report observation; raw inputs are unchanged.

The inspector rejects hierarchical NetCDF groups and custom enum/compound/numeric variable-length types. Supported primitive root variables and strings remain metadata-only. Limits reject oversized reports rather than silently dropping fields:

| Limit | Bound |
| --- | --- |
| Registry input / entries | 128 KiB / 100 entries |
| Dimensions / variables | 64 / 512 |
| Attributes per object / total | 128 / 4,096 |
| Attribute array elements | 2,048 |
| Individual attribute bytes | 64 KiB for strings/arrays |
| Names | 256 characters |
| Serialized metadata nodes | 65,536 |
| Metadata JSON / saved wrapped report | Each capped at 2 MiB |
| Checksum read block | 1 MiB |

These bound metadata processing/output, not the NetCDF library's internal allocation while opening a file or retrieving an attribute. Accept trusted local operator inputs only; this is not a safe arbitrary-upload service or a process memory/time sandbox. No 9.2 GB runtime benchmark was performed. netCDF4 is used directly to avoid implicit xarray coordinate/index loading in this first inspection stage; xarray processing remains part 3. [netCDF4 API](https://unidata.github.io/netcdf4-python/), [xarray open_dataset](https://docs.xarray.dev/en/stable/generated/xarray.open_dataset.html).

## Verification

The final configured V2 path was checked locally and returned `unavailable` / `file_missing`; other entries returned `not_configured` / `adapter_not_implemented`. No real ocean file or user partial-download content was opened, hashed, renamed, or modified. No real-data report or prepared output was generated.

Offline tests use tiny synthetic NetCDF files in temporary directories. They cover metadata preservation, nonfinite JSON, no value reads, file closure, unsupported structures, bounds, registry/path validation, local states, checksum failures/changes, report publication, CLI flags, and the unchanged health/startup contract.

Final combined result: **113 passed, 4 skipped, 2 dependency warnings** (117 collected). The three added regression cases verify checksum clearing after change/deletion plus metadata failure, and the complete wrapped-report size limit. Ruff lint passes and Ruff format verifies all 26 Python files. `pip check` reports no broken requirements. Local Markdown links and fenced blocks were checked in all 11 Markdown files.

The four skips are actual symlink-escape tests: two input-resolution variants and two report-destination variants. Windows denied creating those temporary test symlinks with error 1314 (privilege not held). Traversal/absolute-path validation and other path tests passed, but real symlink/junction behavior was not fully verified on this machine; do not report those skipped cases as passing. No privilege escalation or system policy change was attempted.

Reproduce from the project root:

```powershell
.\ocean-env\Scripts\python.exe -m pytest -c backend/pyproject.toml
.\ocean-env\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m ruff format --check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m pip check
```

Added pinned runtime packages: netCDF4 1.7.4, NumPy 2.5.3, cftime 1.6.5, and PyYAML 6.0.3; certifi 2026.7.22 is shared by runtime/test dependencies. Provider clients, xarray, and pandas were not installed in this part. Full pins are in `backend/requirements.txt` and `backend/requirements-dev.txt`.

Known dependency warnings remain visible: Starlette TestClient deprecates its current HTTPX integration in favor of `httpx2`; Starlette also references the deprecated AnyIO `BlockingPortal` alias. The existing tested test-client stack is retained for this part; no warning suppression or unrelated upgrade was introduced.

## Next part — not yet authorized

After permission, start bounded preparation and scientific data API contracts, validating coordinates/time/coverage/capabilities before subsetting or exposing data. Tiny labelled fixtures can support development while the download is pending; real V2 must still be inspected and checksum-verified before real-source preparation. `/ready` needs defined local prerequisites before implementation. Acquisition adapters, comparison, and frontend remain their later milestones. No Git operations were performed.
