import { ScientificPlotShell } from "@/features/analysis/ScientificPlotShell";
import {
  validPairs,
  plotMetadata,
  type ComparisonPlotProps,
} from "./comparisonModel";
import {
  axis,
  modelColor,
  observationColor,
  details,
  hover,
} from "./comparisonPlot";
export function ScatterComparisonPlot({
  result,
  selected,
}: ComparisonPlotProps) {
  const pairs = validPairs(result),
    values = pairs.flatMap((p) => [p.model!, p.observation!]);
  const min = Math.min(...values) - 0.5,
    max = Math.max(...values) + 0.5;
  return (
    <ScientificPlotShell
      metadata={plotMetadata(
        result,
        "Model vs Observation scatter",
        "All eligible matched pairs in the selected scope",
      )}
      traces={[
        {
          type: "scatter",
          name: "1:1 reference",
          x: [min, max],
          y: [min, max],
          mode: "lines",
          line: { color: "#a2b2c2", dash: "dot", width: 1 },
          hoverinfo: "skip",
        },
        {
          type: "scatter",
          name: `Matched ${result.quantity} (${result.units})`,
          x: pairs.map((p) => p.observation),
          y: pairs.map((p) => p.model),
          customdata: details(pairs),
          mode: "markers",
          marker: {
            color: pairs.map((p) =>
              p.id === selected.id ? observationColor : modelColor,
            ),
            size: pairs.map((p) => (p.id === selected.id ? 11 : 6)),
          },
          hovertemplate: hover,
        },
      ]}
      layout={{
        xaxis: {
          ...axis(`Observation ${result.quantity} (${result.units})`),
          range: [min, max],
          constrain: "domain",
        },
        yaxis: {
          ...axis(`Model ${result.quantity} (${result.units})`),
          range: [min, max],
          scaleanchor: "x",
          scaleratio: 1,
        },
        hovermode: "closest",
      }}
    />
  );
}
