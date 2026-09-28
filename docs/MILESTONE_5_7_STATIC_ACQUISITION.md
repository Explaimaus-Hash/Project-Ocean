# Part 5.7 — bounded static mask/bathymetry acquisition

Implemented and tested on 2026-09-17 after permission to continue the [support-evidence plan](MILESTONE_5_7_SUPPORT_EVIDENCE.md). This completes the narrow acquisition/grid-check checkpoint, **not real matching or the whole of 5.7**. No metrics, API or frontend was added.

## Implemented boundary

`backend/app/ingestion/static_support.py` provides a deliberately narrow public-HTTPS reader for the undownsampled version202311 bathymetry asset advertised by the official Copernicus catalogue. `scripts/acquire_static_support.py` is its explicit operator command. The earlier credential-based daily/monthly Toolbox adapter is unchanged. This path reads publicly accessible catalogue/Zarr objects without credentials; it does not log in, search account files, or disable TLS.

It validates the exact catalogue identity/asset and inspected Zarr-v2 encoding before requesting arrays. Latitude/longitude arrays must equal the existing prepared model selection exactly, with at most25 centres per horizontal axis. Every prepared depth must occur exactly in the static depth list after the explicit sign/order comparison. No nearest join, rounding, interpolation or display downsampling is used. The saved subset preserves original negative elevation values and source attributes; the source's `positive=down` attribute is retained as observed, not silently repaired or interpreted as a shared datum.

All50 mask levels and `deptho`/`deptho_lev` are retained for the selected horizontal region. Binary masks, contiguous wet columns, finite positive wet-column bathymetry and integer bottom-level values are checked. Numeric agreement between wet-level counts and `deptho_lev` is reported, **not promoted into a documented indexing convention**. Model-reference, time, observation wet status and candidate coastline connectivity remain independent gates.

Exact compressed source objects plus original catalogue/Zarr metadata are retained in a private `source_read_set/`, with byte counts and SHA256 hashes. This is an incomplete global read set, **not a complete Zarr store**: do not open it as a global dataset and treat absent chunks as dry/fill. `subset.nc` is read back against every selected array before publication. Catalogue/metadata are checked again after transfer, all saved objects are rehashed and the prepared model is reverified. These checks detect ordinary changes; they do not authenticate the publisher or guarantee remote chunk immutability during acquisition.

## Usage and enforced limits

Run only when another acquisition is explicitly wanted; this command performs network/file writes and does not reuse a saved snapshot automatically:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.acquire_static_support
```

The default model is `m_35e4c0ab33c1469a334ca837`; `--model-id` can select another verified small version202311 daily model. Unsupported identities or source layouts fail explicitly. Exit0 means acquired/grid-checked support only; exit2 means acquisition did not complete. Errors omit private paths/credentials/traces. No HTTP route, startup or health check calls this command.

- Fixed official HTTPS catalogue/asset allowlist, no redirects, credentials, retries or global-file fallback.
- At most1MiB per metadata object,4MiB decoded per chunk,64MiB cumulative response-body transfer,128MiB cumulative decoded chunks and128 requested objects.
- At most250,000 selected array elements; one source chunk decoded at a time after checking its Blosc size header.
- Socket timeout at most15seconds, cooperative160-second acquisition deadline and180-second parent-process timeout. Direct internal calls do not provide the parent-process hard timeout.
- Subset capped at4MiB; private manifest capped at64KiB. These are processing limits, not an OS process-memory sandbox.

Only an atomic final directory rename publishes a snapshot under `data/raw/static_copernicus/b_<digest>/`. Existing published directories are not overwritten. Failed private `.static_*` stages are not published or automatically deleted/reused; an operator must review them. The older unrelated `.acquire_vcwxfuvw` stage is untouched. A new explicit acquisition has new retrieval provenance; no deduplication/cache-reuse claim is made.

The current reader supports only the inspected public asset layout. If catalogue hosting, chunks or encoding change, review/update the adapter instead of weakening checks or downloading the full global file. Format references: [Zarr-v2 storage specification](https://zarr-specs.readthedocs.io/en/latest/v2/v2.0.html), [Numcodecs Blosc API](https://numcodecs.readthedocs.io/en/stable/compression/blosc.html). Existing pinned Numcodecs/NetCDF/NumPy dependencies are reused.

## Actual local result

Snapshot: **`b_b18353b728b66639c7787d55`** under `data/raw/static_copernicus/`. Status: `acquired_grid_checked_not_matching_ready`, `data_mode=real`, `comparison_ready=false`.

| Measurement | Verified result |
| --- | --- |
| Horizontal centres | 65–66E, 1S–0N;13×13, exactly equal to the prepared model |
| Mask shape | 50×13×13, source elevation ordering preserved |
| Actual body transfer | 4,664,667 bytes including repeated metadata |
| Cumulative decoded source chunks | 60,843,052 bytes, not peak RAM |
| Original objects retained/rehashed | 59 |
| Saved `subset.nc` | 31,037 bytes |
| Subset SHA256 | `ed0efdff6e48ef2fa7cae6824b900df3a71d40b3b480ed4b694f0d348b67af23` |
| Surface mask | 169 wet,0 dry native centres |
| Wet levels per column | 43–47; numeric agreement with `deptho_lev` |
| Bathymetry values | 3,194–4,688m; metadata is geoid-referenced |

An initial metadata probe timed out; a subsequent probe and the actual bounded acquisition succeeded. This is not evidence of guaranteed future connectivity. The511,420,508-byte global NetCDF was **not** downloaded. No credential was supplied or stored.

Independent post-publication checks rehashed all59 objects and the subset, checked saved dimensions/values and verified its stored file identity. Original model/observation inputs were not rewritten. The existing matching-input audit was rerun successfully: exit3, no stderr, nine salinity blockers, zero pairs and overlap not evaluated. The9.2GB BIO-ROMS original was not reread or changed.

## Verification

The latest targeted static group passes **38 tests**, with6 existing NumPy/NetCDF shape deprecation warnings. Coverage includes exact subset/read-set publication, metadata/grid mismatch, binary/holey masks, missing/invalid bottom data, unsafe keys, transfer/decode/deadline limits, truncated/compression-bomb headers, missing remote chunks and changed metadata before publication. Synthetic fixtures remain labelled synthetic and use no provider network.

Full regression passed **813 tests, with4 Windows symlink-permission skips and1,526 warnings in459.37seconds**. That run collected the initial29 static tests; the expanded latest38-test static group passed separately after additional transport/change-detection cases were added. These counts overlap and must not be added. Existing warnings remain NumPy/NetCDF/xarray/Starlette deprecations and the intentionally invalid-range fixture; no failing check remains in these runs.

Ruff lint/format passes for98 Python files; `pip check` reports no broken requirements. All27 root/docs Markdown files passed local-link, fenced-block and final-newline checks. The acquisition directory contains only the published snapshot, with no new unpublished stage remaining from this run. No Git operation, server, recurring job or frontend work was started. No browser-performance or production-readiness claim is made.

## Next part — request permission

Later update: the narrow [5.7-A local reader](MILESTONE_5_7_STATIC_READER.md) is now implemented. The paragraph below records the earlier proposal; observation binding and scientific-support policy still require 5.7-B/5.7-C approval. Do not reacquire the saved snapshot automatically.

Implement a verified local static-support reader/adapter that binds this snapshot to the model and selected observations, with explicit bottom/coastline/observation-cell policy and negative tests. Do not pass the acquisition summary directly into the matcher or mark wet/bottom/connectivity evidence verified by hand. Exact time intervals, vertical-reference compatibility and reviewed numerical tolerances remain unresolved; temperature semantics remain separately blocked. No provider clarification was sent. Request approval before further5.7 work;5.8–5.10 and frontend remain later.
