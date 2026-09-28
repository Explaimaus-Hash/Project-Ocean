# Backend measurement checkpoint — 2026-09-10

Latest resource change (2026-09-28): [all-date SST/SSS archive](BIO_ROMS_ARCHIVE.md) uses 120 four-date products plus the preserved original product. Only catalogue capacity increases to 128; per-product 8M values/128MiB files and API frame/response limits remain unchanged. Preparation now uses bounded spatial tiles across a small selected time batch to avoid repeated decompression of 80-time source chunks. Historical frame-by-frame preparation wording below is superseded by this implementation. Functional all-date verification is not an all-source/concurrent-load or GPU performance guarantee; see the archive milestone for actual completion evidence.

## Latest local acceptance measurement — 2026-09-27 / 5.10

Reference: Intel Core i9-14900HX (24 cores / 32 logical processors), 16,869,548,032 bytes physical memory, Windows 11 build 26200, Python 3.12.10. Existing prepared selections; no cache clearing or throttling, sequential requests, nearest-rank p95 from 30 repetitions after initial checks. [Complete acceptance scope](MILESTONE_5_10.md).

| Selection | In-process p95 | Persistent loopback HTTP p95 | JSON body bytes |
| --- | --- | --- | --- |
| BIO-ROMS SST preview, first prepared frame, 95 × 136 | 32.18 ms | 35.53 ms | 170,898 |
| Argo collection, all 14 native points | Not remeasured in-process in 5.10 | 15.51 ms | 18,537 |
| Exploratory comparison, all 14 evaluated rows | 8.01 ms | 10.14 ms | 15,938 |

Fresh authenticated comparison replay took 1.758 s; this is operator verification of existing inputs, not first preparation or HTTP work. The surface verifier matched six raw values and reported a 126,668,800-byte process peak working set, not an API/preparation-only memory measurement. Its first preview request took 169.45 ms, not cold-disk latency. Repeated bodies were identical. Temporary loopback server was stopped after checking all 13 application paths and expected errors.

No browser/network-deployment/large-selection/concurrency/GPU targets are established. A fast 14-row comparison does not establish 5,000-row worst-case paging performance. Historical measurements below remain scoped to their dates; this is not a controlled speedup comparison.

This is a local backend measurement, not a browser/globe benchmark or production service-level guarantee. Reference runtime: Windows 11 (10.0.26200), Python 3.12.10, the project `ocean-env` pinned stack. Requests used FastAPI TestClient in one process; no network transfer, imagery, chart rendering, or GPU work was timed. Filesystem cache was not deliberately cleared, so the first request is not a cold-disk measurement.

## Selection and results

Real V2 product: `p_7c8210052d41d41259724e2d`, SST/SSS, January–March 2019, requested lon30–120/lat-30–30. Scientific shape `3 × 756 × 1081`; actual source timestamps January29, February28, March30. Source chunking for these fields is `80 × 126 × 181` float64; reading a small logical selection may decompress more source bytes than that selection contains.

| Measured item | Result | Interpretation |
| --- | --- | --- |
| Preserved raw file | 9,248,080,750 bytes | Remains on disk; not sent to browser. |
| Compressed scientific subset | 10,093,402 bytes | Two variables, three full-native-resolution frames each. |
| Separate preview file | 233,615 bytes | Both variables/times at source-cell stride8. |
| SST single preview response | 170,898 bytes | Full JSON metadata and values; below 2 MiB transfer ceiling. |
| Preview shape | 95 × 136 | 12,920 cells; 7,440 valid SST cells in first frame. |
| First preview request in process | 0.2403 seconds | Includes first-use work, not cold disk/network/browser. |
| Warm preview p95 | 0.0422 seconds | Nearest-rank p95 from 30 repeated local in-process requests. |
| Verification-process peak working set | 120,983,552 bytes (~115.4 MiB) | Whole verification process including API imports and bounded raw sample check; **not preparation-job peak memory**. |
| Raw point samples compared | 6, exact match | Three finite SST and three finite SSS values; not exhaustive validation. |

The first real preparation duration and peak process memory were not captured reliably, so neither is claimed measured. An idempotent repeat checks/reuses existing products and must not be reported as first-preparation speed. These measurements do not justify a guarantee that every larger input or selection will be fast.

## Reproduce

After installing development requirements and preparing the product:

```powershell
.\ocean-env\Scripts\python.exe -m scripts.verify_product p_7c8210052d41d41259724e2d --check-raw
```

The command does not modify data. It exercises actual typed API routes, compares a native point series against bounded raw reads, confirms oversized scientific requests are rejected, checks 30 repeat previews, and prints measurements. Repeat values naturally vary with system load/cache state.

Source verification and preparation are explicit operator work; HTTP never opens raw data. Resource limits are enforced in [config/performance.yaml](../config/performance.yaml) and described in [MILESTONE_3.md](MILESTONE_3.md). One per-process nonblocking lock serializes NetCDF reads; concurrent scientific requests can return `503 busy` rather than queue unbounded work. This policy is not a load-tested multiworker deployment.

## Part-4 regression and observation measurements

After installing source clients and adding observation APIs, repeated the same real V2 verification: 6/6 raw sample matches, unchanged scientific/preview file sizes, first in-process preview 0.2502 seconds and 30-request warm p95 0.0392 seconds. Preview JSON remains 170,898 bytes. Verification-process peak working set was 121,958,400 bytes; this is not preparation memory. Timing changes between runs are not a controlled comparative benchmark.

Real Argo collection `o_c645f248f801845378f0fdaf` contains 14 native scientific points with three core variables, raw/adjusted/QC/error provenance. Its private JSON is 21,802 bytes; the five-sample API page is 6,848 bytes and full 14-sample page 18,537 bytes. Thirty repeated full-page requests in FastAPI TestClient measured nearest-rank p95 0.0171 seconds. Source/selection and exact raw-value checks are in [MILESTONE_4.md](MILESTONE_4.md). Acquisition/preparation time was not benchmarked; a small page does not establish performance for the 5,000-sample/16 MiB collection ceilings.

Observation HTTP access hashes/parses the bounded private collection before paging; it does not read raw NetCDF or acquire data. No hard process-memory cap, cold-disk, browser rendering or many-user load has been measured. Source request ceilings live in the typed acquisition/observation contracts, while `config/performance.yaml` continues to govern the surface pipeline.

## Remaining unmeasured scope

Browser feedback/globe startup/frame rate, cold/warm network transfers, animation prefetch/cancellation, sustained concurrency, GPU/decoded-browser memory, large preparation-job peak RSS/duration and deployment storage throughput. Keep the architecture's original experience targets as goals; do not mark them achieved based on these API-only measurements. Measure and tune them in their authorized implementation parts.

## Part-5.3 native-model storage checkpoint

The separately approved local Copernicus selection now has private model product `m_35e4c0ab33c1469a334ca837`: four native fields at 2×8×13×13 samples. Measured output sizes are 66,533 bytes for scientific NetCDF, 7,043 bytes for typed source metadata and 4,939 bytes for the manifest. Every decoded field value matched the small acquired input; repeat preparation preserved output hashes/stats. [Verification](MILESTONE_5_3.md).

These are disk sizes, not HTTP payloads or browser measurements. No model-serving API, preview or frontend exists for this product. Operator preparation/reuse performs input/output hashing and selected-slab readback; it is not an interactive latency claim. Earlier surface API measurements above keep their original scope.
