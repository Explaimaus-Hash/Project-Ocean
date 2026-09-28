import type { PlotMetadata } from "@/features/analysis/plotModel";
export type MatchStatus =
  | "valid"
  | "qc_rejected"
  | "no_temporal_overlap"
  | "no_depth_support"
  | "quantity_incompatible";
export interface MatchedPair {
  id: string;
  modelSource: string;
  observationSource: string;
  variable: string;
  units: string;
  model: number | null;
  observation: number | null;
  modelTime: string;
  observationTime: string;
  timeOffsetSeconds: number | null;
  horizontalOffsetKm: number | null;
  modelDepth: number | null;
  observationDepth: number | null;
  depthOffset: number | null;
  verticalUnit: "m" | "dbar";
  latitude: number;
  longitude: number;
  qc: string;
  status: MatchStatus;
}
/** Internal presentation model, NOT an invented backend wire contract. Real adapter is absent. */
export interface ComparisonResult {
  mode: "synthetic" | "real";
  provenance: string;
  quantity: string;
  units: string;
  pairs: MatchedPair[];
  matching: "illustrative" | "verified" | "blocked";
  compatible: boolean;
  regionOverlap: boolean;
  timeOverlap: boolean;
  depthSupport: boolean;
  metrics?: {
    origin: "fixture" | "backend";
    validPairs: number;
    meanBias: number;
    rmse: number;
    correlation?: number;
  };
  exclusions: { reason: MatchStatus; count: number }[];
}
export interface ComparisonSelection {
  model: "INCOIS" | "Copernicus";
  observation: "Argo" | "Glider";
  variable: string;
  region: string;
  start: string;
  end: string;
  verticalRange: string;
}
export const initialComparison: ComparisonSelection = {
  model: "INCOIS",
  observation: "Argo",
  variable: "",
  region: "project",
  start: "",
  end: "",
  verticalRange: "",
};
export const unavailableMessage =
  "Scientific comparison service is not available for this selection";
export function validPairs(result?: ComparisonResult): MatchedPair[] {
  if (
    !result ||
    !result.compatible ||
    !result.regionOverlap ||
    !result.timeOverlap ||
    !result.depthSupport ||
    result.matching === "blocked" ||
    (result.mode === "real" && result.matching !== "verified")
  )
    return [];
  return result.pairs.filter(
    (p) =>
      p.status === "valid" &&
      Number.isFinite(p.model) &&
      Number.isFinite(p.observation) &&
      p.units === result.units,
  );
}
export function trustedMetrics(result?: ComparisonResult) {
  if (!result || !validPairs(result).length || !result.metrics)
    return undefined;
  const m = result.metrics;
  if (
    m.validPairs !== validPairs(result).length ||
    !Number.isInteger(m.validPairs) ||
    m.validPairs <= 0 ||
    !Number.isFinite(m.meanBias) ||
    !Number.isFinite(m.rmse) ||
    m.rmse < 0 ||
    (m.correlation !== undefined &&
      (!Number.isFinite(m.correlation) || Math.abs(m.correlation) > 1))
  )
    return undefined;
  if (
    result.mode === "real" &&
    (result.matching !== "verified" || m.origin !== "backend")
  )
    return undefined;
  if (result.mode === "synthetic" && m.origin !== "fixture") return undefined;
  return m;
}
export function residual(pair: MatchedPair) {
  return pair.model !== null && pair.observation !== null
    ? pair.model - pair.observation
    : null;
}
export function plotMetadata(
  result: ComparisonResult,
  title: string,
  selection: string,
): PlotMetadata {
  const pairs = validPairs(result);
  const times = pairs.flatMap((p) => [p.modelTime, p.observationTime]).sort();
  return {
    title,
    source: `${pairs[0]?.modelSource ?? "Model"} / ${pairs[0]?.observationSource ?? "Observation"}`,
    dataset:
      result.mode === "synthetic"
        ? "Comparison UI fixture"
        : "Verified matched pairs",
    quantity: result.quantity,
    units: result.units,
    selection,
    timeRange: times.length
      ? `${times[0]} → ${times.at(-1)}`
      : "No matched timestamps",
    mode: result.mode,
    note:
      result.provenance +
      " Residual = Model - Observation. No frontend scientific matching. No pressure/depth conversion.",
  };
}
export type ComparisonPlotProps = {
  result: ComparisonResult;
  selected: MatchedPair;
};
