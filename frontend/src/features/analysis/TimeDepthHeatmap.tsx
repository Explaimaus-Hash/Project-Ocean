"use client";
import { ScientificPlotShell, scientificAxis } from "./ScientificPlotShell";
import type { PlotMetadata } from "./plotModel";
export interface TimeDepthData {
  timestamps: string[];
  depths: number[];
  verticalUnit: "m" | "dbar";
  values: (number | null)[][];
}
export function TimeDepthHeatmap({
  data,
  metadata,
}: {
  data?: TimeDepthData;
  metadata: PlotMetadata;
}) {
  if (!data)
    return (
      <p className="analysis-unavailable" role="status">
        Time–depth not available: a verified backend field is required.
      </p>
    );
  if (
    data.depths.length * data.timestamps.length > 65536 ||
    data.values.length !== data.depths.length ||
    data.values.some((row) => row.length !== data.timestamps.length)
  )
    return (
      <p role="status">Time–depth field exceeds the supported shape or size.</p>
    );
  const axis = data.verticalUnit === "m" ? "Depth (m)" : "Pressure (dbar)";
  return (
    <ScientificPlotShell
      metadata={metadata}
      traces={[
        {
          type: "heatmap",
          name: metadata.quantity,
          x: data.timestamps,
          y: data.depths,
          z: data.values,
          connectgaps: false,
          hoverongaps: false,
          zsmooth: false,
          colorscale: "Viridis",
          colorbar: { title: { text: metadata.units } },
          hovertemplate: `%{x|%Y-%m-%d %H:%M UTC}<br>%{y} ${data.verticalUnit}<br>%{z} ${metadata.units}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: {
          ...scientificAxis,
          title: { text: "Time (UTC)" },
          type: "date",
        },
        yaxis: {
          ...scientificAxis,
          title: { text: axis },
          autorange: "reversed",
        },
        hovermode: "closest",
      }}
    />
  );
}
