# Part 5.10 — local end-to-end backend acceptance

## Scope

Approved on 2026-09-27 after 5.9. This milestone checks the implemented local prepared-data workflow, safe failures, regression coverage and measured API costs. It does **not** certify every original problem-statement capability, independent scientific validation, live provider availability, deployment or frontend performance. No source acquisition, credential use, provider message, new API, scientific-policy change or frontend was included.

## Repeatable comparison verification

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.verify_comparison c_0abd2057c5bc5c41fcf49109 --accept-assumptions --page-size 5
```

The new development-only command reruns authenticated local exploratory matching/metrics, binds their canonical report to an **existing** comparison ID/private report hash, and checks the saved public projection. It then checks health, explicitly unconfigured readiness (503), catalogue/metadata, all/matched/excluded pages, exact row order/values, summary/assumption consistency, invalid queries, beyond-last-page behavior and 30 identical repeated sample responses. Published file hashes/stats and policy identity must remain unchanged. Missing, corrupt or different snapshots fail; it never prepares, publishes, downloads or repairs them.

`--accept-assumptions` is required. `--page-size` accepts 5, 100 (default) or 500; optional `--policy` and `--support-id` follow the existing operator selection. Exit 0 means the selected snapshot and current inputs are consistent, including a legitimate zero-pair or partially blocked result whose state remains visible. Exit 2 is a sanitized verification failure. This command reuses the existing projection and science contracts: it is an integration consistency check, not an independent scientific algorithm.

### Actual comparison result

- Snapshot: `c_0abd2057c5bc5c41fcf49109`; daily Copernicus version 202311 against preserved Argo observations.
- Fresh replay matched the saved report/projection: 14 evaluated samples, 2 accepted exploratory pairs, 12 exclusions (9 horizontal-support, 3 pressure-endpoint-support).
- Bias +0.04651907179504633 and RMSE 0.04651981657958769 PSS-78; assumptions and source identities unchanged.
- With page size 5: 3 all-sample pages, 1 matched page, 3 excluded pages matched exactly.
- All three saved comparison files and the policy retained their hashes/modification times.
- Separate strict `scripts.run_local_matching` returned exit 3, `blocked`, zero pairs and ten retained blocker codes, including the real-field/support guard. No strict scientific gate was bypassed.

## Surface and observation workflow

Repeated the existing read-only command:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.verify_product p_7c8210052d41d41259724e2d --check-raw
```

All six bounded raw SST/SSS point values matched the served three-timestamp series exactly at 75E / 0.0246918667N. Native scientific output remains separate from the stride-8 preview. Preview is 95 × 136 cells / 170,898 JSON bytes; scientific and preview files remain 10,093,402 / 233,615 bytes. Oversized scientific frame returned 413; unavailable variable was rejected. This is a six-value source check, not a fresh whole-file checksum or exhaustive V2 validation.

The existing Argo collection `o_c645f248f801845378f0fdaf` was served through actual HTTP with 14 native points / 18,537 bytes. Its raw/adjusted/QC fields remain separate from the comparison projection; no independent profile identity was invented.

## Actual loopback HTTP smoke check

A temporary Uvicorn instance bound only to an OS-assigned free port on `127.0.0.1`, with the real surface product explicitly required for readiness. Standard-library HTTP requests exercised **all 13 implemented application GET paths**, each returning 200 with `no-store` and bounded JSON: health, readiness, dataset catalogue, surface metadata/frame/series, acquisitions, observation catalogue/metadata/samples, comparison catalogue/metadata/samples.

Also verified 422 for invalid comparison page size, 404 for a nonexistent comparison ID and 413 for the oversized scientific frame. This adds a real local socket/ASGI check beyond TestClient. The owned server was stopped and its socket closed afterward; no user's existing server was stopped. No browser, external network, TLS deployment, CORS integration or multiuser load was tested.

To manually inspect the same paths, use the existing [run instructions](../README.md#run-the-backend-now) and [route guide](API_ROUTES.md). The temporary smoke run did not persist server/environment configuration.

## Performance evidence

Reference machine: Intel Core i9-14900HX (24 cores / 32 logical processors), 16,869,548,032 bytes reported physical memory; Windows 11 build 26200, Python 3.12.10, pinned `ocean-env`. Sequential requests, filesystem cache not cleared, no deliberate CPU/network throttling. p95 is nearest-rank from 30 repeated requests per row, excluding prior warm-up/check requests. JSON body sizes are not complete TCP/HTTP wire sizes.

| Measurement | Observed | Scope |
| --- | --- | --- |
| Fresh authenticated comparison replay | 1.758 s | Operator verification, existing local inputs, no publication |
| Comparison page p95 | 8.01 ms / 15,938 bytes | In-process TestClient; first measured page was already warmed by acceptance checks |
| Surface preview p95 | 32.18 ms / 170,898 bytes | In-process; first preview 169.45 ms, not cold disk |
| Surface preview p95 | 35.53 ms / 170,898 bytes | Persistent sequential loopback HTTP |
| Argo sample-page p95 | 15.51 ms / 18,537 bytes | Persistent sequential loopback HTTP |
| Comparison sample-page p95 | 10.14 ms / 15,938 bytes | Persistent sequential loopback HTTP |
| Surface verifier peak working set | 126,668,800 bytes | Entire verifier process including bounded raw check, not preparation/API-only memory |

These small-selection measurements do not establish 5,000-row worst-case performance, hard memory caps, concurrent throughput, cold-cache speed or production SLAs. Browser globe startup, displayed-layer latency, FPS, interaction cancellation, memory growth and GPU budgets remain unmeasured. Do not mark the architecture's browser targets achieved.

## Failure coverage and regression

Added `backend/tests/test_comparison_verification.py`: 18 offline tests passed (55 warnings). They cover exact paging/replay, zero/partial results, changed/missing snapshots, mismatched replay, policy changes during verification, HTTP status/header/row/assurance regressions, bounded page configuration, required opt-in, no publication and sanitized CLI failures. The unit fixtures mock replay with explicitly synthetic reports; the separate real command above exercises the actual authenticated readers.

Initial new-test failures were test-harness issues: blocking all socket connections also blocked Windows asyncio's internal loopback socket pair; a partial-result fixture lacked its required unresolved-support reason; trailing JSON whitespace was incorrectly treated as semantic corruption. Tests now allow only loopback for event-loop setup, retain partial-state reasons and use actual malformed JSON. Production behavior was not weakened to satisfy those tests.

Existing regression coverage includes missing/corrupt prepared inputs, resource limits, invalid requests, no-overlap/null metrics, QC/depth/time/support gates, failed publication/conflicts, no raw/provider work in HTTP and independent startup/health. Existing publication failure history remains in [5.9](MILESTONE_5_9.md); this milestone does not erase it or guarantee permanent access errors cannot occur.

Final backend regression completed: **1,021 passed, 4 Windows symlink skips, 1,835 warnings in 169.00 seconds**. Project-configured Ruff lint/format passed for 125 Python files; `pip check` reported no broken requirements. The HTTPX/TestClient deprecation and other existing warnings are retained; no dependency upgrade was bundled into acceptance work. Subsequent user-approved frontend work is tracked separately in [the integration milestone](FRONTEND_INTEGRATION.md); the no-frontend statements below describe this backend-only checkpoint.

## Remaining capability boundaries / handoff

| Area | Implemented local scope | Still not established |
| --- | --- | --- |
| INCOIS BIO-ROMS | Prepared V2 SST/SSS surface preview and scientific point/region reads | Full depth/current/volume support (absent from this V2 file); all variables/date selections |
| INCOIS GODAS | Bounded adapter and LAS-import path | Currently reachable inspected live dataset; earlier timeout is not invalidity |
| Copernicus | Small native model, authenticated local reads, exploratory salinity comparison | Native depth/current-serving routes, full ocean/water-column support, verified temperature comparison |
| Argo | 14 QC-preserving points and exploratory sample comparison | Proven separate profile identities, independent validation |
| IFREMER glider | Preserved Bella acquisition and normalization safeguards | Usable in-region QC-valid collection; metadata conflict remains unresolved |
| Frontend/deployment | No frontend added; API contract available | Browser rendering/UX, CORS/auth/deployment, sustained load and production acceptance |

All four source families remain in scope. Next, **only after fresh approval**, Part 6 begins with frontend real-payload/capability compatibility, then the Earth-style shell/globe. Unsupported layers must stay disabled with reasons; a successful backend checkpoint is not permission to fabricate missing depth, currents, profiles or scientifically verified comparisons. Additional backend capabilities require their own scoped work.
