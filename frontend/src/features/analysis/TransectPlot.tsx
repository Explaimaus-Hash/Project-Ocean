"use client";
import { ScientificPlotShell, scientificAxis } from "./ScientificPlotShell";
import type { PlotMetadata } from "./plotModel";
export interface TransectData {
  distancesKm: number[];
  depths: number[];
  verticalUnit: "m" | "dbar";
  values: (number | null)[][];
}
export function TransectPlot({
  data,
  metadata,
}: {
  data?: TransectData;
  metadata: PlotMetadata;
}) {
  if (!data)
    return (
      <p className="analysis-unavailable" role="status">
        Transect not available: a suitable backend source is required.
      </p>
    );
  if (
    data.depths.length * data.distancesKm.length > 65536 ||
    data.values.length !== data.depths.length ||
    data.values.some((row) => row.length !== data.distancesKm.length)
  )
    return (
      <p role="status">Transect field exceeds the supported shape or size.</p>
    );
  const axis = data.verticalUnit === "m" ? "Depth (m)" : "Pressure (dbar)";
  return (
    <ScientificPlotShell
      metadata={metadata}
      traces={[
        {
          type: "heatmap",
          name: metadata.quantity,
          x: data.distancesKm,
          y: data.depths,
          z: data.values,
          connectgaps: false,
          hoverongaps: false,
          zsmooth: false,
          colorscale: "Viridis",
          colorbar: { title: { text: metadata.units } },
          hovertemplate: `%{x} km along path<br>%{y} ${data.verticalUnit}<br>%{z} ${metadata.units}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: {
          ...scientificAxis,
          title: { text: "Distance along transect (km)" },
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
