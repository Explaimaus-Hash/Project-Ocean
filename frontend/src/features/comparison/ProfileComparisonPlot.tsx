import { ScientificPlotShell } from "@/features/analysis/ScientificPlotShell";
import {
  validPairs,
  plotMetadata,
  type ComparisonPlotProps,
} from "./comparisonModel";
import { axis, modelColor, observationColor } from "./comparisonPlot";
export function ProfileComparisonPlot({
  result,
  selected,
}: ComparisonPlotProps) {
  const pairs = validPairs(result)
    .filter(
      (p) =>
        p.modelTime === selected.modelTime &&
        p.verticalUnit === selected.verticalUnit &&
        p.latitude === selected.latitude &&
        p.longitude === selected.longitude,
    )
    .sort((a, b) => (a.modelDepth ?? 0) - (b.modelDepth ?? 0));
  const vertical =
    selected.verticalUnit === "m" ? "Depth (m)" : "Pressure (dbar)";
  return (
    <ScientificPlotShell
      metadata={plotMetadata(
        result,
        "Model vs Observation profile",
        `${selected.modelTime} · ${selected.latitude}°, ${selected.longitude}°`,
      )}
      traces={[
        {
          type: "scatter",
          name: "Model",
          x: pairs.map((p) => p.model),
          y: pairs.map((p) => p.modelDepth),
          mode: "lines",
          connectgaps: false,
          line: { color: modelColor, width: 2 },
          hovertemplate: `Model: %{x} ${result.units}<br>%{y} ${selected.verticalUnit}<extra></extra>`,
        },
        {
          type: "scatter",
          name: "Observation",
          x: pairs.map((p) => p.observation),
          y: pairs.map((p) => p.observationDepth),
          mode: "markers",
          marker: { color: observationColor, size: 8, symbol: "diamond" },
          hovertemplate: `Observation: %{x} ${result.units}<br>%{y} ${selected.verticalUnit}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: axis(`${result.quantity} (${result.units})`),
        yaxis: { ...axis(vertical), autorange: "reversed" },
        hovermode: "closest",
      }}
    />
  );
}
