import type {
  ComparisonResult,
  MatchedPair,
  MatchStatus,
} from "./comparisonModel";
/** Authored UI fixture only. No source dataset or display raster is matched here. */
export function createComparisonFixture(): ComparisonResult {
  const pairs: MatchedPair[] = [];
  for (let day = 1; day <= 3; day++)
    for (let level = 0; level < 4; level++) {
      const observation = 26 - level * 2 + day * 0.1;
      pairs.push({
        id: `illustration-${day}-${level}`,
        modelSource: "INCOIS · illustrative",
        observationSource: "Argo · illustrative",
        variable: "TEMP",
        units: "°C",
        observation,
        model: observation + (level % 2 === 0 ? 0.2 : -0.2),
        modelTime: `2020-01-0${day}T00:00:00Z`,
        observationTime: `2020-01-0${day}T00:00:00Z`,
        timeOffsetSeconds: 0,
        horizontalOffsetKm: 0,
        modelDepth: level * 50,
        observationDepth: level * 50,
        depthOffset: 0,
        verticalUnit: "dbar",
        latitude: 0,
        longitude: 65,
        qc: "Illustrative accepted flag",
        status: "valid",
      });
    }
  const reasons: MatchStatus[] = [
    "qc_rejected",
    "no_temporal_overlap",
    "no_depth_support",
    "quantity_incompatible",
  ];
  for (const [i, status] of reasons.entries())
    pairs.push({
      ...pairs[0],
      id: `excluded-${i}`,
      model: null,
      observation: null,
      modelDepth: null,
      observationDepth: null,
      depthOffset: null,
      timeOffsetSeconds: null,
      horizontalOffsetKm: null,
      qc:
        status === "qc_rejected"
          ? "Illustrative rejected flag"
          : "Not evaluated",
      status,
    });
  return {
    mode: "synthetic",
    quantity: "Temperature",
    units: "°C",
    pairs,
    matching: "illustrative",
    compatible: true,
    regionOverlap: true,
    timeOverlap: true,
    depthSupport: true,
    metrics: { origin: "fixture", validPairs: 12, meanBias: 0, rmse: 0.2 },
    exclusions: reasons.map((reason) => ({ reason, count: 1 })),
    provenance:
      "Illustrative / Demo data. Authored development fixture, not provider data, operational validation, a BIO-ROMS water column or an authoritative matching policy.",
  };
}
