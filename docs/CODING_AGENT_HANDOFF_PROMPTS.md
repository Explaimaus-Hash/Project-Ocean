# Ocean_2 — coding-agent handoff and approval-gated prompts

Current handoff: the user approved [5.10 local backend acceptance](MILESTONE_5_10.md). Read that milestone and the latest root status before any historical prompt below. Preserve the verified local workflow and explicit scientific/source limitations; do not repeat 5.7–5.9, reacquire sources or interpret local API timings as browser acceptance. Next Part 6 frontend requires fresh approval and starts with actual API/capability compatibility. No frontend authorization is implied by this handoff.

Latest continuation: [5.9 prepared comparison API](MILESTONE_5_9.md) is implemented after approval. Read its operator-publication, public-projection and snapshot-freshness boundaries before using the historical prompts below. Next proposal is 5.10 end-to-end verification, requiring fresh approval. Do not rebuild 5.7–5.9, remove exploratory labels, put matching in HTTP, acquire more data or start frontend based only on this handoff.

Current handoff update (2026-09-27): the user approved assumption-labelled [5.7 matching](MILESTONE_5_7_EXPLORATORY.md), then [5.8 exploratory metrics](MILESTONE_5_8.md); both operator workflows are implemented. Read these latest milestones and root status first. Do not rerun the historical 5.7/5.8 implementation prompts below or remove strict scientific gates. Next proposal is 5.9 API, with fresh approval, bounded public contracts and explicit exploratory assurance. There is no comparison HTTP route or persisted comparison product yet. Sharing this handoff is not approval to build one.

Prepared on 2026-09-17. This document is a handoff, not authorization to implement any milestone. Start with the read-only onboarding prompt; obtain explicit approval before each coding checkpoint. Current continuation starts at remaining **5.7**, not by rebuilding 5.1–5.6.

## 1. What to give the other agent

Newest state: [5.7-C guarded execution](MILESTONE_5_7_EXECUTION.md) is implemented, connecting local readers/diagnostics to a blocked kernel invocation. Do not rebuild this plumbing or remove the real guard. Remaining 5.7-B scientific evidence/decisions still precede real enablement; use the latest milestone before any continuation. A/B and the reusable C prompt below record prior/proposed stages, not a claim that real matching is enabled.

Latest update: [5.7-B spatial diagnostic coding](MILESTONE_5_7_SPATIAL_SUPPORT.md) is implemented. Read its decision register before continuing: physical observation support, time/datum and reviewed tolerances remain unresolved. Do not rebuild diagnostics or automatically start 5.7-C/5.8; obtain a scoped approval for remaining 5.7-B decisions/evidence. The earlier 5.7-A update below is historical.

Current update: [5.7-A saved static reader](MILESTONE_5_7_STATIC_READER.md) is implemented and verified locally. Do not rebuild it using the reusable 5.7-A prompt below. Onboard read-only, verify current state, and propose 5.7-B policy/evidence next; real integration remains a separate 5.7-C approval. Full 5.7 is not complete.

Open the actual project folder: `C:/Users/pc/OneDrive/Desktop/ocean_2`. The older Documents workspace and older `ocean` project are not the build root. Give the agent this document and access to the files below, preserving relative paths.

### Required Markdown reading order

| File | Purpose |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Workspace boundaries, source restrictions and approval workflow |
| [README.md](../README.md) | Purpose, installed stack, commands and implemented status |
| [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) | Retained decisions and current checkpoint |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Components, scientific boundaries and reasons |
| [FILE_STRUCTURE.md](../FILE_STRUCTURE.md) | Existing versus proposed modules |
| [CONVENTIONS.md](../CONVENTIONS.md) | Naming, immutable data, resource limits and tests |
| [BACKEND_DEVELOPMENT_PLAN.md](../BACKEND_DEVELOPMENT_PLAN.md) | Milestone order and approval gates |
| [PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) | Original required capabilities; not completed-feature claims |
| [MATCHING_POLICY.md](MATCHING_POLICY.md) | Canonical matching/QC/support/tolerance rules |
| [MILESTONE_5_7_STATIC_READER.md](MILESTONE_5_7_STATIC_READER.md) | Latest offline static-reader implementation, verification and remaining work |
| [MILESTONE_5_7_SPATIAL_SUPPORT.md](MILESTONE_5_7_SPATIAL_SUPPORT.md) | Current candidate/stencil diagnostics, real result and remaining scientific decision register |
| [MILESTONE_5_7_EXECUTION.md](MILESTONE_5_7_EXECUTION.md) | Latest verified assembly/blocked engine invocation and real-data verification boundary |
| [MILESTONE_5_7_STATIC_ACQUISITION.md](MILESTONE_5_7_STATIC_ACQUISITION.md) | Preceding acquired support and original acquisition evidence |
| [MILESTONE_5_7_READER.md](MILESTONE_5_7_READER.md) | Verified model-field reader and blocked local audit |
| [MILESTONE_5_7.md](MILESTONE_5_7.md) | Historical synthetic-kernel/adjusted-depth implementation |
| [API_ROUTES.md](API_ROUTES.md) | Actual routes; proposed comparison routes are not implemented |

Retain the rest of `docs/` too. Read [MODEL_PREPARATION_CONTRACT.md](MODEL_PREPARATION_CONTRACT.md), [MILESTONE_5_4.md](MILESTONE_5_4.md), [MILESTONE_5_5.md](MILESTONE_5_5.md), [MILESTONE_5_6.md](MILESTONE_5_6.md) and [MILESTONE_5_7_SUPPORT_EVIDENCE.md](MILESTONE_5_7_SUPPORT_EVIDENCE.md) before changing their scientific contracts. Read [performance.md](performance.md) for later performance verification. Historical milestone facts remain dated; latest verified state supersedes earlier no-download/no-reader statements. A conflict in current scientific requirements must be flagged, not silently resolved by weakening checks.

The frontend implementation prompt is for a later, separately approved milestone. Do not use it to start frontend work during 5.7–5.10.

### Markdown alone is not enough for implementation

The agent also needs `backend/`, `scripts/`, non-secret `config/`, dependency files, tests and `.gitignore`. On this machine reuse `ocean-env/Scripts/python.exe`. On another machine, establish the new workspace/runtime explicitly; do not claim the Windows environment or local datasets transferred merely because the Markdown did.

For real comparison checks, the relevant existing local inputs include:

- Prepared model: `data/models/m_35e4c0ab33c1469a334ca837/`.
- Its acquisition: `data/raw/acquisitions/a_9e918d43555ffc26d3659e08/`.
- Argo collection: `data/observations/o_c645f248f801845378f0fdaf/`.
- Argo client/provider acquisition: `data/raw/acquisitions/a_d30181bd8998aca81bb33be1/`.
- Static support: `data/raw/static_copernicus/b_b18353b728b66639c7787d55/`, including manifest, subset and exact partial source read set.

Verify files before trusting them. Do not upload these datasets to another service automatically. Do not include passwords, `.env`, account screenshots, private history or the virtual environment in an external handoff. Retain all four source families in the design; this first matching implementation is specifically Copernicus plus Argo. Missing data on the receiving machine means real verification is unavailable, not that it passed. Do not redownload or expand the selection without approval.

## 2. Shared rules for every prompt

1. Every new checkpoint starts with a short read-only plan: scope, files to change, validation, missing decisions and expected output. Then ask, "Is checkpoint ko implement karne ki permission hai?" Wait for an explicit reply.
2. A prompt, this handoff, a previous approval or an earlier completed part is not blanket permission for the next checkpoint. After approval implement only that named checkpoint. End by asking for the next approval; do not continue automatically.
3. Aim for roughly20-minute work checkpoints. If a larger part needs multiple sessions, finish safely, save verified progress, state unfinished work and request continuation. Do not claim a timebox completed a milestone or skip validation to meet it.
4. Preserve user changes and original datasets. Keep work inside the confirmed build root. No Git staging/commit/reset/clean/worktree against the parent `C:/Users/pc` repository; establish a project-local boundary before any such operation. No older-project modifications.
5. Keep INCOIS, Copernicus, Argo and gliders together. Keep original-resolution scientific data separate from display previews, pressure separate from depth, and provider metadata/QC/provenance intact.
6. Do not guess time bounds, vertical datums, bottom numbering, temperature definitions or numeric tolerances. No fabricated verified flags, raw/adjusted mixing, wet-cell fallback or threshold relaxation to obtain pairs. Unresolved evidence is not no-overlap.
7. No source download, provider message, credential reuse/persistence, deployment, frontend, new background job or material dependency change outside the explicitly approved scope. Public scientific-documentation research is allowed when relevant; use primary sources and record findings.
8. Health/startup remain independent of scientific reads, ingestion and provider access. Raw NetCDF/private paths/credentials never become browser assets or public payloads.
9. After every approved checkpoint, substantial behavior change or safe stopping point, synchronize relevant Markdown before handing back. Do not rewrite every document after every small edit; update affected contracts/status and record the checkpoint once.
10. Run proportionate tests and report exact commands/counts, skips, warnings and scope. Old results are historical; targeted/full-suite counts overlap and must not be added. Never claim live/real/browser verification from synthetic tests.
11. Communicate in concise Hinglish. Final checkpoint summary is2–4 lines: what was done, what was verified, remaining blockers/next step, and a clear permission question. Detailed evidence belongs in the milestone document.

### Documentation update checklist

- `README.md`: current capability/status, new commands or setup changes.
- `PROJECT_CONTEXT.md`: exact latest checkpoint, verified input/output identities and remaining work.
- `BACKEND_DEVELOPMENT_PLAN.md`: scoped milestone status; differentiate implementation from unresolved scientific acceptance.
- `FILE_STRUCTURE.md`: new/moved modules and one-line ownership.
- `ARCHITECTURE.md`: component boundaries, data flow or scientific decisions and rationale.
- `CONVENTIONS.md`: newly adopted shared rules, not hypothetical patterns.
- `docs/MATCHING_POLICY.md`: only if approved matching rules or verified support handling change; preserve unresolved requirements.
- `docs/API_ROUTES.md`: actual route/schema/parameter/error changes only; never present planned routes as implemented.
- A dated checkpoint/milestone document: changed files, tests, source findings, limits and unfinished work.
- `AGENTS.md`: concise current continuation pointer/boundaries when checkpoint status changes.
- This handoff: update the current-state pointer if it becomes stale; do not change historical test results into new claims.

Check local links and status consistency after updates. Keep historical records dated and clearly label superseded statements. No secrets or full raw observation dumps in Markdown.

## 3. Prompt 0 — onboarding only

Copy this first. No implementation is authorized by it.

```text
Continue the existing Ocean_2 project, not a new scaffold.
Build root: C:/Users/pc/OneDrive/Desktop/ocean_2.

Read docs/CODING_AGENT_HANDOFF_PROMPTS.md and its required Markdown files, then inspect the relevant actual code and available local inputs without modifying them. Follow AGENTS.md and the shared approval/documentation rules in the handoff. If this is another machine, report the actual workspace/runtime/data available before assuming the recorded paths exist.

Current checkpoint: 5.7 has a synthetic matching kernel, adjusted-depth bridge, verified native model reader/input audit, a downloaded regional static snapshot with its 5.7-A replay reader, and 5.7-B candidate/stencil diagnostics. Read MILESTONE_5_7_SPATIAL_SUPPORT.md and propose the remaining scientific-decision/evidence checkpoint, not a diagnostic rebuild or automatic 5.7-C integration. Real matching remains disabled. Parts 5.8–5.10 and frontend are not implemented. Do not restart 5.1–5.6 or interpret their scoped completion as resolved real scientific evidence.

First report: implemented pieces, remaining 5.7 work, external/scientific decisions, and a small plan for checkpoint 5.7-A below. Distinguish recorded historical tests from anything you actually ran. Do not edit code/docs, download data or start a server yet. Ask for my explicit approval before implementing 5.7-A.
```

## 4. Prompt 5.7-A — verify/read saved static support

```text
Plan checkpoint 5.7-A only, following the handoff rules. Ask for approval before editing; this planning request does not authorize implementation.

After approval, implement a bounded read-only static-support reader for the existing saved snapshot. Reuse original model/observation readers and shared validation helpers. Validate contained paths, manifest/schema, source identity/version/mode, hashes/stat identities, encoding, dimensions, exact axes and mask/bottom values. Tie the snapshot to the intended verified model. Preserve the original partial read set; never treat absent global chunks as dry cells. Do not redownload.

Add typed internal outputs and corruption, wrong-source, grid mismatch, missing-value, masking and resource-limit fixtures. Preserve negative source elevation/attributes and document any explicit interpreted coordinate mapping; do not silently repair source semantics. The result is verified local support input, not accepted pairs or established observation/bottom/datum/connectivity semantics.

Verify against synthetic fixtures and the existing real snapshot if available. Update affected Markdown and record exact evidence. Stop after 5.7-A, summarize in2–4 lines, and ask permission to plan/start5.7-B. Do not advance to5.8.
```

## 5. Prompt 5.7-B — support rules and unresolved scientific decisions

```text
Plan checkpoint 5.7-B only. Inspect 5.7-A results and canonical MATCHING_POLICY.md. Present the proposed rules, evidence gaps and validation plan, then ask approval before implementation or changing scientific policy.

After approval, implement support handling only where evidence is sufficient: candidate-bound wet status, observation-position support at the distributed grid's supported resolution, local wet-depth-centre limits, bottom handling and coastline connectivity. Do not claim sub-grid coastline certainty, silently nearest-join coordinates or use a farther wet cell as fallback. Treat deptho_lev numeric agreement as a diagnostic, not proof of its indexing convention.

Separately investigate exact version202311 daily label-to-interval mapping, model/pressure-derived vertical-reference compatibility, and model temperature scale/reference. Record primary-source evidence, conflicting metadata and explicit unresolved states. Do not send a provider message or acquire additional data without separate approval.

Review horizontal/depth/time tolerances with a selection-specific rationale; do not invent universal defaults or mark them reviewed without the necessary decision. Present supported candidate choices and uncertainties for user/scientific review rather than increasing limits until pairs appear.

If evidence or decisions are missing, complete only the supported coding/tests, document exactly what is blocked and ask the specific question needed. Do not claim full5.7 completion or blindly repeat the same research. Update relevant Markdown, stop, and request approval for any continuation or5.7-C.
```

## 6. Prompt 5.7-C — connect the real matching path

```text
Plan checkpoint 5.7-C only. Recheck completion/evidence from5.7-A/B, actual policy and source identities. Explain which scientific requirements are satisfied or still blocked; ask approval before implementation.

After approval, connect verified scientific fields, original observations, adjusted quantities/depths and verified static support to the existing matching engine. Do not remove the real-mode guard merely because files exist; replace it only with a fully verified input path for the supported scope. Keep unknown requirements blocked, synthetic data labelled and temperature-specific exclusions intact. Salinity may be completed separately if every salinity requirement is satisfied; do not claim temperature completion from it.

Return identified accepted/rejected observations, actual native model indices, source labels/verified intervals, values/units, offsets, QC/errors, policy identity and per-row reasons. Preserve nearest-candidate-before-mask behavior, no fallback/extrapolation, pressure-error endpoint support and bounded work/output. No metrics or API in this checkpoint.

Test valid matches and genuine evaluated no-valid-pair cases, missing evidence, wrong identities, time boundaries, masks, bottom/uncertainty/tolerance failures and determinism. Run a small verified real workflow if prerequisites permit. Missing evidence must not be reported as evaluated no-overlap, and do not force positive pairs. Update Markdown; declare5.7 complete only for demonstrated supported scope, otherwise name the remaining blockers. Stop and ask permission before5.8.
```

## 7. Prompt 5.8 — comparison metrics

```text
Plan Part5.8 only under the handoff approval rules. Verify the actual5.7 result contract and scientific status first. If real5.7 is blocked, report that; any synthetic-only metrics continuation needs explicit approval and must not imply real comparison is ready. Ask approval before coding.

After approval, implement model-minus-observation residuals, valid-pair counts, mean bias, RMSE and exclusion counts from validated accepted pairs only. Preserve units, quantity definitions, real/synthetic mode, source/policy identity and numerical validity. Do not mix incompatible quantities or pool unrelated units. Missing/rejected samples are not zero; zero accepted pairs produce unavailable metrics with reasons, not zero error. Do not invent full uncertainty, weights or confidence intervals.

Keep calculations reusable outside FastAPI and test known numeric answers, sign convention, empty/single-pair cases, masks/nonfinite values and incompatible input. No graphs/frontend, comparison API or unapproved extra statistics. Update relevant Markdown and add a5.8 evidence record with exact tests and remaining limits. Stop with a2–4-line summary and request approval before5.9.
```

## 8. Prompt 5.9 — comparison API

```text
Plan Part5.9 only. Read the implemented5.7/5.8 contracts, actual routers, docs/API_ROUTES.md and performance limits. Propose exact methods/paths, bounded requests/responses, execution/storage behavior and safe error states; these routes are not already finalized. Ask approval before implementation.

After approval, expose only supported validated comparison results, accepted/excluded pairs and metrics through typed versioned FastAPI contracts. Bound selections, work, response size and pagination where needed. Clearly distinguish missing input, blocked scientific evidence, unsupported quantity, evaluated no-valid-pair results and invalid requests. Never return a misleading success-readiness flag or fabricated metrics.

Keep provider acquisition and expensive/unbounded preparation out of HTTP/startup/health. Do not invent a persistent worker, job progress or cache; any necessary architectural expansion requires approval. Exclude raw NetCDF, private paths, source credentials and traces from responses. Preserve existing APIs and real/synthetic labels.

Add API success/failure/limit/privacy/regression tests, verify actual OpenAPI, update API_ROUTES.md and other affected Markdown, and record exact implemented endpoints. Do not create frontend components. Stop and ask permission before5.10.
```

## 9. Prompt 5.10 — end-to-end acceptance

```text
Plan Part5.10 only. Inspect the actual supported5.7–5.9 scope and unresolved scientific gates, then propose a small acceptance dataset/workflow and checks. Ask approval before executing implementation/fixes or any newly required acquisition.

After approval, verify the full existing chain: preserved inputs -> QC/adjusted quantities/depths -> verified support -> matching -> metrics -> API payload. Use the real local selection where supported; show independently checked sample outcomes, deterministic repetition, original-file identity preservation, correct source/units/QC/policy provenance and explicit exclusions. Keep synthetic and real acceptance separate.

Exercise missing/corrupted input, unsupported quantity, rejected QC, no-valid-pair and resource-limit cases. Measure bounded execution/payload/resource behavior with environment, selection and cache conditions stated; do not label API timing as browser FPS or deployment readiness. Run relevant regression/lint/format/dependency checks, fix only in-scope defects, and rerun affected checks. No secrets or raw data in reports.

Update the maintained Markdown and create a final5.10 acceptance record: what passed, what failed or remains blocked, measured scope, commands and remaining source/backend capabilities. Do not claim all four sources, depth/current/volume serving or production readiness from one Copernicus-Argo comparison. Stop and ask for the next explicit decision; frontend remains a separately approved final milestone and must not start automatically.
```

## 10. How to approve and resume safely

Send one checkpoint prompt at a time. Let the agent propose the plan and ask. Then a suitable approval is:

```text
Yes, implement ONLY the checkpoint you just proposed. Do not start the next checkpoint. Verify it, update the affected Markdown, give the2–4-line completion/blocker summary and ask permission before proceeding.
```

For interrupted work:

```text
Read the latest saved checkpoint and inspect the current files first. Tell me what is genuinely unfinished versus already implemented. Propose only the smallest remaining step and ask approval; do not restart completed work, rerun downloads automatically or assume an earlier approval covers a new checkpoint.
```

This handoff does not promise that every listed checkpoint fits one20-minute session. External scientific evidence may require user/provider input; document that separately from remaining coding work.
