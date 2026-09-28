import { ScientificPlotShell } from "@/features/analysis/ScientificPlotShell";
import {
  validPairs,
  plotMetadata,
  type ComparisonPlotProps,
} from "./comparisonModel";
import { axis, modelColor, observationColor } from "./comparisonPlot";
export function PairedSeriesPlot({ result, selected }: ComparisonPlotProps) {
  const pairs = validPairs(result).filter(
    (p) =>
      p.observationDepth === selected.observationDepth &&
      p.verticalUnit === selected.verticalUnit &&
      p.latitude === selected.latitude &&
      p.longitude === selected.longitude,
  );
  return (
    <ScientificPlotShell
      metadata={plotMetadata(
        result,
        "Paired time series",
        `${selected.observationDepth} ${selected.verticalUnit} · ${selected.latitude}°, ${selected.longitude}°`,
      )}
      traces={[
        {
          type: "scatter",
          name: "Model",
          x: pairs.map((p) => p.modelTime),
          y: pairs.map((p) => p.model),
          mode: "lines+markers",
          connectgaps: false,
          line: { color: modelColor, width: 1.5 },
          hovertemplate: `%{x}<br>Model: %{y} ${result.units}<extra></extra>`,
        },
        {
          type: "scatter",
          name: "Observation",
          x: pairs.map((p) => p.observationTime),
          y: pairs.map((p) => p.observation),
          mode: "markers",
          marker: { color: observationColor, size: 8, symbol: "diamond" },
          hovertemplate: `%{x}<br>Observation: %{y} ${result.units}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: { ...axis("Time (UTC)"), type: "date", nticks: 4 },
        yaxis: axis(`${result.quantity} (${result.units})`),
      }}
    >
      <p className="field-note">
        Observation markers are discrete. Unmatched observations are excluded,
        never joined into continuous coverage.
      </p>
    </ScientificPlotShell>
  );
}
