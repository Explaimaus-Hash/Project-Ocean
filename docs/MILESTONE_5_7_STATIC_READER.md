# Part 5.7-A — verified offline static-support reader

Implemented on 2026-09-17 as the next approved continuation of 5.7. This completes the bounded saved-input reader, **not the whole matching engine**. No download, observation-cell assignment, scientific-support promotion, real pairs, metrics, API or frontend was added.

## Implemented boundary

`backend/app/comparison/static_reader.py` reads the previously acquired static snapshot without network access or writes. `backend/app/schemas/static_support.py` defines strict, versioned manifest and snapshot contracts. `scripts.inspect_static_support` is an explicit local operator command; health, startup and HTTP handlers do not invoke it.

The reader checks contained private paths, the manifest digest-derived support ID, model ID/version/mode and the stored model-manifest identity. It hashes the bounded source objects and subset, verifies original/final catalogue metadata equality, then decodes the retained original chunks to reconstruct every selected array. Source axes must exactly match the prepared model; selected native indices, byte counts and structural checks must match the manifest. Missing or extra listed chunks are rejected, not interpreted as land/fill.

NetCDF variable names, dimensions, dtypes, attributes, fill definitions and values must match the reconstructed source arrays. Recomputing a changed subset's hash does not bypass these checks. Model fields, manifest, subset and source identities are checked again before returning. These are local consistency checks, not publisher authentication, an atomic filesystem snapshot or protection against an attacker replacing all mutually consistent inputs.

The returned snapshot preserves all 50 original negative elevation levels, source-order binary mask values, bottom arrays and explicit model-depth-to-source-level indices. Bottom fill/nonfinite values map to null in the typed view; source files remain unchanged, and missing wet-column bottom data is rejected. Numeric bottom-level agreement is not a verified indexing definition. Observation wetness, connectivity, time interval mapping, datum compatibility and reviewed tolerances remain pending. The existing matching audit is intentionally not wired to this reader yet.

Limits: 64 KiB manifest, 1 MiB per metadata object, 4 MiB subset, 128 source objects, 64 MiB retained transfer count, 128 MiB cumulative decoded chunks and 4 MiB per decoded chunk. At most 25 centres per horizontal axis and 50 static levels are accepted. Chunk decoding is bounded; these limits do not establish an OS memory sandbox or a wall-clock deadline for local disk access. Existing dependencies are reused.

## Operator command and real-data check

From the Desktop build root:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.inspect_static_support
```

Optional `--support-id` and `--model-id` select another compatible local pair. Default support is `b_b18353b728b66639c7787d55`; model is `m_35e4c0ab33c1469a334ca837`. Exit 0 means **local static inputs verified**, not comparison-ready. Exit 2 is a sanitized verification failure. Output is a compact summary, not raw arrays/private paths.

The real local command passed: 59 source objects, 8,450 mask values (50 × 13 × 13), 169 wet and 0 dry surface centres. The eight prepared model depths map exactly to original static indices `[49, 48, 47, 46, 45, 44, 43, 42]`. Status remains `static_inputs_verified_not_matching_ready`, `comparison_ready=false`.

- Manifest SHA256: `b18353b728b66639c7787d55bf9706bbb270b787df22966b9dfcec7b44c65afd`.
- Subset SHA256: `ed0efdff6e48ef2fa7cae6824b900df3a71d40b3b480ed4b694f0d348b67af23` (unchanged from acquisition).
- No provider access, new raw dataset, credentials or BIO-ROMS whole-file reread was needed.

## Verification

The new targeted suite passed **26 tests, 25 NumPy/NetCDF shape deprecation warnings**. Synthetic fixtures use the actual model preparer and static publisher with a fake local transport. Tests cover read-only behavior, exact depth mapping, safe IDs/CLI errors, corrupted objects, rehashed subset values/attributes, model/mode/source/index/count mismatches, missing/extra read-set entries, changed final metadata and post-read file changes. A first fixture-setup attempt hit a Windows permission error during publication; rerunning the unchanged fixture passed. No retry or weaker publication rule was added to production code.

Ruff lint/format passed for 102 Python files; `pip check` found no broken requirements. All 29 maintained Markdown files passed local-link, fence and final-newline checks. The existing real salinity audit was rerun: exit 3, no stderr, all nine original scientific blockers, zero pairs and overlap not evaluated. No policy threshold or evidence flag changed.

Full regression passed **848 tests, 4 Windows symlink-permission skips and 1,554 warnings in 302.72 seconds**. This includes all 26 new reader tests and the expanded 38-test acquisition group; the counts overlap and must not be added. Warnings remain visible: NumPy/NetCDF/xarray/Starlette deprecations and the intentionally invalid-range fixture. The earlier fixture publication permission error did not recur in this complete run. No failing test remains in the final run.

Verification commands: `python -m pytest -c backend/pyproject.toml -q --tb=short`, Ruff check/format with `backend/pyproject.toml`, and `python -m pip check`, all through `ocean-env/Scripts/python.exe`. These are backend/offline and scoped local-data checks, not browser-performance or production-readiness evidence.

## Next approval: 5.7-B

Later update: the [5.7-B candidate-bound diagnostic checkpoint](MILESTONE_5_7_SPATIAL_SUPPORT.md) is now implemented. Its scientific decision register remains unresolved; the earlier next-step proposal below does not authorize real integration or another acquisition.

Define and verify observation-cell, full-depth mask/bottom and coastline-connectivity policy, with explicit evidence and negative tests. Resolve or retain blocked time-label mapping, vertical-reference compatibility and justified reviewed tolerances; do not guess them to produce pairs. Then separately approve 5.7-C real integration. Parts 5.8–5.10 and frontend remain later.
