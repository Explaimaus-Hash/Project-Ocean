# Part 5.2 — model preparation contract

Completed 10 September 2026 in `C:/Users/pc/OneDrive/Desktop/ocean_2`, after explicit approval for this checkpoint only. Part 5.3 and every later checkpoint require separate permission; frontend remains last.

## Outcome

Implemented private, validated native-model contracts, not the model processor. The [canonical contract](MODEL_PREPARATION_CONTRACT.md) defines bounded preflight, native scientific storage, source provenance, immutable publication and unresolved scientific gates for the next approved implementation.

| Added file | Delivered behavior |
| --- | --- |
| [models.py](../backend/app/schemas/models.py) | Frozen/tuple request, actual axes/source indices, budgets, source metadata summaries, deterministic identity and private manifest schemas; bounded JSON serialization without I/O. |
| [test_model_contracts.py](../backend/tests/test_model_contracts.py) | 42 synthetic offline contract tests, including invalid selections, pressure/depth separation, no-decimation indices, gates, immutability, identity and payload budgets. |
| [model_preparation.example.json](../config/model_preparation.example.json) | Schema-valid selection of the already acquired small four-field Copernicus input; not an executable preparation command yet. |
| [MODEL_PREPARATION_CONTRACT.md](MODEL_PREPARATION_CONTRACT.md) | Storage/validation decisions, reasons and explicit Part-5.3 enforcement obligations. |

README, architecture, conventions, file structure, current context, development plan, AGENTS and API route guide were synchronized. The API route guide still describes the same 10 application routes; no runtime route was added or modified.

## Important decisions

- Keep depth-resolved models in a separate future `data/models/m_.../` namespace. Existing `p_` surface storage and configured `/ready` behavior remain unchanged.
- Preserve native four-dimensional sample resolution, actual UTC labels and contiguous source indices. Separate source packing metadata from decoded float64 output. No preview or comparison data is generated here.
- Hash scientific identity including input/acquisition provenance, request, actual axes, source metadata summaries, limits and policies. Output files/publication timestamps remain outside identity; full identity and output checks are required before later reuse.
- Keep temperature-scale/reference, averaging-window, vertical-reference and wet-domain interpretation unresolved. `comparison_ready` and `api_serving` are fixed false for this contract version.
- Contract validation alone cannot establish coordinate/field correspondence, masks, metadata truth, file integrity or atomic storage. Those actual I/O checks are explicitly required in 5.3.

## Verification actually run

| Check | Observed result |
| --- | --- |
| New contracts + existing health/startup tests | 50 passed, 2 existing dependency warnings, 2.57 seconds. |
| Full offline regression suite | 428 passed, 4 Windows symlink-permission skips, 640 deprecation warnings, 173.69 seconds. |
| Final contract-only rerun after adding byte-limited serialization coverage | 42 passed, 0.28 seconds. The full suite had begun before this final helper was added; its final version is covered by this targeted rerun, not a claimed second full run. |
| Ruff check | Passed across backend and scripts. |
| Ruff format check | All 61 Python files already formatted. |
| Dependency consistency | `pip check`: no broken requirements. No dependencies installed or changed. |
| Saved example request | Validated against `ModelPreparationRequest`; variables and selection agree with the existing Copernicus acquisition manifest. |
| Acquired model input integrity | SHA256 still matches its manifest and the Part-5.1 value `c92568212fc4b2b46f31162106bc7aced404e1c32d9675267d1d399c5abfb3a3`; size/mtime match the manifest and remain unchanged across this read. |
| Preparation output boundary | Confirmed `data/models/` does not exist; no prepared model was published. |
| Markdown handoff checks | All 18 root/docs Markdown files passed local-link, code-fence and final-newline checks. |

Warnings concern the existing HTTPX/Starlette/AnyIO integration and NumPy/xarray/NetCDF array-shape/timedelta deprecations. The four skipped tests require Windows symlink privileges. These remain visible limitations; a passing suite is not a guarantee of error-free deployment.

The tests use temporary synthetic fixtures. The real-input check reads/hashes only the small existing Copernicus file and validates its manifest/request; it does not reopen its scientific fields, retest provider access or resolve the audit's scientific findings. No provider credentials were used. The 9.2 GB V2, Argo and glider files were not rehashed in this checkpoint; no task action wrote them.

## Not performed

No new acquisition, raw-input rewrite, model processor/CLI/storage service, real model output, readiness promotion, pressure conversion, adjusted-data change, scientific matching, metrics, HTTP route, background job, Git operation or frontend implementation. No browser/network performance claim is made. The private failed-acquisition staging residue from Part 4 remains outside this task.

## Next checkpoint — permission required

**5.3: model preparation implementation.** Implement the documented local preflight, bounded native-field extraction, typed metadata snapshot encoding, immutable publication/reuse and readback tests; then prepare the existing small Copernicus selection if validation succeeds. Do not silently resolve metadata ambiguities or enable comparison/serving to complete that step.
