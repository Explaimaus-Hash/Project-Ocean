# Part 5.7 — scientific-support evidence checkpoint

Checked on 2026-09-16. This continuation inspected official public metadata/documentation and reran local verification. It does not enable real matching or complete 5.7. No application code, policy thresholds, dataset bytes, credentials, dependency or API changed. No scientific arrays were downloaded. The next acquisition described below requires permission.

Historical checkpoint: acquisition was subsequently approved and completed on2026-09-17; read [the static acquisition milestone](MILESTONE_5_7_STATIC_ACQUISITION.md) for actual code/data/tests. The no-download statements below describe this earlier evidence-only session, not the current state.

## Findings and remaining gates

| Requirement | Evidence checked | Result for the saved inputs |
| --- | --- | --- |
| Daily intervals | Official daily version202311 catalogue, remote Zarr metadata and saved source metadata | Midnight labels and daily sampling confirmed; no bounds or exact label-to-interval rule found. Keep unresolved. |
| Depth units/order | Catalogue depth list versus the eight saved model depths | Bathymetry catalogue depths match exactly after the documented sign/order transformation. This is metadata compatibility, not an inspected static dataset or shared vertical datum. |
| Wet mask/bottom | Version202311 static bathymetry catalogue | Correct candidate source identified; mask/bathymetry values are not yet acquired or verified. |
| Coastline connectivity | No local supporting mask/grid-cell geometry | Unresolved. A finite model field, matching axis list or same nearest centre is insufficient. |
| Vertical reference | Saved depth attributes and remote bathymetry definition | Metres positive down alone do not establish compatibility with pressure-derived observation depth. Bathymetry is described relative to the geoid; do not silently identify it with sea-surface-relative depth. |
| Tolerances | Existing comparison policy | All three limits remain null/unreviewed. Metadata discovery does not justify numeric limits. |

The [PUM issue1.7, sections1 and2(c)](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf) describes full-day means centred at noon, but the acquired ARCO/subset labels are midnight. It also describes the distributed regular grid as interpolated from the model's computational grid. Here **native** means unchanged samples of the distributed product, not the original NEMO computational mesh. Neither statement authorizes shifting timestamps or reconstructing missing time bounds.

The [daily version202311 catalogue](https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/GLOBAL_MULTIYEAR_PHY_001_030/cmems_mod_glo_phy_my_0.083deg_P1D-m_202311/dataset.stac.json) identifies the inspected remote asset. Its `time/.zattrs` declares Gregorian hours since 1950, without bounds. Its `thetao` attributes still do not establish ITS-90/reference-pressure compatibility. No inspected support metadata resolves these gates. Do not claim that such evidence cannot exist elsewhere; a version-specific provider clarification is still needed.

## Exact static source identified

The [official product catalogue](https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/GLOBAL_MULTIYEAR_PHY_001_030/product.stac.json) links separate version202311 bathymetry, coordinates and MDT parts. For the next acquisition, the candidate is:

- Dataset: `cmems_mod_glo_phy_my_0.083deg_static`, version `202311`, part `bathy`.
- [Bathymetry catalogue item](https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/GLOBAL_MULTIYEAR_PHY_001_030/cmems_mod_glo_phy_my_0.083deg_static_202311--ext--bathy/dataset.stac.json).
- Variables: `mask(elevation,latitude,longitude)`, `deptho(latitude,longitude)` and `deptho_lev(latitude,longitude)`. Mask metadata declares 1=sea/0=land; bottom-level numbering still needs verification, not an assumed zero-/one-based conversion.
- The undownsampled `static` asset advertises 50×2041×4320 mask elements. It also advertises downsampled assets: those must not be used for scientific matching.
- An HTTP HEAD request, without reading the body, reports the original `GLO-MFC_001_030_mask_bathy.nc` as **511,420,508 bytes**. This is not a downloaded or checksum-verified file. Its multipart ETag is not an MD5 verification.

All 50 bathymetry catalogue depth values equal the daily catalogue values; the eight local prepared depths match their shallowest eight values. Horizontal catalogue descriptions also agree, but actual coordinate-array equality must still be checked after acquisition.

The [separate coordinates item](https://s3.waw3-1.cloudferro.com/mdl-metadata/metadata/GLOBAL_MULTIYEAR_PHY_001_030/cmems_mod_glo_phy_my_0.083deg_static_202311--ext--coords/dataset.stac.json) differs at **33 of 50** advertised depths (maximum absolute difference 0.00048828125 m). This may be a representation difference; its cause was not established. Do not round, nearest-join or override coordinates to hide it. It is not required for the first mask/bathymetry acquisition. Its original file HEAD size was 374,210 bytes, not a verified local dataset.

## Proposed next bounded acquisition — NOT executed

Acquire only `mask`, `deptho`, `deptho_lev` for **65–66E, 1S–0N**, preserving all 50 depth levels for bottom/column checks. The existing science selection remains unchanged at eight levels. Before field transfer, verify actual coordinate coverage/alignment and source chunks, and enforce transfer/decompression/output limits. A small requested region does not guarantee equally small network reads: advertised mask chunks are 1×512×2048; each uncompressed int8 chunk is 1 MiB.

Use the undownsampled static subset service if supported by the installed Toolbox and the inspected source. Do not silently fall back to the approximately511MB global file. Exact transfer size, SDK support, output size and authentication requirements remain untested. The current daily/monthly acquisition adapter does not yet accept this static dataset/part; add an explicit bounded static path, not a fabricated existing command or a relaxed daily-data contract. Keep originals and source/version/part/transform/hash provenance separate from prepared support. Nothing runs at startup or through HTTP.

After acquisition, verify binary mask values, shape/order, exact horizontal/depth alignment, missing values, bottom-level convention and consistency with bathymetry. Define/test candidate-bound connectivity at the distributed grid's supported resolution; do not claim a sub-grid coastline certificate. The static file alone cannot resolve daily intervals, vertical-datum compatibility, temperature semantics or reviewed tolerances. Follow [MATCHING_POLICY.md](MATCHING_POLICY.md) without promoting flags by hand.

## Provider clarification draft — not sent

Historical heading retained for links: the draft below was subsequently approved and sent by Gmail on **2026-09-25**. See the [verified send record](MILESTONE_5_7_EXECUTION.md#email-sent-and-verified--2026-09-25). Do not resend it; a substantive provider reply remains pending.

For product `GLOBAL_MULTIYEAR_PHY_001_030`, daily dataset `cmems_mod_glo_phy_my_0.083deg_P1D-m`, version202311, Toolbox2.4.1 preserves 2019-01-29/30 at00:00UTC without time bounds. Please confirm the exact UTC averaging interval represented by each label and whether ARCO changes the original file's time encoding. Please also identify the reference surface of the distributed depth coordinate and its relation to sea-pressure-derived depths and geoid-referenced `deptho`; confirm the temperature scale/reference pressure of `thetao` and the indexing convention of `deptho_lev`. A published version-specific reference is preferred.

At this original evidence checkpoint, sending the request was a separate user decision and no message, account login or support ticket had been submitted. The later authorized email is recorded above; no provider ticket has been verified.

## Reproducibility and checks

Catalogue/Zarr metadata was read over verified HTTPS with 20-second-or-shorter request timeouts and a 1 MiB body cap; array chunks and native NetCDF bodies were not requested. These are fingerprints of the metadata bytes observed, not permanent version pins or local saved artifacts:

| Metadata document | Bytes | SHA256 |
| --- | --- | --- |
| Daily version202311 STAC | 33,650 | `537bbda9af5760a64d715e354677e7cc13f128d1c827dd75951f3f1a9cd64188` |
| Static bathy STAC | 15,750 | `1807de98b5ca212ca9f9f1b82f110aadd75b58be39e5705269571ac5aec3ef90` |
| Static coordinates STAC | 15,648 | `4adf1687934182acb34217ca8d0f9c721928db68694e1cc624c53f2cf3462fcb` |
| Daily timeChunked `.zmetadata` | 17,376 | `8f1798367c2fa7cccad3432bb0cf3c3c649f3f6e0cdd7dcf88de1123d7b02b36` |
| Static bathy `.zmetadata` | 4,551 | `de9bab08b9cd447510446671f3138a3bbbc4571c16f4eaad678ceb8747de2368` |

The catalogue's daily `timeChunked` and bathymetry `static` asset URLs locate the inspected `.zmetadata` documents. No support claim is promoted automatically from these fingerprints.

The existing real salinity audit was rerun: exit3, no stderr,17,326-byte JSON,2,704 finite field values,14 adjusted central depths,12 evaluated pressure-error ranges, nine blockers, zero pairs and overlap not evaluated. Its seven-file before/after identity checks passed. Targeted policy/reader/local-audit/health/startup regression: **143 passed,69 warnings in25.88seconds**. Warnings include existing NumPy/xarray/Starlette deprecations and provider-plugin discovery denied by offline fixtures. No full-suite rerun was needed for this documentation-only checkpoint;784passed/4skipped remains the historical full result in [the reader milestone](MILESTONE_5_7_READER.md), not a new run.

All 26 root/docs Markdown files passed local-link, fenced-block and final-newline checks. No new Python module or test was added; this checkpoint changes documentation only.

Next permission: implement and attempt the bounded static acquisition/validation above. Real matching remains disabled; 5.8 metrics, 5.9 API, 5.10 end-to-end and frontend are not started.
