# Part 5.1 — scientific compatibility audit

Date: 2026-09-10. Build: `C:/Users/pc/OneDrive/Desktop/ocean_2`. The user approved only this approximately 20-minute audit checkpoint. Parts 5.2–5.10 and frontend need separate permission. This document records inspected evidence and unresolved decisions; it is not an executable comparison policy.

## Outcome

The audit is complete, but **no model-observation pair is certified comparison-ready**. Five of the fourteen saved Argo points fall inside the acquired Copernicus horizontal envelope; nine do not. Date overlap exists, but adjusted-data selection, pressure/depth conversion, model time support, temperature definitions, wet-domain evidence and preparation remain unresolved. No conversions, matching engine, tolerances, residuals, metrics, new acquisition or HTTP routes were implemented. Existing inputs and scientific products were not changed.

Part 5.2 can design the model preparation contract after permission. It must retain these unknowns and keep comparison disabled; preparing a model file does not itself resolve scientific compatibility.

## Inputs actually inspected

| Input | Identity | Bytes | SHA256 checked in this audit |
| --- | --- | --- | --- |
| Copernicus client-produced model subset | `a_9e918d43555ffc26d3659e08/input.nc` | 54,832 | `c92568212fc4b2b46f31162106bc7aced404e1c32d9675267d1d399c5abfb3a3` |
| Argo expert-client output | `a_d30181bd8998aca81bb33be1/input.nc` | 62,646 | `6a6de3db0d8b150783c25b39f99797944eed986eab915b1a6677bc1d9d2e96be` |
| Original saved ERDDAP response | Same Argo acquisition, `provider_input.nc` | 18,108 | `42cbf31dc51e28afb1c3e349723b53b5cf67ac9581145eb89ff83516e61b75cb` |
| Prepared Argo point collection | `o_c645f248f801845378f0fdaf/collection.json` | 21,802 | `e77f2e92760b95ac820cab36839fcdc84d6df363dc25d837d05ba1eb06c9f078` |

Acquisition inputs live below `data/raw/acquisitions/`; the observation collection lives below `data/observations/`. Both acquisition manifests and the observation collection were schema-validated. The data hashes above agree with their saved manifest records. These four files and their three manifests retained identical SHA256, size and modification time before/after the local audit. Hash integrity is not independent scientific validation.

The Copernicus source is `GLOBAL_MULTIYEAR_PHY_001_030`, daily dataset `cmems_mod_glo_phy_my_0.083deg_P1D-m`, version `202311`. Its acquisition status remains `acquired_not_prepared`. No credentials or provider login were needed to inspect these local files.

## Actual horizontal and time envelopes

The model has `(time=2, depth=8, latitude=13, longitude=13)`. All four axes are finite and strictly increasing. Longitude centres span 65–66E; latitude centres span −1–0N. Actual UTC timestamps are January 29 and 30, 2019 at 00:00, stored as `hours since 1950-01-01` with Gregorian calendar.

| Observed point group, not a certified profile | Saved source position/time | Points | Horizontal envelope result |
| --- | --- | --- | --- |
| Float `1901804`, cycle 118, ascending | 65.439E, −0.994N; `2019-01-29T19:31:09Z` | 5, source indices 0–4 | Inside model centre envelope |
| Float `2902577`, cycle 186, ascending | 66.284E, 2.946N; `2019-01-29T22:49:26Z` | 9, source indices 5–13 | Outside model centre envelope |

All fourteen station timestamps fall between the two stored model timestamps. This is only an envelope check, not a valid time match. The provider describes `time` as the station's Julian day in UTC, not a separately timed measurement for each depth. All profile IDs remain null/`ambiguous_points`; do not merge rows into an invented profile. Stable individual sample IDs can support later pointwise analysis without claiming profile uniqueness.

Keep the nine outside points as explicit exclusions for this model subset. Do not expand the model acquisition, extrapolate or find a distant wet cell automatically. The five inside points are only candidates for later checks, not five accepted pairs.

## Variable and vertical compatibility

| Pair or coordinate | Actual evidence | Audit decision |
| --- | --- | --- |
| `thetao` versus `TEMP` | Model: `sea_water_potential_temperature`, `degrees_C`; original Argo: in-situ ITS-90 temperature, `degree_Celsius` | Different quantities; direct subtraction prohibited. Model temperature-scale/reference policy still needs substantiation. |
| `so` versus `PSAL` | Model `unit_long="Practical Salinity Unit"`, units `1e-3`; provider Argo `sea_water_practical_salinity`, units `PSU` | Practical-salinity mapping is supported, but must be explicit and source-specific. Do not interpret this as Absolute Salinity or blindly rescale values by 1,000. |
| Model depth versus Argo pressure | Model metres, positive down; provider pressure in decibar, zero at sea level | Not interchangeable; latitude-aware conversion and a common vertical reference are prerequisites. |
| `uo`, `vo` versus current observation collection | Model eastward/northward velocity in `m s-1`; collection has only PRES/TEMP/PSAL | No observation-current counterpart; velocity residuals are unsupported for these inputs. |

The eight actual model depths are approximately 0.494025, 1.541375, 2.645669, 3.819495, 5.078224, 6.440614, 7.929560 and 9.572997 m. All four model fields contain 2,704 finite decoded values and no masked cells in this small acquired selection. Source int16 packing/fill/valid-range metadata remains present. Finite cells alone do not prove bathymetry or coastline connectivity: this file has no independent wet-mask/bathymetry variable and ends above the full model bottom.

The five horizontally overlapping Argo points have raw pressures approximately `[2.8, 4, 6, 8, 10]` dbar and adjusted pressures `[2.73, 3.93, 5.93, 7.93, 9.93]` dbar. Every saved `depth_m` is null. A request ceiling of 10 m does not mean a 10 m model centre exists; the deepest observation cannot be declared vertically supported by comparing pressure numerically with depth. No pressure conversion was performed, and GSW is not installed in this environment.

The [Argo parameter vocabulary](https://vocab.nerc.ac.uk/collection/R03/current/TEMP/) confirms the in-situ ITS-90 definition; [PRES](https://vocab.nerc.ac.uk/collection/R03/current/PRES/) is sea pressure and [PSAL](https://vocab.nerc.ac.uk/collection/R03/current/PSAL/) is practical salinity. Future conversion may use [SA_from_SP](https://www.teos-10.org/pubs/gsw/html/gsw_SA_from_SP.html) with Practical Salinity, sea pressure and position, followed by [pt0_from_t](https://www.teos-10.org/pubs/gsw/html/gsw_pt0_from_t.html) only for an appropriately verified zero-sea-pressure target. Absolute Salinity is an intermediate here, not a relabeling of model `so`. [z_from_p](https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html) returns upward-positive height; depth uses the opposite sign, with latitude and any vertical-reference assumptions recorded.

The [CF standard-name definition](https://cfconventions.org/Data/cf-standard-names/34/build/cf-standard-name-table.html) supports a sea-level reference for potential temperature. That is standards-level evidence, not an independently verified numeric reference attribute or ITS-90/IPTS-68 declaration for this particular model product. The inspected file/PUM did not establish the model temperature scale. Keep this evidence distinction; do not use the PUM's mixed-layer-depth reference-pressure statement as proof about `thetao`.

## QC and raw/adjusted selection

All fourteen points have time QC1, position QC1, and raw/adjusted PRES/TEMP/PSAL QC1; all three parameters are in delayed mode `D`. The current collection deliberately selects **raw**, while retaining adjusted values and errors. Its existing `qc_eligible` flag means eligibility under the Part-4 flag policy, not suitability for scientific comparison.

The [official Argo usage guide](https://argo.ucsd.edu/data/how-to-use-argo-files/) directs D/A core observations to their adjusted values and adjusted QC/error; its strongest-quality recommendation adds QC1 and suitably small errors. Future comparison must establish an explicit adjusted selection for these D-mode points, preserving the current raw collection unchanged. No automatic fallback or in-place change was made here. QC2 means probably good, not identical to QC1; the eventual acceptance/error policy belongs to the later approved checkpoints.

For the five inside points, adjusted minus raw pressure is approximately −0.07 dbar and salinity differs by approximately −0.012 to −0.013 practical-salinity units; temperature is unchanged. Recorded adjusted errors are approximately 2.4 dbar, 0.002 °C and 0.01 salinity units. These are source uncertainty fields, not matching tolerances; no new cutoff was selected. The pressure error is material to shallow-layer interpretation and must not be discarded.

## Metadata discrepancies that must remain visible

1. **Daily time support:** the [Copernicus PUM issue 1.7, November 2025, p.9](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf) describes midnight-to-midnight daily means centred at noon. The acquired file stores midnight labels and only `cell_methods="area: mean"`, with no time-bounds variable. The exact label-to-averaging-window mapping is unresolved. Do not shift timestamps by 12 hours, treat daily means as instantaneous samples or invent interval bounds. Preserve source labels and require version-specific evidence/policy before time matching.
2. **Inherited model globals:** local `field_date=2021-06-30`, `bulletin_date=2021-07-07`, `z_max≈5727.917` and a forecast-style title do not describe the actual 2019/shallow selection. `source=MERCATOR GLORYS12V1` remains present. Derive actual coverage from axes; retain the contradictory/inherited globals separately as provenance. Do not replace the registry identity or rewrite original attributes to hide the discrepancy.
3. **Provider versus Argopy metadata:** original provider TEMP bounds are −2.5–40 °C, while the client/collection uses −2–40; original PSAL bounds are 2–41 with `sea_water_practical_salinity`, while the client/collection uses 0–43 and `sea_water_salinity`. Part-4 provenance already records that Argopy replaces attributes. All current values lie within both sets of bounds, so no current invalid sample was discovered from this difference. However, client metadata must not be represented as unchanged provider authority. A future contract/policy must retain both layers and resolve validation precedence explicitly; no provider/collection metadata was edited in this audit.

## Comparison gates and next owners

These are audit findings, not implemented API error codes or executable defaults.

| Gate | Present finding | Later checkpoint |
| --- | --- | --- |
| Prepared model contract/product | Copernicus acquired only | 5.2–5.3 |
| Provider/client metadata authority | Both retained, differences identified | Carry in 5.2 contract; resolve before 5.5/5.7 |
| Vertical conversion/reference/support | No GSW or converted depths; full-bottom evidence absent | 5.4 and 5.6 |
| Adjusted D-mode selection and quantity definitions | Raw collection not approved for comparison; model temperature scale unresolved | 5.5 |
| Daily averaging/label semantics | Midnight/noon discrepancy unresolved | Evidence prerequisite for 5.6 |
| Spatial/depth/time tolerances, masks and uncertainty handling | Not selected; five horizontal candidates only | 5.6 |
| Matching, residuals, bias/RMSE and API | Not implemented | 5.7–5.9 |
| End-to-end acceptance/performance | No comparison benchmark exists | 5.10 |

GLORYS12 assimilates ocean temperature/salinity profiles, including Argo through CORA, according to the [product authors' system description](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2021.698876/full). Inclusion of these exact float/cycle observations was not established. Any eventual agreement statistics are descriptive, not proof of independent model validation; five candidates from one station/cycle are not a representative validation sample.

INCOIS and gliders are not being replaced: the existing BIO-ROMS product is surface-only with unresolved averaging/quantity definitions for comparison; GODAS has no verified local 2019-compatible product; Bella is outside this region/date window and has its previously documented TIME/QC problems. Those prior findings were not retested against live providers in this checkpoint. No all-four-source common match is claimed.

## Verification and scope boundary

Read-only local NetCDF/JSON inspection, schema/hash checks and the two envelope counts were run with network connection guards; all seven audited data/manifest files remained unchanged. Official-document retrieval was separate and used no source credentials. A supplementary full CF-table XML request was cancelled when it did not finish promptly; no conclusion relies on that incomplete fetch.

Existing health/startup checks were rerun: **8 passed, 2 existing warnings**, 2.43 seconds. No application code, configuration, dependencies or data products were changed. The full 386-pass/4-skip suite remains the historical Part-4 result, not a newly executed Part-5 comparison suite. Handoff checks passed for all 15 Markdown files' local links, fences and final newlines; all 68 snapshotted application/configuration files retained their hashes. No new scientific-result API, server, background task, Git operation or frontend was created.

Next: request permission for **5.2 — model preparation contract** only. Each later checkpoint has its own approximately 20-minute timebox and approval; unresolved scientific gates stay explicit rather than being guessed to fit the clock.
