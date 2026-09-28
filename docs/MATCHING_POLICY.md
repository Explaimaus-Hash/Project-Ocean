# Matching policy v1 — canonical contract

2026-09-27: this is still the **strict** policy and its configuration is unchanged. The user separately authorized [exploratory shallow salinity matching](MILESTONE_5_7_EXPLORATORY.md), which has a distinct immutable assumption contract/report and explicit operator opt-in. It does not satisfy or weaken the evidence requirements here. Real exploratory pairs must never be passed off as verified-policy pairs. Earlier synthetic-only implementation status below predates the exploratory branch.

Part 5.6 implements policy validation/preflight; approved Part 5.7 adds a synthetic-only native matching kernel, adjusted-depth bridge and verified local native-field/input audit. Native scientific-field reading is implemented; scientific-support verification and real-kernel integration remain unfinished, and the kernel explicitly blocks real mode. This contract does not establish that any real pair exists. [Historical kernel checkpoint](MILESTONE_5_7.md), [reader scope and verification](MILESTONE_5_7_READER.md). Preserve INCOIS, Copernicus, Argo and gliders; the first narrow policy supports the prepared Copernicus daily native grid plus core Argo observations. Do not assign these definitions to GODAS, BIO-ROMS surface products or gliders without source-specific verification.

## Explicit configuration, not guessed tolerances

The subsequent [5.7-C local coordinator](MILESTONE_5_7_EXECUTION.md) now assembles verified fields/observations/adjusted quantities/depths and calls the engine with physical support unresolved. The engine retains its real-mode guard and returns blocked before pair search. Two null candidate indices represent no horizontal candidate; no dummy cell or support assertion is introduced. The separate spatial diagnostics do not promote evidence. Existing policy rules, tolerances and legacy real-guard code are unchanged.

The later [5.7-B spatial diagnostic](MILESTONE_5_7_SPATIAL_SUPPORT.md) now implements nearest-centre-before-mask selection, bracketing native-node inspection and candidate-specific full-mask wet-depth reporting. It preserves unknown observation wetness/bottom/connectivity as null and never becomes engine support by itself. A diagnostic all-wet stencil is not a verified coastline rule; scientific review and reference/time evidence remain prerequisites. Existing policy values and blocker flags are unchanged.

The [5.7-A offline static reader](MILESTONE_5_7_STATIC_READER.md) now verifies the saved model-bound mask/bathymetry arrays and their retained source chunks. This establishes local structural consistency only. It does not alter this policy, call the kernel or resolve observation-cell wetness, bottom reference, connectivity or daily time support. The matching audit retains its existing blockers. Next approval is 5.7-B scientific-support policy/evidence, then 5.7-C integration.

`config/comparison.yaml` binds the policy to the exact model, collection, acquisition, real/synthetic mode and quantity. Its canonical serialized schema generates a full SHA256 `mp_` identity. Changing a threshold, source, quantity or policy rule changes that identity. Inputs and policy belong in future result provenance/cache identity.

Horizontal metres, vertical metres and temporal seconds are **required reviewed settings, with a rationale for this selection**. The current values are null and unreviewed, so matching remains blocked. No inspected official source establishes universal collocation tolerances. Neither an 8–9 km grid spacing nor a 2.4 dbar pressure error automatically supplies a matching tolerance. Do not increase limits until pairs appear.

Schema ceilings of 100,000 m horizontal, 1,000 m vertical and 86,400 s temporal are engineering resource/scope ceilings, not recommended scientific thresholds. Zero is a valid explicitly reviewed exact-coincidence requirement, distinct from missing. Values must be finite/nonnegative. Tighten and justify actual limits using the selected grid, time support, observation errors and intended interpretation before enabling an engine on real data.

## QC and errors

The new matching policy is deliberately stricter than Part 5.5 diagnostics: use adjusted D-mode core parameters with QC1, plus time and position QC1. A-mode, QC2 and raw fallback are not accepted by this policy. Existing collections/APIs and the A/D flags-1/2 quantity report remain unchanged. For salinity, require eligible PRES and PSAL; potential-temperature conversion also requires TEMP. Verify sample ID/index and exact original parameter provenance rather than reusing raw-selected eligibility.

Require supplied adjusted errors for the selected parameters; missing is not zero. Reject adjusted pressure error **greater than 20 dbar**, adopting Argo's high-accuracy, pressure-bias-sensitive recommendation. Equality alone passes that numeric screen, but QC and every other gate still apply. This is neither a depth-matching tolerance nor proof of scientific suitability. No universal TEMP/PSAL error cutoff is invented. [Argo Data FAQ](https://argo.ucsd.edu/data/data-faq/), [Argo usage guidance](https://argo.ucsd.edu/data/how-to-use-argo-files/).

Retain original error components without converting them into complete uncertainty, confidence intervals or error weights. Unknown model and representativeness uncertainty stay unknown. Do not label future model agreement as independent validation: the reanalysis assimilates in-situ observations. [Product description and assimilation context](https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description).

## Time semantics

Human-support update, assessed 2026-09-26: Gabrielle describes the daily data as interval-centred but does not provide the exact endpoints for the saved midnight-labelled sample. This cannot yet reconcile the saved labels with the PUM's noon-centred UTC-day wording. The follow-up explicitly distinguishes previous-noon-to-current-noon from same-date-midnight-to-next-midnight; neither interval is applied as an assumption. [Reply assessment and provenance](MILESTONE_5_7_EXECUTION.md#human-reply-assessment--2026-09-26).

The [2026-09-16 support-evidence check](MILESTONE_5_7_SUPPORT_EVIDENCE.md) reconfirmed the missing exact interval mapping in official version202311 metadata. It identified the matching static bathymetry candidate but acquired no support arrays. No scientific gate is promoted by that research. "Native" throughout this policy means original-resolution distributed-product samples, not the producer's original computational mesh.

The current PUM describes daily means across a full UTC day, centred at noon. The preserved version202311 subset instead labels samples at midnight and has no time-bounds variable. The PUM does not independently resolve that exact label-to-interval mapping. Keep original labels and block temporal matching until interval evidence for this precise input is verified. Generic CF coordinates need not be cell centres when bounds are absent. [PUM, issue 1.7, §2(c)](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf), [CF coordinate and cell bounds](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.4/build/cf-conventions.html).

Represent verified cells with native time index, original label and separate UTC `start`/`end`. For this daily-only policy, intervals are exactly one day, ordered and non-overlapping; every selected native time must be covered. Never rewrite labels or attach inferred intervals while evidence is unresolved.

The synthetic kernel's time selection uses **[start, end)** membership: a midnight boundary belongs to the following interval, not both. The observation must also satisfy the reviewed absolute offset limit measured from the verified interval midpoint, not from an assumed meaning of the stored label. Missing interval coverage means no temporal support; no nearest-day fallback or time shift. Report both original model label and verified averaging bounds, with instantaneous-observation versus daily-cell-mean representativeness explicit.

## Nearest-native selection and masks

The following rules are implemented for bounded synthetic snapshots in 5.7; the local native-field reader now exists, but real use additionally requires unfinished scientific-support verification and kernel integration:

1. Validate bound snapshot identities/modes/quantity, recompute the canonical observation hash and adjusted-depth alignment, and apply the documented QC/error gates. The local reader authenticates prepared scientific fields against their bounded manifests/metadata and pre/post file identities. Future support integration must verify its supporting files and bind all evidence to that same input snapshot; a supplied digest is not proof of those files. Use native scientific data, never display previews.
2. Require the observation inside the inclusive prepared horizontal centre envelope. Do not extrapolate half a cell beyond it or silently wrap a dateline selection. Find the geographically nearest native horizontal centre; ties use the lowest native latitude index, then longitude index.
3. Select the verified containing daily interval and check midpoint offset. If none exists, retain the temporal exclusion. Do not replace it with another nearby day.
4. Within that same native column/time, select the level closest to the observation's adjusted-pressure-derived central depth. Break equal offsets using the lowest native depth source index. Native source indices, not array iteration order or rounded display coordinates, define ties.
5. Check inclusive reviewed horizontal and vertical distance limits. Require verified wet status at the observation and selected cell, coastline/water connectivity, per-variable/time/depth masks, local vertical centre support and bottom support. Reject missing/nonfinite/dry/unsupported nearest cells. **Never search farther away to find a wet or finite replacement.**
6. Require central observation depth AND both pressure-error-derived depth endpoints inside the verified local vertical support. Do not clamp endpoints at the surface/bottom or expand tolerance by uncertainty. Endpoints are pressure-error sensitivity, not a confidence interval. Reject missing/out-of-domain endpoint calculations and unverified vertical datum compatibility.

The implemented spatial metric is explicitly reported great-circle distance (mean-sphere radius 6,371,008.8 m, a project computational convention), not degrees used as metres. A future alternative geodesic metric requires a new processing-policy version and tests. Choice of nearest native sample does not imply interpolation or a conservative remap.

Finite model values alone do not prove coastline connectivity or full local bottom support. The [regional static mask/bathymetry acquisition](MILESTONE_5_7_STATIC_ACQUISITION.md) is now downloaded and grid-checked, but verified matching-support integration remains unfinished. A shallow prepared science-depth subset is not the full model water column, even when the separate static mask contains all50 levels. GSW's zero-dynamic-height/geopotential diagnostic does not automatically share a model/geoid/ellipsoid datum. [GSW pressure-to-height definition](https://www.teos-10.org/pubs/gsw/html/gsw_z_from_p.html).

## Provenance and fail-closed behavior

Human support confirmed that thetao is potential temperature in the EOS-80 framework. Record that narrow provider statement separately from the still-unconfirmed delivered temperature scale/reference pressure; it does not by itself prove compatibility with the implemented ITS-90/GSW target. No conversion, capability flag or prepared metadata was changed from this email. Also, unresolved deptho_lev indexing is not itself an additional blocker for the current full-mask reader: preserve that variable uninterpreted and continue deriving wet-level diagnostics from the actual mask. This does not resolve vertical datum, observation support or connectivity.

The [2026-09-17 static acquisition](MILESTONE_5_7_STATIC_ACQUISITION.md) now provides a local grid-checked source subset, but the matching adapter has not consumed/verified its support semantics. Acquisition status,169 wet surface centres and numerical bottom-level agreement do not automatically resolve observation wetness, local bottom reference or candidate connectivity. The existing local audit intentionally retains all nine salinity blockers until a verified support adapter and remaining policy evidence exist.

Keep on-disk collection SHA256 and canonical collection SHA256 separately named; they can differ due to serialization. Match depth/quantity/collection by sample ID AND native sample index, and bind reports to exact model/collection/client/provider identities. A raw-pressure depth cannot be combined with an adjusted-pressure quantity report merely because the values are close. Model-temperature exclusions remain blocking even when a finite converted observation temperature exists.

Count strict-QC eligibility, quantity eligibility and their intersection separately. Positive marginal counts do not prove a shared eligible observation. These are preflight counts, never matched-pair counts.

Support evidence is an internal verified-input contract, not a public request body. A reference string alone is not verification. The implemented local input audit promotes only adjusted-depth alignment after verified source/sample identity and bridge checks; it never upgrades missing time/wet/bottom/connectivity/vertical-reference evidence from YAML or changes model capability flags. A finite-value mask is not wet-domain evidence. Future evidence readers must validate the specific grid/variable/time/depth snapshot they claim to support.

`blocked` is distinct from a future genuine no-overlap result. Preflight always returns `overlap_status=not_evaluated`, `matched_pair_count=0`, and `comparison_ready=false`, including when synthetic policy requirements pass. Future engine results must preserve separate reasons for metadata blocked, no horizontal/time/depth support, QC rejection, quantity incompatibility, missing values, mask/bottom rejection, uncertainty rejection and tolerance exceeded. Empty results must retain their reason/counts, never become zeros in metrics or a success-readiness claim.

## Synthetic engine boundary and budgets

`NativeMatchingInput` is an internal synthetic snapshot, not a browser request or proof of file authenticity. `match_native` validates identities and recomputes adjusted-depth/quantity alignment before nearest selection; `serialize_matches(request)` recomputes results, rather than accepting a caller's claimed pairs. Reports preserve policy/context/input and scientific-file digests, actual native indices, source labels/verified intervals, values, offsets, adjusted errors and per-sample exclusions. No residuals or metrics are computed; `comparison_ready` remains false.

The kernel caps 250,000 native field values and one million horizontal candidate checks (`horizontal_cells × observation_count`), with at most 5,000 observations, 12 model times, a 16 MiB serialized input and a 1 MiB output checked incrementally. These bounds do not establish an OS memory sandbox or browser performance. A failed limit requires a smaller explicit selection, not scientific decimation.

A global missing requirement returns `blocked` with overlap `not_evaluated` and no evaluated rows. Per-row unknown support produces `partially_blocked`; without accepted pairs its overlap also remains `not_evaluated`. Otherwise evaluated rows distinguish `matched` from `no_valid_pairs` with reasons retained. `no_valid_pairs` is not a universal claim of geographic no-overlap. Real mode is always blocked by `real_field_and_support_adapter_not_implemented`, even with caller-supplied verified-looking evidence. Leave actual tolerances unset until reviewed; the existing preflight cannot override missing source support.

## Limits and current operator behavior

At most 5,000 observations, 12 model times, a 16 KiB policy file and 1 MiB preflight report. This existing preflight command performs no API, startup, health, ingestion, pair search, metrics or frontend work. The source adapter remains bounded by the prior read-only quantity-audit limitations. A valid policy document does not authenticate inputs or establish model readiness.

```powershell
.\ocean-env\Scripts\python.exe -m scripts.check_matching_policy
```

Exit **3** means a valid preflight report with blocking requirements; **2** means invalid/unavailable input or failed verification; **0** means policy requirements satisfied only, never matched pairs. The present real salinity selection returns 3. The current local adapter intentionally has no support-evidence override, so entering numeric limits alone cannot enable real matching.
