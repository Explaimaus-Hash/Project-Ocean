import { scientificAxis } from "@/features/analysis/ScientificPlotShell";
import { residual, type MatchedPair } from "./comparisonModel";
export const modelColor = "#59d9e8",
  observationColor = "#ffba55";
export const axis = (title: string) => ({
  ...scientificAxis,
  title: { text: title },
});
export const details = (pairs: MatchedPair[]) =>
  pairs.map((p) => [
    p.model,
    p.observation,
    residual(p),
    p.latitude,
    p.longitude,
    p.observationDepth,
    p.observationTime,
    p.id,
    p.units,
    p.verticalUnit,
    p.modelTime,
  ]);
export const hover =
  "Model: %{customdata[0]} %{customdata[8]}<br>Observation: %{customdata[1]} %{customdata[8]}<br>Model - Observation: %{customdata[2]:.3f} %{customdata[8]}<br>Lat: %{customdata[3]} / Lon: %{customdata[4]}<br>Vertical: %{customdata[5]} %{customdata[9]}<br>Observation time: %{customdata[6]}<br>Model time: %{customdata[10]}<br>%{customdata[7]}<extra></extra>";
