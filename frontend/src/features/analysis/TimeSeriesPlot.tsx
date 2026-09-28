"use client";
import type { Timeseries } from "@/lib/api/types";
import { ScientificPlotShell, scientificAxis } from "./ScientificPlotShell";
import type { PlotMetadata } from "./plotModel";
export function TimeSeriesPlot({
  data,
  metadata,
  requested,
}: {
  data: Timeseries;
  metadata: PlotMetadata;
  requested: { longitude: number; latitude: number };
}) {
  if (!data.timestamps.length)
    return (
      <p className="analysis-unavailable" role="status">
        No time series samples returned for this selection.
      </p>
    );
  return (
    <ScientificPlotShell
      metadata={metadata}
      traces={[
        {
          type: "scatter",
          name: `${metadata.quantity} (${data.units})`,
          x: data.timestamps,
          y: data.values,
          mode: "lines+markers",
          connectgaps: false,
          line: { color: "#59d9e8", width: 1.5, shape: "linear" },
          marker: { size: 5, color: "#59d9e8" },
          hovertemplate: `%{x|%Y-%m-%d %H:%M UTC}<br>${metadata.quantity}: %{y:.4f} ${data.units}<extra></extra>`,
        },
      ]}
      layout={{
        xaxis: {
          ...scientificAxis,
          title: { text: "Time (UTC)" },
          type: "date",
          nticks: 4,
        },
        yaxis: {
          ...scientificAxis,
          title: { text: `${data.variable} (${data.units})`, standoff: 14 },
        },
      }}
      csv={{
        headers: [
          "timestamp_utc",
          metadata.quantity,
          "units",
          "source",
          "dataset",
          "product_id",
          "mode",
          "requested_longitude",
          "requested_latitude",
          "actual_longitude",
          "actual_latitude",
          "distance_km",
        ],
        rows: data.timestamps.map((time, i) => [
          time,
          data.values[i],
          data.units,
          metadata.source,
          metadata.dataset,
          data.product_id,
          data.mode,
          requested.longitude,
          requested.latitude,
          data.longitude,
          data.latitude,
          data.distance_km,
        ]),
      }}
    >
      <p className="field-note">
        {data.timestamps.length} API timestamps ·{" "}
        {data.values.filter((v) => v === null).length} missing samples. Missing
        samples are gaps, never zeros.
      </p>
      <details>
        <summary>Accessible plotted values</summary>
        <table>
          <thead>
            <tr>
              <th>Time (UTC)</th>
              <th>
                {metadata.quantity} ({data.units})
              </th>
            </tr>
          </thead>
          <tbody>
            {data.timestamps.map((time, i) => (
              <tr key={time}>
                <td>{time}</td>
                <td>{data.values[i] ?? "Missing"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </ScientificPlotShell>
  );
}
