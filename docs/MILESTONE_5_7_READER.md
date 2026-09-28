# Part 5.7 continuation — verified local input reader

Status: the approved continuation adds a bounded, read-only prepared-model reader and local matching-input audit. The earlier [synthetic kernel checkpoint](MILESTONE_5_7.md) remains historical evidence. This continuation verifies inputs and adjusted-depth alignment; it does **not** enable real matching, complete 5.7, or start metrics/API/frontend work.

## Implemented scope

- `schemas/model_reading.py` and `comparison/model_reader.py` verify the selected prepared native `so` or `thetao` field against its model manifest, typed source metadata, file hashes/stat identities, header, axes, units and dimensions. Reads are native-resolution, one bounded time/depth slab at a time; no display preview is used. Prepared-output attribute allowlists reject unexpected bounds, coordinate mappings or formula terms even if a changed file has a freshly computed hash.
- `schemas/matching_local.py` and `comparison/local.py` bind that reader to existing provider/client/collection verification and the adjusted-pressure depth bridge. Only `adjusted_depth_alignment` is promoted after verified sample/provenance alignment and a separately hashed depth report; this does not establish a common model vertical datum or accept every pressure endpoint.
- `scripts/audit_matching_inputs.py` prints a bounded private operator report. Its status is `inputs_verified_matching_blocked`, with zero pairs, overlap `not_evaluated` and `comparison_ready=false`. It does not call the matching kernel or persist a report.

The reader preserves actual model labels, native axes and per-variable missing values. A finite-value mask is **variable validity, not a wet-domain, coastline or bottom certificate**. No interval, bathymetry, connectivity or vertical-reference evidence is inferred from finite values or a shallow depth subset. Existing null/unreviewed tolerances and the strict D-mode/QC1 policy remain unchanged.

## Operator command and limits

Run from `C:/Users/pc/OneDrive/Desktop/ocean_2`:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.audit_matching_inputs
```

`--policy` optionally selects a contained policy file; the default is `config/comparison.yaml`. Exit **3** means input verification completed but matching remains blocked, never successful pairs. Exit **2** means verification could not be completed. The original `scripts.check_matching_policy` remains unchanged and does not read native model fields or promote adjusted-depth alignment.

The reader caps one selected field at 250,000 native values before reading field slabs, and validates prepared-file/chunk/cache limits. The local audit retains the existing 5,000-observation and 12-time ceilings; policy input is at most 16 KiB and serialized audit output at most 1 MiB. Input files are checked before and after the read chain. These detect ordinary concurrent changes, not adversarial immutable snapshots or an OS memory sandbox. No network calls, downloads, credentials, source writes, new dependencies, HTTP routes or frontend work are introduced.

## Verification record

The reader was implemented on 2026-09-15 and final verification completed on 2026-09-16. The final full backend suite passed **784 tests, with 4 Windows symlink-permission skips and 1,523 warnings in 261.70 seconds**. This includes the metadata-allowlist and wrong-returned-variable regressions. Earlier 737-test and targeted 67-test runs are superseded by this full run, not additional tests to add to its count.

Ruff lint and formatting pass for 95 Python files; `pip check` reports no broken requirements. All 25 root/docs Markdown files pass local-link, fence and final-newline checks. Known warnings remain NumPy/xarray/NetCDF deprecations, Starlette HTTPX/AnyIO deprecations and an intentionally invalid range fixture. The isolated targeted run also logged provider-plugin discovery warnings when its fixture intentionally denied networking; no live provider access was performed. No failing check remains in these runs, but neither browser performance nor deployment readiness is established.

Independent review identified and fixed two gaps: unknown scientific attributes could survive header checking, and a mismatched returned field could be relabelled with the requested variable. The reader now accepts only its prepared-output attribute contract; the coordinator revalidates the snapshot and explicitly checks the returned source variable. The regression fixtures cover both axes/fields and a valid but wrong-variable snapshot.

### Actual local checks on 2026-09-16

Both quantities were audited without changing the policy YAML or any dataset. Each selected native field contains **2,704 finite values**, at the original two time labels/eight depths/13×13 horizontal cells. Each audit derives 14 adjusted central depths, with 12 evaluated pressure-error ranges and two retained out-of-domain ranges. No midpoint shift, source-depth replacement or surface clamping was introduced.

| Audit | Jointly QC/quantity eligible | Remaining blockers | Matched pairs | Serialized report |
| --- | --- | --- | --- | --- |
| Practical Salinity (`so`) | 14 | 9 | 0 | 17,326 bytes |
| Zero-dbar ITS-90 potential temperature (`thetao`) | 0 | 11 | 0 | 17,464 bytes |

Only adjusted-depth alignment is now verified; the other support requirements stay unresolved. A finite temperature field does not resolve its temperature scale/reference compatibility. CLI execution returned **exit3**, valid `inputs_verified_matching_blocked` JSON and no stderr. Reports were inspected in memory, not saved as comparison products.

All seven inputs passed before/after SHA256 and size/mtime checks in the coordinator: observation collection, client input, preserved provider input, Argo acquisition manifest, model manifest, scientific fields and source metadata. The field reader independently checks all three prepared model files. The large original BIO-ROMS file was not reread, replaced or deleted. The source checks detect ordinary concurrent changes, not hostile races or publisher authentication.

## Remaining 5.7 work — request permission

Subsequent approved evidence research is recorded in [MILESTONE_5_7_SUPPORT_EVIDENCE.md](MILESTONE_5_7_SUPPORT_EVIDENCE.md). It identifies the static bathymetry source and a bounded acquisition proposal but leaves the scientific gates unresolved. The test counts above remain this reader checkpoint's historical evidence.

Reviewed horizontal/depth/time tolerances, precise daily interval evidence, independent wet/bottom/coastline support and compatible vertical-reference evidence remain unresolved. Model potential-temperature scale/reference remain separately blocked. The kernel still rejects real mode with `real_field_and_support_adapter_not_implemented`; the local reader is only one part of that integration. Do not pass its snapshot to the kernel or invent verified support to obtain pairs.

Continue evidence/support integration only after permission, with any additional source acquisition separately authorized. Then request approval before 5.8 metrics, 5.9 comparison API, 5.10 end-to-end verification and the final frontend. Preserve the [canonical policy](MATCHING_POLICY.md), original inputs and all four source families.
