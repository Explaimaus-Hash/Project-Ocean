# Part 5.7-C — guarded local execution checkpoint

Current continuation, 2026-09-27: the user explicitly approved assumptions cross-checked online. See [the separate exploratory milestone](MILESTONE_5_7_EXPLORATORY.md): real shallow salinity can now be explored with visible assumptions, yielding 2 pairs in the selected data. This checkpoint's strict command remains blocked and unchanged. Its earlier verified-only completion boundary below is historical for exploratory scope, but still applies to scientifically verified matching. No 5.8 started.

Implemented on 2026-09-17 after explicit approval to continue with 5.7-C. This completes **verified input assembly and blocked engine invocation**, not scientifically enabled real matching or all of 5.7. The unresolved 5.7-B decisions remain binding. No 5.8 metrics, comparison API or frontend was started.

## What is connected

`backend/app/comparison/execution.py` now runs the existing local model/Argo audit, reads the verified native field and static snapshot, obtains the original collection and adjusted quantity report, computes candidate-bound spatial diagnostics, and assembles `NativeMatchingInput`. It passes real native values and variable-validity masks without display decimation, plus original sample IDs and the verified adjusted-depth report, to `match_native`.

The existing engine independently checks observation/quantity/source identities, canonical collection hash, depth recalculation and eligibility counts. It then checks scientific policy and its retained real-mode guard **before pair selection**. Current real inputs therefore produce an explicitly blocked engine result with no evaluated pairs, not a no-overlap result.

Physical column wet/bottom/depth support and observation wet/connectivity remain unknown. Static node masks and geoid bathymetry stay in a separate diagnostic object; they are not converted into verified physical support. Original time labels remain unchanged and no daily intervals or numerical tolerances are invented. The temperature unit label in the engine contract is the requested target quantity, not proof that the source temperature has that definition; temperature gates remain blocked.

For outside-envelope observations the optional candidate-index pair is now `(null, null)` instead of fabricated zero indices. The support contract rejects half-missing index pairs or asserted support with no candidate. Inside candidates retain their actual model-source indices. This schema extension does not alter selection, masks, tie rules or valid synthetic matches.

Model manifest/scientific/metadata identities, exact axes, static model binding, collection canonical identity and mode are checked across stages. The native field, static snapshot and local input audit are reverified after engine invocation; changed inputs fail instead of returning output. Existing bounded-reader limits still apply. The typed combined `LocalMatchingExecution` output requires blocked status, no engine result rows, zero pairs and overlap not evaluated. Its serializer rechecks policy blockers, identities and the final 1 MiB output cap. Serialization is validation, not file authentication or a substitute for the coordinator.

No file writes, acquisition, provider login, support-evidence override or HTTP route is added. Ingestion and scientific processing remain absent from health/startup. No new dependency. No performance/atomic-filesystem-snapshot claim is made; repeated reads deliberately prioritize input consistency for this small operator workflow.

## Operator command

From the Desktop project root:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.run_local_matching
```

Defaults: `config/comparison.yaml` and `b_b18353b728b66639c7787d55`. Optional `--policy` and `--support-id` select compatible local inputs. Policy files are bounded to 16 KiB and checked before/after. Exit **3** is a valid blocked execution report; **2** is invalid input/failed verification. There is intentionally no real-success exit path in this checkpoint. Errors omit private paths and traces.

The output contains separate `engine` and `spatial` objects, source/static/audit fingerprints and `comparison_ready=false`. Spatial rows describe all collection positions; they are not accepted/rejected matched pairs. The existing blocker code `real_field_and_support_adapter_not_implemented` is retained for compatibility: field assembly now exists, but the full verified scientific-support adapter still does not. Do not remove the guard merely to clear that code.

## Actual real-data checks

| Check | Result |
| --- | --- |
| Default salinity CLI | Exit 3, empty stderr, 18,569-byte JSON |
| Salinity engine state | `blocked`; nine unchanged scientific blockers plus retained real-mode guard |
| Native field | Existing 2,704-value salinity snapshot passed through the verified reader |
| Spatial rows | 14 retained; 5 inside / 9 outside, kept separately from engine results |
| Real accepted pairs | 0; overlap `not_evaluated`, never an evaluated no-overlap claim |
| Temperature, in-memory policy override only | 18,707-byte blocked output; zero jointly eligible samples; eleven scientific/quantity blockers plus guard |

The temperature check did not rewrite `config/comparison.yaml`. Both runs completed the coordinator's post-input checks. Existing raw/model/observation/static inputs were not rewritten or acquired. The 9.2 GB BIO-ROMS file was not reread. No real successful matching or 5.10 end-to-end acceptance is claimed.

## Verification

New execution tests: **18 passed, 45 warnings**. They exercise actual blocked kernel invocation, native values/masks retained, pair-selection suppression, identity/mode mismatches, post-read changes, absent-candidate invariants, forged reports/blockers, output limits and CLI blocked/sanitized behavior. Tiny fixture files are synthetic; static reader boundaries are explicitly mocked for assembly tests. Acquisition/reader behavior remains covered separately.

An early test setup reused a static acquisition fixture and hit a Windows publication permission error. Assembly tests were decoupled from acquisition instead of adding retries or weakening production publication. The reused audit fixture also had placeholder eligibility counts, which the integrated engine correctly rejected; fixture counts now reflect its actual synthetic samples. These were test setup corrections, not bypasses of production validation.

Final full regression: **893 passed, 4 Windows symlink-permission skips, 1,614 warnings in 273.94 seconds**. This includes the 18 new execution tests; counts overlap and must not be added. Warnings remain NumPy/NetCDF/xarray/Starlette deprecations and the deliberately invalid-range fixture. The targeted run additionally reported provider-plugin discovery blocked by offline fixtures. No test failed in the final full run.

Ruff lint/format passed for 110 Python files, `pip check` found no broken requirements, and all 31 maintained Markdown files passed local-link/fence/final-newline checks. Commands ran through `ocean-env/Scripts/python.exe`, with pytest/Ruff using `backend/pyproject.toml`. Existing synthetic kernel regressions cover successful pairs, genuine evaluated no-valid-pair cases, time boundaries, masks, bottom/error endpoints and tolerances. Those synthetic outcomes must not be reported as real-data success.

## What remains before real matching / 5.8

Resolve the [5.7-B decision register](MILESTONE_5_7_SPATIAL_SUPPORT.md#scientific-decision-register--still-blocking): exact daily interval mapping, vertical-reference compatibility, reviewed grid-resolution observation support/connectivity and selection-specific tolerances; temperature semantics remain separate. Then implement a verified physical-support path and deliberately revise/test the real guard and result contract. This checkpoint provides no configuration switch that can do that prematurely.

No provider clarification was sent or new evidence source acquired. If those actions are needed, request explicit authorization. The next approval must identify the evidence/decision work or a separately labelled synthetic-only milestone; do not silently start 5.8 or mark the whole 5.7 complete.

## Completion attempt — evidence/review boundary

The subsequent user instruction authorizes completing the remaining 5.7 implementation without repeated internal checkpoint approvals. It does not supply the missing scientific decisions. This continuation inspected the saved policy and current contracts and pursued primary-source evidence; it made no runtime-code, raw-data or configuration changes. The test totals above remain the last completed implementation regression, not a new test run.

The [GLORYS12 producer paper](https://doi.org/10.3389/feart.2021.698876) describes a 50-level model and assimilation of in-situ profiles, including Argo. It reinforces the need to distinguish comparison from independent validation. It does not, in the material inspected, resolve the later version202311 ARCO midnight-label interval mapping or establish the required pressure-depth-to-static-bathymetry reference transformation. This is a scoped evidence finding, not a claim that the provider has no answer. The existing PUM and GSW findings in the [decision register](MILESTONE_5_7_SPATIAL_SUPPORT.md#scientific-decision-register--still-blocking) remain unchanged.

Completion requires these distinct inputs:

1. **Provider evidence:** the exact UTC averaging interval represented by each version202311 midnight label, and the applicable vertical reference/relationship for the distributed depths and static bathymetry. Use the existing [unsent clarification draft](MILESTONE_5_7_SUPPORT_EVIDENCE.md#provider-clarification-draft--not-sent); no message was sent.
2. **Project scientific decisions:** explicit horizontal, vertical and temporal limits with rationale, plus approval of a resolution-limited observation wetness/connectivity rule or suitable additional geometry. These are not facts that a generic catalogue lookup can decide. Limits must not be tuned until these particular observations produce pairs.
3. **Implementation after those inputs:** bind the accepted evidence and rules to the verified snapshot, populate physical support and time cells, replace the unconditional real guard with tested verified-path checks, and run the actual real-data command plus regression suite. Real pair counts may legitimately be zero after evaluation; blocked output is not that outcome.

Salinity is the first narrow real-data target. Temperature still needs its separate compatibility evidence; an enabled salinity path must not silently enable temperature. A separately labelled exploratory mode using declared approximations would change the current verified-only contract and needs an explicit scope decision; it must never mark those approximations as verified evidence.

**Status: full 5.7 incomplete, awaiting evidence/review.** More generic metadata searches or additional wrappers returning the same blocked report do not resolve this boundary. Numeric settings alone cannot enable real matching. No new source download, provider contact, metrics, API or frontend work was performed.

## Authorized contact attempt — 2026-09-24

The user explicitly approved submitting the existing clarification draft, then asked to continue. The Gmail connection check returned not connected; no email-send operation was executed. The official Help Center messenger showed no existing messages or new-message action in the unauthenticated session. The [current official contact page](https://marine.copernicus.eu/contact) explicitly directs users to log in before chatting with support. Its login link opened an unauthenticated page; no request, ticket or provider reply was obtained. The contact and login tabs were retained for user sign-in. No password was entered, saved or added to project files.

Initial communication status at that handoff: **authorized, not sent; awaiting user login**. This specific contact no longer needs another coding/contact approval. Provider confirmation and project scientific policy review remain separate requirements; neither has been completed by opening the chat. No application code, data or scientific gate changed, and no tests were rerun for this documentation-only update.

### Follow-up — 2026-09-25

After the user signed in, the product catalogue showed a logout link and the messenger displayed the account greeting, verifying login in that session. Home showed help articles but no new-message action; Messages showed no messages and no composer. The product description's metadata-chat action opened the same messenger. The [product contact page](https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/contacts) displayed a chat entry, but interacting with it did not open a message composer. No request text was entered or submitted; no ticket or provider response exists from these attempts.

At that attempt, plugin discovery confirmed Gmail was installed, but its profile check returned not connected. The status was **authorized, not sent; awaiting an available support composer or user-connected Gmail**. Do not ask the user to repeat login solely because the previous handoff record said login was pending. No runtime code, data, policy or tests changed.

### Email sent and verified — 2026-09-25

After the user connected Gmail, the connection was verified and a narrow Sent-folder search for this recipient/version found no preceding email. The approved clarification was sent once to `servicedesk.cmems@mercator-ocean.eu`, the contact published in the [product PUM issue 1.5, November 2023](https://catalogue.marine.copernicus.eu/documents/PUM/CMEMS-GLO-PUM-001-030.pdf). The send response and independent metadata readback both carried the `SENT` label; recipient and subject were verified.

- Sent at: **2026-09-25 06:00:21 UTC / 11:30:21 IST**.
- Subject: **Metadata clarification: GLORYS12 daily version 202311 time intervals and vertical reference**.
- Gmail message/thread ID: `1a0d72686ad99bc7` (not a provider ticket number).
- Questions: exact daily interval/ARCO time encoding; distributed-depth reference and compatibility with pressure-derived depths/geoid bathymetry; thetao temperature scale/reference pressure; deptho_lev indexing convention.
- No attachments, credentials, local paths, private project files, CC or BCC were sent.

Status at the send checkpoint: **sent, substantive reply pending**. Gmail acceptance alone was not proof of recipient delivery, provider review or resolution. Do not send a duplicate initial request. A provider answer must be assessed against the exact saved inputs before changing scientific evidence flags. Project tolerances/connectivity policy still require their separate review. No runtime code, data or matching gate changed, and no application tests were rerun for this documentation-only update. No automatic inbox monitor was configured.

### AI reply assessed; human review requested — 2026-09-25

Reading the original thread and a narrow related-message search found reply `1a0d727a242408a1`, dated 06:01:33 UTC, from the same service desk. Its footer explicitly identifies the author as CopernicusMarineService's AI Agent, Blu. Message authentication headers report SPF/DKIM/DMARC pass; sender authentication does not establish scientific correctness.

- Daily full-UTC-day/noon-centred averaging is reiterated, but the reply explicitly lacks confirmation of the observed ARCO midnight-label encoding.
- The reply describes level centres and asserts bathymetry/datum details, but supplies no version-specific reference or pressure-depth transformation. These statements are recorded as unverified provider-AI assertions, not accepted support evidence.
- It explicitly cannot confirm thetao reference pressure/ITS-90, deptho_lev indexing/count meaning, or a published version202311 reference.

Consequently, no matching evidence flag, time interval, tolerance or physical-support field was promoted. The email's general native-grid description also cannot replace verification of the actual distributed regular-grid snapshot.

A same-thread follow-up requested human technical/product-team verification of the original questions, with an explicit example UTC interval and a request to substantiate vertical-reference claims. Follow-up Gmail message `1a0d72e40b63cec9`, thread `1a0d72686ad99bc7`, was sent at **06:08:47 UTC / 11:38:47 IST**. Independent metadata readback verified SENT, recipient, subject and In-Reply-To. No attachments, credentials, local paths or extra recipients were added. This is an escalation request, not proof that a human has accepted or resolved it.

Current status: **human technical review requested; version-specific confirmation and project policy review pending**. The user declined 5.8, so no metrics work was started. No runtime code/data/configuration changes or new application test run occurred. Full 5.7 remains incomplete; do not substitute more blocked wrappers or resend the escalation while waiting for a response.

### Human reply assessment — 2026-09-26

The original thread and a narrow related-message search were checked. The substantive new message is `1a0d893c3a5dfa96`, from Gabrielle at the same service-desk address, dated **2026-09-25 12:39:16 UTC**. A preceding Blu message only acknowledged the support team's availability; it is not scientific evidence.

| Topic | Human response and implementation consequence |
| --- | --- |
| Time | Describes the daily data as representing the interval centre. Does not state the endpoints for the concrete midnight-labelled ARCO sample. Applying midnight +/- 12 hours would differ from the PUM's full UTC-day wording; do not choose between these interpretations without clarification. |
| Depth | Requests that the question be reformulated. No vertical-reference relationship or transformation was confirmed. |
| Temperature | Confirms potential temperature in the EOS-80 framework. This is useful new provider evidence, but the exact delivered scale and reference pressure were not stated; do not silently enable the existing ITS-90/GSW comparison target. |
| deptho_lev | Reports no documentation found on the indexing convention. Preserve it uninterpreted; current full-mask diagnostics do not require deriving wet levels from that index. |

A same-thread reply provided two explicit candidate intervals for the saved `2019-01-29 00:00 UTC` label and asked for the actual endpoints. It reformulated depth using an Argo pressure-derived depth, the saved shallow model levels and the difference between local sea surface, a fixed reference surface and the geoid. It asked whether additional sea-surface height/other corrections are needed, requested remaining temperature details, and deferred interpreting deptho_lev rather than making it an unnecessary dependency.

Follow-up `1a0dbf0fbbfcc035` was sent at **2026-09-26 04:19:58 UTC / 09:49:58 IST** in thread `1a0d72686ad99bc7`. Independent metadata readback verified SENT, recipient, subject and reply linkage to Gabrielle's message. No attachments, private files, credentials or extra recipients were included. This is a targeted clarification of an actual reply, not a duplicate of the initial request.

Current status: **human reply partially informative; exact time/depth/temperature contract and project tolerance/connectivity review still pending**. `config/comparison.yaml` was inspected and still has three null/unreviewed limits. The reply does not select those project limits. No runtime code, source data, configuration or scientific gates changed, no new application tests were run, and no real matching completion is claimed. Documentation records the new evidence without converting uncertainty into a verified flag. No 5.8 work or automatic monitoring was started.
