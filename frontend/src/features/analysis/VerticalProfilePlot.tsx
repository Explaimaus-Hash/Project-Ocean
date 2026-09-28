"use client";
import { ScientificPlotShell, scientificAxis } from "./ScientificPlotShell";
import type { PlotMetadata } from "./plotModel";
export function VerticalProfilePlot({
  metadata,
  coordinates,
  values,
  verticalUnit,
}: {
  metadata: PlotMetadata;
  coordinates: (number | null)[];
  values: (number | null)[];
  verticalUnit: "m" | "dbar";
}) {
  if (values.length !== coordinates.length || values.length > 10000)
    return <p role="status">Profile exceeds the supported shape or size.</p>;
  const axis = verticalUnit === "m" ? "Depth (m)" : "Pressure (dbar)";
  return (
    <ScientificPlotShell
      metadata={metadata}
      traces={[
        {
          type: "scatter",
          name: `${metadata.quantity} (${metadata.units})`,
          x: values,
          y: coordinates,
          connectgaps: false,
          mode: coordinates.some((v) => v === null)
            ? "markers"
            : "lines+markers",
          line: { color: "#59d9e8", width: 1.5, shape: "linear" },
          marker: { size: 5 },
          hovertemplate: `%{x} ${metadata.units}<br>%{y} ${verticalUnit}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: {
          ...scientificAxis,
          title: { text: `${metadata.quantity} (${metadata.units})` },
        },
        yaxis: {
          ...scientificAxis,
          title: { text: axis },
          autorange: "reversed",
        },
        hovermode: "closest",
      }}
      csv={{
        headers: [
          metadata.quantity,
          "units",
          axis,
          "source",
          "dataset",
          "mode",
        ],
        rows: values.map((value, i) => [
          value,
          metadata.units,
          coordinates[i],
          metadata.source,
          metadata.dataset,
          metadata.mode,
        ]),
      }}
    />
  );
}
