# Model preparation contract · version 1

Created in 5.2 and implemented in 5.3 on 10 September 2026. Schemas, local processor, operator CLI, typed metadata, immutable publication and readback are implemented for the verified Copernicus selection. HTTP serving and comparison remain disabled. [Actual results](MILESTONE_5_3.md).

## Boundary and rationale

Keep the working INCOIS surface products and Argo observation collections unchanged. A depth-resolved model uses a separate private `m_` namespace, because the existing `p_` manifest asserts surface-only dimensions. Do not stretch it into a misleading four-dimensional product or make `/ready` accept models implicitly.

The first supported preparation input is a verified, local Copernicus acquisition of the daily/monthly `GLOBAL_MULTIYEAR_PHY_001_030` datasets already accepted by the acquisition adapter. This does not replace INCOIS/GODAS or observations. Other model grids need separately inspected adapters; BIO-ROMS V2 does not gain depth/current fields through this schema.

| Stage | Current responsibility |
| --- | --- |
| Acquisition | Existing operator workflow preserves `input.nc` and its provenance. |
| Contract — implemented in 5.2 | Validate selection, axes, native indices, budgets, identity and private publication manifest. No I/O. |
| Preparation — implemented in 5.3 | Verify bytes/metadata, read bounded native samples, publish and readback/reuse immutable scientific output. |
| Compatibility/matching — pending later approval | Resolve the audit gates, conversions, QC, temporal windows and matching policy. |
| API/frontend — not enabled here | No new route, readiness requirement, display preview or frontend component. |

## Executable contracts

Source: [models.py](../backend/app/schemas/models.py). Existing [acquisition selection](../backend/app/schemas/acquisition.py) and [resource ceilings](../backend/app/schemas/products.py) are reused, not duplicated with looser limits.

| Type | Meaning |
| --- | --- |
| `ModelPreparationRequest` | Exact acquisition ID, 1–4 unique supported source variables and explicit region/time/depth selection. |
| `ModelLimits` | Existing performance ceilings plus at most 64 selected native depth levels. |
| `ModelProvenance` | Acquisition/input SHA256 identities, dataset/version, client transforms, acquisition time and real/synthetic label. |
| `ModelAxes` | Actual increasing UTC times, positive-down depth centres, latitude/longitude and contiguous original source indices. |
| `ModelVariableInfo` | Original names, units, standard/long names, dtype and cell methods; definitions remain unharmonized. |
| `ModelScientificPolicy` | Fixed native sampling/mask policies and unresolved scientific gates; comparison and API serving are false. |
| `ModelIdentity` | Validated scientific inputs/selection/axes/metadata/policies/limits and deterministic `m_` ID calculation. |
| `ModelManifest` | Private identity plus output file hashes/stats and UTC creation time; not a filesystem existence check. |
| `serialize_model_manifest` | Revalidates and caps UTF-8 publication JSON before any future file write. |

Contracts forbid unknown fields and reassignment. New sequence fields are tuples so they cannot be mutated in place. Construct from validated input; Pydantic's unchecked `model_construct`/`model_copy(update=...)` are not validation paths. A valid schema does not prove file contents, scientific definitions or provider access.

## Operator selection

[model_preparation.example.json](../config/model_preparation.example.json) targets acquisition `a_9e918d43555ffc26d3659e08`: four fields, 65–66E/1S–0N, January 29–30 2019, 0.49402499198913574–10 m. Run `python -m scripts.prepare_model --request config/model_preparation.example.json` using the project environment. This is local preparation/reuse, not acquisition or comparison.

- Select native centres inclusively; no time rounding, nearest-depth substitution, extrapolation, interpolation or striding.
- Longitude must be non-wrapping in `[-180,180)` for returned centres; latitude is signed degrees. Region bounds must increase.
- Selection timestamps must be timezone-aware and span more than zero and at most 31 days. The existing selection schema normalizes explicit offsets to UTC. Stored actual timestamps must be explicit UTC.
- Vertical selection is `depth_m`, not `pressure_dbar`; a single selected depth centre is supported.
- Variable order is preserved and included in identity; callers should retain the same order for repeat requests. Unknown or duplicate source variables fail.
- A requested 10 m ceiling does not invent a 10 m model level. Actual axes, not request bounds or inherited globals, define returned coverage.

## Required preflight for Part 5.3

These obligations are implemented by `processing/prepare_model.py` for the supported rectilinear subset; schemas alone do not verify files:

1. Resolve the exact acquisition under this project's private raw directory. Reuse containment/locality protections; reject placeholders, symlink escapes and unpublished staging directories. Never accept arbitrary user-upload paths.
2. Bounded-read and validate its manifest; verify ID, Copernicus source/dataset/version, recorded coordinate mappings and selected variable availability. Rehash `input.nc` against the manifest and record the manifest hash. Record stat identities around reads; fail on ordinary concurrent changes. This is not an adversarial filesystem snapshot guarantee.
3. Inspect metadata before field reads. Accept only supported one-dimensional rectilinear `time/depth/latitude/longitude` axes and numeric four-dimensional fields. Reject unsupported groups/types, descending/duplicate/curvilinear/sigma/staggered layouts, calendars, coordinate units/ranges or unsupported QC/ancillary declarations. Do not silently sort, rotate or reinterpret them.
4. Check bounded coordinate counts and storage chunk sizes before materialization. Derive actual axes from the file, not `field_date`, `z_max` or other inherited global coverage. Validate monotonicity, finite values and source-index alignment.
5. Select intersecting centres and fail clearly on empty selection. Enforce the declared limits before any science-array allocation. Contiguous index sequences must actually match source coordinates; a self-consistent manifest alone cannot establish that fact.
6. Validate original units, packing and ranges per inspected variable. Preserve masks and missing values; reject inconsistent encoding rather than guessing. Preserve source cell methods exactly; missing declarations should be explicitly recorded, not invented.
7. Read/write one bounded variable/time/depth horizontal slab at a time with explicit chunk/cache limits. Validate output against selected source samples, masks, shape and provenance before publication. No full raw-dataset load and no network work.

Inherited globals and client changes must remain visible in provenance. A contradiction affecting coordinate interpretation blocks preparation; an inherited global coverage label can be retained as a documented discrepancy when actual axes are valid. Preparation must not silently resolve the Part-5.1 averaging or temperature-definition gates.

## Native scientific storage

Implemented layout, first created in 5.3:

```text
data/models/<model_id>/
    fields.nc
    source_metadata.json
    manifest.json
```

`fields.nc` stores decoded float64 values in `(time, depth, latitude, longitude)` order, source-centre resolution, real UTC labels, positive-down metre depths and per-variable missing masks. Missing values stay missing, never zero. Do not pool four variables into one common validity mask. Preserve native units; do not multiply practical salinity by 1,000 or convert temperature in this checkpoint.

Decode packing exactly once. Preserve source fill/scale/offset/valid-range attributes in the separate metadata snapshot, not as active packed-data attributes on decoded float64 output. Apply declared valid ranges in the proper packed/decoded domain before publication; Part 5.3 fixtures verify raw-domain fill/range masks and negative scale factors. Output fill/missing encoding must be explicit and verified on reopening.

`source_metadata.json` is a bounded private snapshot of original acquired global and coordinate/variable attributes, including packing/ranges/units, client transformations and identified discrepancies. Preserve types using a documented JSON-safe representation (including nonfinite attribute values); do not silently truncate metadata. It is the acquired client's provenance, not an unmodified provider file claim. Its SHA256, byte size and stat identity belong in the manifest. It must not contain credentials or copied private history. Part 5.3 implements the typed snapshot in `schemas/model_metadata.py`: flattened values retain dtype/shape, with numeric nonfinite values stored as explicit tokens. Client transformation details live in manifest identity provenance.

The scientific file and metadata snapshot are immutable derived artifacts; raw acquisitions remain untouched. No preview is required for the first scientific preparation. Any later display cache lives separately and never supplies matching samples.

## Identity and publication

`ModelIdentity.model_id()` computes `m_` plus the first 24 hex characters of SHA256 over canonical UTF-8 JSON (sorted object keys, compact separators, ASCII escaping, no NaN). Identity includes request, actual axes/source indices, input and acquisition-manifest hashes, client/version provenance, variable metadata, resource limits, scientific policies and processing version `model_native_1`. Thus a changed source, acquisition record, selection, real/synthetic mode or processing policy cannot silently reuse the same full identity.

Output mtimes, hashes and publication clock are outside this identity. On an ID collision or pre-existing directory, compare the **full** validated identity and all file hashes/stats before reuse; never rely on the shortened ID alone. A changed source-metadata encoding requires a processing-version change.

For 5.3: write to a private stage on the same filesystem, close files, reopen/validate and hash all outputs, serialize the bounded final manifest, then atomically publish the complete directory without replacing an existing destination. Manifest-backed completed directories alone are discoverable. Verify source identity again before publication; an interrupted or conflicting stage is not a product. No public reader exists yet.

## Resource ceilings

| Resource | Maximum contract ceiling |
| --- | --- |
| Source variables | 4 |
| Actual timestamps | 12 |
| Selected native depth levels | 64 |
| Each horizontal axis | 10,000 centres |
| All selected scalar values | 8,000,000, including variables × time × depth × latitude × longitude |
| Source decompressed chunk | 32 MiB |
| Per-variable NetCDF cache | 16 MiB |
| One scientific output file | 128 MiB |
| Manifest and separate source-metadata JSON | 512 KiB each |

The processor carries `config/performance.yaml` limits into `ModelLimits`; operators can tighten but not raise ceilings. Source chunk/cache budgets are enforced. Model-directory entries, including private stages, are conservatively capped at 64. These limits are not an OS memory sandbox or browser-performance measurements.

## Scientific gates stay closed

The [5.1 audit](MILESTONE_5_1.md) remains the scientific evidence source. This contract does not retrieve new scientific sources or resolve its findings:

- Preserve midnight source labels; averaging windows remain unresolved. No invented noon shift or instantaneous interpretation.
- `thetao` remains source-defined potential temperature with unresolved model temperature scale and no asserted numeric reference pressure. Other variables explicitly mark the temperature-scale field not applicable.
- Source depth reference remains unharmonized with observations. No pressure conversion, bottom extrapolation or sea-surface/ellipsoid equivalence.
- Per-variable masks are not independent bathymetry, coastline connectivity or full-bottom support. Stored `uo/vo` do not establish render-verified current vectors.
- No Argo raw-to-adjusted change, QC-policy change, quantity conversion, matched pair or metric is produced.
- `comparison_ready=false` and `api_serving=false` are fixed in this schema version. Enabling either requires a later reviewed contract/version, not toggling a flag.

## Verification and next handoff

Tests live in [test_model_contracts.py](../backend/tests/test_model_contracts.py). They use synthetic Python payloads and test validation, native-index preservation, gates, immutability, deterministic identity, JSON round trips and byte/file budgets. They do not write NetCDF, contact providers or certify real scientific values. Exact run results are recorded in [MILESTONE_5_2.md](MILESTONE_5_2.md).

Part 5.3 has implemented/tested these obligations and prepared the small existing Copernicus acquisition. See [MILESTONE_5_3.md](MILESTONE_5_3.md) for exact verification. Next is separately approved 5.4; comparison, new serving routes and frontend remain later work.
