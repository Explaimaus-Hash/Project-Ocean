# Ocean_2 — permission-gated development order

## All-date surface archive — 2026-09-28

The user approved connecting every actual date in the downloaded BIO-ROMS V2 file to frontend viewing. Current implementation/preparation and verification are tracked in [the archive milestone](docs/BIO_ROMS_ARCHIVE.md). This supersedes earlier three-prepared-timestamp limits/status and no-new-preparation notes only for this local SST/SSS archive. No downloads, source/science-policy changes or comparison recomputation are authorized or implied.

## Current handoff — frontend integration approved

5.10 backend acceptance is complete: 1,021 passed / 4 Windows skips, with warnings and bounded evidence in [5.10](docs/MILESTONE_5_10.md). The user subsequently approved integrating and running their supplied frontend. [Integration milestone](docs/FRONTEND_INTEGRATION.md) connects existing prepared routes without changing backend scientific policies or adding ingestion. Older ask-before-frontend statements below refer to preceding checkpoints. New backend depth/current/profile/source capabilities and deployment remain separate future scope.

## Current 5.10 scope — approved

The user approved [5.10 local end-to-end acceptance](docs/MILESTONE_5_10.md): read-only real comparison replay/API consistency, bounded raw-to-surface checks, temporary real loopback HTTP, failure cases, regression and scoped measurements. No new acquisition, scientific unblocking, frontend or deployment. After recording final checks, ask before Part 6 frontend real-payload/capability compatibility; this does not imply missing depth/current/source integrations are complete. Earlier awaiting-5.10 statements below are historical.

## Current 5.9 outcome

Approved [5.9 comparison API](docs/MILESTONE_5_9.md) is implemented: explicit immutable snapshot publication, read-only catalogue/summary/paginated samples, safe error handling and visible exploratory limitations. Real result `c_0abd2057c5bc5c41fcf49109` was saved and read back through the in-process API. **Next approval: 5.10 end-to-end backend verification.** Frontend remains last; no new source acquisition, provider message or strict scientific unblocking is implied. Earlier no-5.9 statements below are historical.

## Current 5.8 outcome — 2026-09-27

The user approved exploratory comparison metrics. [5.8](docs/MILESTONE_5_8.md) now implements authenticated read-only residual/count/bias/RMSE reporting, preserving assumptions and strict scientific blockers. Actual selection: 2 pairs/14 rows, bias +0.046519 and RMSE 0.046520 PSS-78; no independent-validation claim. **Next: request approval for 5.9 comparison API.** No API, persisted comparison product, worker or frontend was added. Earlier no-5.8 authorization/status statements below are historical.

## Current 5.7 outcome — 2026-09-27

The user explicitly changed scope to permit assumptions cross-checked online. [The separate exploratory salinity implementation](docs/MILESTONE_5_7_EXPLORATORY.md) is complete and yields 2 assumption-labelled real pairs from 14 observations. Strict provider-verified matching remains blocked; the existing strict policy is unchanged. This supersedes the earlier verified-only completion boundary **for the labelled experiment only**. No 5.8 work is authorized or implemented yet. Next proposal: 5.8 residuals/counts/bias/RMSE on explicitly exploratory inputs, with provenance/assurance propagated and no claim of independent validation; request permission first. Temperature and other-source comparison support are not implied.

The full build lives in `C:/Users/pc/OneDrive/Desktop/ocean_2`. Implement one approved part at a time. Finish its checks, update the project Markdown files, give a 2–4-line result/next-step summary, and ask the user before the next part. The frontend is the final part; do not use its reusable prompt as immediate authorization. The user split Part 5 into approximately 20-minute checkpoints, each separately approved; a timebox is not a guarantee of finishing or permission to skip scientific checks.

## Part 1 — backend foundation (complete)

Implemented and checked: Python 3.12 environment, a small FastAPI app, typed `GET /health`, developer `/docs` and `/openapi.json`, safe process-environment configuration, pinned runtime/development requirements, 14 passing offline tests, and Windows instructions. No provider credentials, downloads, ingestion, or scientific imports in API startup. `/ready` stays absent until real prerequisites exist. See [docs/MILESTONE_1.md](docs/MILESTONE_1.md) for evidence and the two dependency warnings. Part 2 was subsequently approved.

## Part 2 — local dataset registration and metadata inspection (complete with fixtures)

Part 2 was approved while V2 was downloading. It implemented source registry, local input-state checks, header-only NetCDF inventory, optional streamed MD5 verification, and explicit atomic report saving, verified with temporary fixtures. Header inspection alone does not compute coverage/capabilities and still reports `not_prepared`, not ready. No automatic acquisition or HTTP data route was added in that part. The subsequent approved part 3 completed real V2 verification and added the preparation/data routes below; [docs/MILESTONE_2.md](docs/MILESTONE_2.md) remains the historical checkpoint.

## Part 3 — bounded preparation and scientific data APIs (complete for local V2 surface selection)

Approved after download. Verified V2 checksum, actual axes/time/calendar/units and surface-only dimensions. Implemented bounded native-resolution preparation, separate strided previews, immutable manifest-backed outputs, typed versioned catalogue/metadata/frame/time-series APIs, and configured local `/ready` with HTTP 200/503. Original data is unchanged; no operation runs at startup or `/health`. A real SST/SSS Jan–Mar2019 selection is served and sample-checked against the raw source. Direct netCDF4 frame/cache control was retained without adding xarray or provider packages. Known limits, tests, warnings and measured performance scope are in [docs/MILESTONE_3.md](docs/MILESTONE_3.md). Quantity harmonization, observation comparison and full vertical/current integrations are not claimed. Part 4 was subsequently approved.

## Part 4 — source integrations and observations (approved; implemented with source-specific live limits)

Implemented explicit bounded GODAS/Copernicus/Argopy/FTP acquisition, immutable source provenance, core observation QC/raw-adjusted normalization and paged scientific sample APIs. Local LAS-export import is available. Source-specific evidence/limitations, tests and commands are in [docs/MILESTONE_4.md](docs/MILESTONE_4.md). Copernicus authentication and daily version `202311` were verified in the credential-authorized follow-up; that is not a prepared-data claim. Reachable inspected GODAS and scientifically usable in-box glider data remain unresolved. Acquired model subsets still need verified preparation/serving before depth/current controls. No frontend or comparison was started. Ask permission before part 5.

## Part 5 — comparison and backend verification

Provider-contact update: [human support replied and was assessed on 2026-09-26](docs/MILESTONE_5_7_EXECUTION.md#human-reply-assessment--2026-09-26). EOS-80 potential temperature is confirmed as a provider statement, not the remaining scale/reference-pressure contract. Exact midnight-label intervals and the depth relationship still need clarification; a concrete same-thread follow-up was sent and verified. Do not duplicate it. Technical confirmation and project tolerance/connectivity policy review remain pending. The user explicitly declined starting 5.8; stay within 5.7.

Latest instruction supersedes internal 5.7 checkpoint approvals: continue through 5.7 without asking permission between coding steps. Full 5.7 is currently **blocked on scientific evidence/review**, not on permission to write the remaining adapter. The [completion-attempt record](docs/MILESTONE_5_7_EXECUTION.md#completion-attempt--evidencereview-boundary) identifies the decisions that require external evidence or an explicitly changed exploratory scope. Do not substitute another blocked diagnostic milestone for completion. Separate approval still applies to 5.8 and to provider messages/new acquisition.

Latest explicit 5.7-C approval produced [guarded local execution](docs/MILESTONE_5_7_EXECUTION.md): verified inputs now reach the engine, which remains blocked before pair selection. This does not resolve the scientific decisions below or finish 5.7. Next permission is for remaining evidence/decision work, not automatic 5.8; any synthetic-only metrics scope requires separate explicit approval.

Current 5.7-B: [candidate-bound spatial diagnostics](docs/MILESTONE_5_7_SPATIAL_SUPPORT.md) are implemented and locally checked. This completes supported diagnostic coding, not the unresolved scientific decisions. Next bounded approval is to resolve/review time/datum/grid-support/tolerance evidence; 5.7-C cannot enable real matching while those remain unknown. Do not repeat 5.7-A or reacquire support.

Preceding 5.7-A: [offline static-support reader](docs/MILESTONE_5_7_STATIC_READER.md) implemented and tested against saved inputs, now reused by 5.7-B diagnostics. Remaining scientific evidence/review and 5.7-C real integration are separate. Do not redownload the existing support snapshot automatically. Full 5.7 remains unfinished; no real matcher, metrics or API is enabled by successful local static verification.

Historical preceding checkpoint: [5.7 support-evidence research](docs/MILESTONE_5_7_SUPPORT_EVIDENCE.md) identified the static source; the subsequent acquisition above is now complete. Its earlier request for acquisition approval is superseded, not a request to download again. Provider messaging and a global-file fallback remain unauthorized. Use [the coding-agent handoff prompts](docs/CODING_AGENT_HANDOFF_PROMPTS.md) to propose separately approved continuations; the prompts themselves do not authorize implementation.

Parts 5.1–5.6 are complete as scoped implementations: audits, preparation, diagnostic conversions and [matching policy/preflight](docs/MILESTONE_5_6.md). Approved 5.7 has a [synthetic kernel/bridge checkpoint](docs/MILESTONE_5_7.md) and a [verified local reader/input-audit continuation](docs/MILESTONE_5_7_READER.md). Native fields and adjusted-depth alignment can now be verified locally; scientific support and real-kernel integration remain unfinished. Real matching remains explicitly disabled. **Ask permission to continue the remaining 5.7 work; do not automatically start 5.8.**

| Checkpoint | Approximately 20-minute scope | Status |
| --- | --- | --- |
| 5.1 — Scientific compatibility audit | Inspect actual model/observation metadata, overlap and missing definitions; record evidence and gates. | Complete as audit, not comparison readiness |
| 5.2 — Model preparation contract | Define bounded validation, native scientific storage, provenance and immutable prepared-model schemas; carry unresolved metadata explicitly. | Complete: schemas/tests and processor obligations; no prepared model |
| 5.3 — Model preparation implementation | Prepare the acquired small Copernicus selection with masks and native resolution preserved. | Complete: native product verified; no comparison or serving API |
| 5.4 — Pressure-to-depth conversion | Implement/test latitude-aware conversion with original pressure, uncertainty and vertical-reference provenance. | Complete: GSW module and read-only report; no collection rewrite or matching |
| 5.5 — Quantity compatibility | Resolve verified salinity/temperature definitions, explicit adjusted D-mode selection and supported conversions; reject unresolved cases. | Complete: adjusted selection/conversions and rejection gates; real temperature comparison blocked |
| 5.6 — Matching policy | Resolve averaging support, horizontal/depth/time tolerances, uncertainty, masks and no-overlap rules. | Complete as policy/preflight; real thresholds and support evidence remain blocking |
| 5.7 — Matching engine | Strict policy plus separately authorized, assumption-labelled shallow salinity experiment; retain exclusions/source identity. | Exploratory implementation complete: 2 real pairs/14 rows. Strict scientific matching remains blocked; see latest milestone. |
| 5.8 — Comparison metrics | Model-minus-observation residuals, valid-pair counts, bias/RMSE and fixtures. | Implemented for explicitly exploratory shallow salinity; strict verification remains blocked. See 5.8 evidence. |
| 5.9 — Comparison API | Bounded typed results and safe failures; no unimplemented/background processing hidden in HTTP requests. | Implemented for immutable exploratory snapshots: explicit operator publication and three read-only GET routes. |
| 5.10 — End-to-end verification | Small real-data workflow, failure cases, regression checks and scoped performance evidence. | Approved; local real replay, loopback and verifier tests checked. See current milestone for final regression and limits. |

If a checkpoint does not fit its timebox, stop at a safe state and report remaining work before requesting continuation. Do not automatically execute the next row. Known unknowns may remain in a preparation contract, but dependent comparisons stay disabled until the evidence is resolved. Never use display-downsampled arrays for matching or metrics.

## Part 6 — frontend LAST

Only after separate approval, use [FRONTEND_IMPLEMENTATION_PROMPT.md](FRONTEND_IMPLEMENTATION_PROMPT.md) to build the Next.js/React/TypeScript, CesiumJS, and Plotly UI. Start this final part with a minimal real-payload compatibility check, then implement the complete Earth-style launch, globe workspace, analysis, profiles, comparisons, and data-source tabs. Verify actual depth/volume/vector support, cancellation, caching, loading/error states, accessibility, and measured performance targets.
