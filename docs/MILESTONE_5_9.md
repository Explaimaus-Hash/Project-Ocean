# Part 5.9 — prepared comparison API

## Scope and boundary

The user approved the comparison API after 5.8. Three read-only GET routes now expose explicitly prepared exploratory salinity results. HTTP reads only bounded prepared JSON: no matching, provider calls, raw NetCDF, publication, credentials or job queue. Health/startup stay independent; frontend and the broader 5.10 acceptance milestone have not started.

Results remain assumption-labelled, not scientifically verified or independent validation. Strict matching and its policy are unchanged. A prepared snapshot is a historical result, **not live source freshness, model readiness or whole-project readiness**. `/ready` continues to check its existing configured surface products only.

## Prepare once as an operator

```powershell
Set-Location 'C:\Users\pc\OneDrive\Desktop\ocean_2'
.\ocean-env\Scripts\python.exe -m scripts.prepare_comparison --accept-assumptions
```

This command reruns authenticated 5.7 matching and 5.8 metrics, rechecks the bounded policy, then publishes one immutable directory under `data/comparisons/<comparison_id>/`:

- `report.json`: private full metrics/matching evidence, at most 1 MiB; never read by HTTP.
- `result.json`: allowlisted public metadata plus all evaluated samples, at most 2 MiB; served only through bounded routes.
- `manifest.json`: private public-metadata/file-identity binding, at most 128 KiB.

The `c_` identifier derives from the complete private report and publication-version prefix. Publication uses an exclusive `.publish.lock`, a private staging directory and a final directory rename. Reuse validates existing public content and private-report hash/stat identity and leaves files unchanged. Conflicting content is rejected, not overwritten. Normal failures remove only that invocation's staging files. An interrupted process can leave a lock/stage requiring operator inspection; do not automatically steal/delete it. The lock coordinates cooperating writers, not hostile local filesystem access.

At most 32 comparison IDs are retained; directory scans inspect at most 65 entries before failing a 64-entry limit. No eviction or acquisition/job retry is implemented. Only the final directory rename has bounded handling for Windows errors 5/32/33: at most four attempts, waiting 0.05, 0.1 and 0.2 seconds. Each attempt uses the same validated sibling paths and refuses an existing destination. Persistent denial fails; permissions are never changed. No raw input is rewritten. The old matching/metrics commands remain read-only and do not publish implicitly.

Exit 0 means an evaluated snapshot was prepared/reused, including legitimate zero-pair results. Exit 3 means a blocked/partial snapshot was prepared with its state visible. Exit 2 means a sanitized failure. `--accept-assumptions` is required; optional `--policy` and `--support-id` use the existing local selection. No saved-report upload option or HTTP write route exists.

## HTTP contract

Start/restart the existing backend to load the new routes:

```powershell
.\ocean-env\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

| Route | Response |
| --- | --- |
| `GET /api/v1/comparisons` | Up to 32 prepared snapshot summaries or unavailable entries with reason codes. Empty catalogue is valid. |
| `GET /api/v1/comparisons/{comparison_id}` | Source/selection IDs, preparation time, scope, assumptions, strict blockers, metrics/counts and limitations. |
| `GET /api/v1/comparisons/{comparison_id}/samples` | Scientific pair/exclusion rows with coordinates, times, depths, original native candidate indices, offsets, reported errors and residuals. |

Sample query parameters: `offset=0..5000` (default 0), `limit=1..500` (default 100), optional `matched=true|false`. Filtering happens before pagination. `total` is the filtered row count; metadata summary always describes the entire snapshot. `next_offset=null` means no next page. An offset beyond the filtered total returns an empty page; missing metrics remain null, not zero. Excluded samples have null residuals and retain reasons/candidate diagnostics.

Every metadata/page retains `exploratory_assumptions`, `comparison_ready=false`, `independent_validation=false`, practical-salinity units, model-minus-observation convention, equal-sample weighting and unpropagated uncertainty. Source references include Copernicus daily dataset/version, model ID, observation collection and observation acquisition ID. Private paths, file stats/hashes, strict evidence context/reference text and the full private report are omitted by an explicit projection. Assumption identity is intentionally public.

Catalogue requests validate bounded manifests and public-file stat identity; detailed metadata/pages additionally verify the public JSON hash, contract, sample/metric consistency and before/after identities. No route rereads original source files. These checks detect ordinary corruption/change in trusted local storage, not an attacker who can replace both data and manifests.

All successful/error responses from these service contracts use `Cache-Control: no-store`. Unknown result: 404 `not_prepared`; invalid parameters: sanitized 422; changed/corrupt snapshot: 409; response byte limit: 413; capacity/unavailable catalogue: 503; invalid generated wire projection: 500. Public JSON is capped at 2 MiB, even for a requested 500-row page. No partial-success truncation is allowed. The API remains local-development scope; authentication, deployment and CORS are unchanged.

## Actual prepared selection

Saved ID: `c_0abd2057c5bc5c41fcf49109`. It preserves 14 evaluated samples, 2 matched pairs and 12 exclusions. Bias +0.04651907179504633 and RMSE 0.04651981657958769 PSS-78 are unchanged from [5.8](MILESTONE_5_8.md). Scientific restrictions remain those in [5.7](MILESTONE_5_7_EXPLORATORY.md).

Local URLs, after starting the server:

- [Comparison catalogue](http://127.0.0.1:8000/api/v1/comparisons)
- [Saved summary](http://127.0.0.1:8000/api/v1/comparisons/c_0abd2057c5bc5c41fcf49109)
- [Matched samples](http://127.0.0.1:8000/api/v1/comparisons/c_0abd2057c5bc5c41fcf49109/samples?matched=true)
- [Excluded samples](http://127.0.0.1:8000/api/v1/comparisons/c_0abd2057c5bc5c41fcf49109/samples?matched=false)

The first real publication attempt returned a sanitized filesystem `publication_failed` error and left no visible comparison/staging result. A subsequent attempt succeeded. The initial full regression also encountered one publication setup error (995 passed/4 skipped/1 error). An instrumented API-test run reproduced the failure specifically at directory rename: `PermissionError`, errno 13, Windows error 5. The process or filesystem condition behind it remains unconfirmed; do not attribute it to OneDrive or antivirus without evidence.

Microsoft defines Windows error 5 as access denied, and 32/33 as sharing/locking violations. These codes alone do not establish that an error is temporary. The bounded rename retry above is an engineering mitigation; tests cover one-off failures, permanent denial and a destination appearing between attempts. No ACL/security settings were changed. [Official Windows error definitions](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-).

Normal CLI reuse exited 0 with all three published file hashes/modification times unchanged. Failed attempts and the bounded mitigation are retained here rather than claiming publication can never fail.

## Verification and next part

Targeted API/storage and existing health/startup tests: **45 passed**, 55 warnings. Real-data verification uses FastAPI's in-process HTTP client, not a claim that a network server or browser was launched. Catalogue/summary/all samples/matched filter/excluded filter returned 200; invalid page size returned 422 and an unknown ID returned 404. Pagination showed 2 matched and 12 excluded samples; responses carried `no-store`. OpenAPI now contains 13 application paths. The respective successful response sizes were 2,386 / 2,256 / 15,938 / 3,599 (`limit=1`) / 13,470 bytes; these are payload measurements, not performance benchmarks.

A subsequent full run passed 1,001 tests with 4 Windows symlink skips, but two older static-reader corruption tests failed during synthetic fixture directory rename with Windows error 5. Their `republish` helper now copies into a separate recomputed-ID directory, retaining the original temporary fixture. Atomic publication is not that helper's subject; production static acquisition/reader code and corruption-rejection assertions are unchanged. The complete static-reader test module then passed **26 tests**, 25 warnings.

Final full regression on 2026-09-27: **1,003 passed, 4 skipped, 1,784 warnings in 160.43 seconds**, exit 0, using `.\ocean-env\Scripts\python.exe -m pytest backend/tests -q --disable-warnings --tb=short`. The four skips are existing Windows symlink-privilege cases (error 1314); they are not verified passing coverage. Warnings remain; this is not a warning-free claim. Part 5.9 is complete within the exploratory/local-development boundary above.

Normal real-data preparation/reuse was checked again after the final comparison code changes: exit 0, all three snapshot hashes/modification times unchanged, 14 rows / 2 matched / 12 excluded and unchanged bias/RMSE. Documentation checks found **233 valid local links across 12 Markdown files**. Dependency validation (`pip check`) found no broken requirements. Ruff must use `--config backend/pyproject.toml` when checking both `backend` and sibling `scripts`: that project configuration passed lint and formatting (**123 Python files**). A first invocation without explicit configuration inherited different rules for sibling scripts and reported eight findings; no unrelated style rewrite was made.

Next, only after approval: **5.10 end-to-end backend verification**, covering the prepared workflow, failure cases and scoped performance evidence. Frontend remains last. Do not interpret this milestone's local tests as completion of that separate acceptance scope or deployment readiness.
