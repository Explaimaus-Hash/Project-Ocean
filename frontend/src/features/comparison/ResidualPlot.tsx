"use client";
import { useState } from "react";
import { ScientificPlotShell } from "@/features/analysis/ScientificPlotShell";
import {
  validPairs,
  residual,
  plotMetadata,
  type ComparisonPlotProps,
} from "./comparisonModel";
import { axis, details, hover } from "./comparisonPlot";
export function ResidualPlot({ result, selected }: ComparisonPlotProps) {
  const [mode, setMode] = useState("depth");
  const pairs = validPairs(result).filter((p) =>
    mode === "depth"
      ? p.modelTime === selected.modelTime
      : p.observationDepth === selected.observationDepth,
  );
  const r = pairs.map((p) => residual(p)!);
  const bound = Math.max(...r.map(Math.abs), 0.001);
  return (
    <div>
      <label className="residual-control">
        Residual coordinate
        <select
          aria-label="Residual coordinate"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="depth">Depth / pressure</option>
          <option value="time">Time</option>
        </select>
      </label>
      <ScientificPlotShell
        metadata={plotMetadata(
          result,
          "Residual · Model - Observation",
          mode === "depth"
            ? selected.modelTime
            : `${selected.observationDepth} ${selected.verticalUnit}`,
        )}
        traces={[
          {
            type: "scatter",
            name: `Model - Observation (${result.units})`,
            x: mode === "depth" ? r : pairs.map((p) => p.observationTime),
            y: mode === "depth" ? pairs.map((p) => p.observationDepth) : r,
            mode: "markers",
            customdata: details(pairs),
            marker: {
              size: 8,
              color: r,
              colorscale: [
                [0, "#254ba0"],
                [0.5, "#e9ede9"],
                [1, "#b92c42"],
              ],
              cmin: -bound,
              cmax: bound,
            },
            hovertemplate: hover,
          },
        ]}
        layout={{
          xaxis:
            mode === "depth"
              ? axis(`Model - Observation (${result.units})`)
              : { ...axis("Observation time (UTC)"), type: "date", nticks: 4 },
          yaxis:
            mode === "depth"
              ? {
                  ...axis(
                    selected.verticalUnit === "m"
                      ? "Depth (m)"
                      : "Pressure (dbar)",
                  ),
                  autorange: "reversed",
                }
              : axis(`Model - Observation (${result.units})`),
          shapes: [
            mode === "depth"
              ? {
                  type: "line",
                  xref: "x",
                  yref: "paper",
                  x0: 0,
                  x1: 0,
                  y0: 0,
                  y1: 1,
                  line: { color: "#a2b2c2", dash: "dot" },
                }
              : {
                  type: "line",
                  xref: "paper",
                  yref: "y",
                  x0: 0,
                  x1: 1,
                  y0: 0,
                  y1: 0,
                  line: { color: "#a2b2c2", dash: "dot" },
                },
          ],
          hovermode: "closest",
        }}
      />
    </div>
  );
}
