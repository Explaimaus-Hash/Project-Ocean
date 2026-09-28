# Part 5.5 — quantity compatibility

Approved separately on 2026-09-10. Implemented a bounded, read-only quantity stage, not matching or frontend. Original acquisitions, observation collections and native models are not rewritten. No dependencies, credentials, provider requests or HTTP routes were added.

## Scientific policy and evidence

- Core Argo A/D modes select adjusted PRES/TEMP/PSAL with flags 1/2; R, missing adjusted values, failed coordinate/parameter QC and unresolved metadata are rejected. There is no raw fallback. This preserves the existing prototype flags-1/2 policy, not a claim that every such value is suitable for publication. More restrictive uncertainty/quality requirements belong to the separately approved matching policy. [Argo guidance](https://argo.ucsd.edu/data/how-to-use-argo-files/).
- Provider adjusted metadata and client adjusted metadata remain separate. Apply their decoded valid-range intersection conservatively; missing/conflicting ranges block that quantity. Do not recover values removed upstream or invent a wider collection. Adjusted pressure outside the original request window is excluded.
- The inspected provider TEMP is in-situ ITS-90 Celsius, PSAL is Practical Salinity and PRES is sea pressure with zero at sea level. Provider TEMP bounds are −2.5–40 versus client −2–40; provider PSAL bounds 2–41 versus client 0–43. The originals are retained, not corrected in place.
- Model `so` has `unit_long=Practical Salinity Unit`, `units=1e-3`, and `standard_name=sea_water_salinity`. Its Practical Salinity mapping preserves the numeric PSAL value: do not divide it by 1,000 or replace it with Absolute Salinity.
- GSW 3.6.23 is loaded only on calculation. `SA_from_SP` produces the Absolute Salinity intermediate (g/kg), then `pt0_from_t` produces ITS-90 potential temperature at zero dbar. Never pass Practical Salinity directly as Absolute Salinity. [Salinity definition](https://www.teos-10.org/pubs/gsw/html/gsw_SA_from_SP.html), [temperature definition](https://www.teos-10.org/pubs/gsw/html/gsw_pt0_from_t.html).
- The generic calculation accepts only explicit verified definitions. Its conservative numeric domain is SP 0–42, temperature −2.5–40 °C, pressure 0–12,000 dbar, valid geographic coordinates and finite numbers. Negative SP is rejected before GSW can clip it. These bounds and finite GSW output do not establish a wet mask or oceanographic validity everywhere.
- **Real model temperature remains blocked:** its scale and zero-dbar reference are not independently verified. Observation potential temperature can be reported as a derived diagnostic without claiming compatibility with `thetao`. No silent ITS-68/ITS-90 conversion or assumption repairs the model manifest.
- Original adjusted errors, modes, QC and selected source names remain in the report. Converted total uncertainty is unknown, not zero. No error threshold, error propagation, temporal tolerance or accepted pair is invented.

## Operator usage

From the confirmed Desktop build root:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.audit_quantities --collection-id o_c645f248f801845378f0fdaf --acquisition-id a_d30181bd8998aca81bb33be1 --model-id m_35e4c0ab33c1469a334ca837
```

The command prints bounded JSON only. It checks the immutable collection, acquisition identities and provider/client file hashes, validates the native-model manifest, and verifies exact selected provider row values/errors/modes/QC/time/position before deriving quantities. It rechecks collection/client/provider/model-manifest hash/stat identities afterward. Model fields are not opened or matched. This is trusted local metadata verification, not provider-signed authenticity.

The provider reader deliberately supports only the inspected core ERDDAP row representation: at most 100 variables, 100,000 elements per variable, numeric/fixed-byte types, contiguous NetCDF3/NetCDF4 storage without packing, and locally bounded files. Unsupported transforms/layouts fail safely. Other Argo layouts and glider quantities are not silently assigned these definitions.

The pure `derive_quantities` library requires caller-verified typed evidence; it cannot establish file authenticity or row alignment by itself. Prefer the audited operator adapter for actual local data. Reports carry real/synthetic mode and a canonical serialized collection hash, explicitly distinct from its on-disk JSON hash. Maximum report is 16 MiB and 5,000 samples; it is private operator output, not a browser payload contract.

## Verified real result

All 14 saved Argo points passed provider row verification, adjusted quantity selection and observation-side conversion. All 14 passed the salinity **quantity** gate, but none is a matched pair: only five were horizontal candidates in the earlier audit. All 14 retained model-temperature incompatibility reasons. `comparison_ready` remains false everywhere.

First source row: adjusted pressure 2.7300000190734863 dbar; adjusted Practical Salinity 35.16699981689453; Absolute Salinity 35.333284310735294 g/kg; diagnostic potential temperature 28.670344148520858 °C at zero dbar. The old collection still selects raw pressure 2.799999952316284 dbar. Its adjusted pressure error 2.4000000953674316 dbar is preserved, not interpreted as complete converted uncertainty.

Real CLI report: 26,523 UTF-8 bytes at verification. Provider SHA256 remains `42cbf31dc51e28afb1c3e349723b53b5cf67ac9581145eb89ff83516e61b75cb`; client SHA256 remains `6a6de3db0d8b150783c25b39f99797944eed986eab915b1a6677bc1d9d2e96be`. Successful pre/post checks verified unchanged source files. No new persistent scientific collection or derived model was published.

## Tests and remaining gates

Targeted quantity/provider tests: **39 passed**, with existing NumPy/xarray deprecation warnings. Full regression: **551 passed, 4 Windows symlink-privilege skips, 1,240 warnings in 301.14 seconds**. Ruff checks and formatting pass for 75 Python files; `pip check` reports no broken requirements. All 21 root/docs Markdown files passed local-link, fence and final-newline checks. The stricter bundled potential-temperature assertion was also rerun separately and passed. Warnings remain the known NumPy/xarray/NetCDF shape/timedelta, Starlette HTTPX/AnyIO and deliberately invalid range-fixture warnings; they are not a clean-warning or production-readiness claim.

The first strict salinity check found differences up to about 7.45×10⁻⁵ g/kg from the website's explicitly identified GSW 3.05 (2015) examples. Those examples now test cross-version agreement at an explicit 10⁻⁴ tolerance, not bitwise equivalence. The installed GSW package's independent reference-cast data match at 10⁻¹⁰ absolute tolerance; the official zero-dbar temperature example is separately checked with its published Absolute Salinity input. No production formula was changed to force an old example to match.

Next, only after permission: **5.6 matching policy** — daily averaging support, horizontal/depth/time tolerances, wet/bottom masks, uncertainty and exclusion/no-overlap rules. Model temperature scale/reference can remain a blocking gate. 5.7 matching engine, metrics, API and frontend are not implemented by this checkpoint.
