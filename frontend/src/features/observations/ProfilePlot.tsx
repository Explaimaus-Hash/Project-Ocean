"use client";
import { useEffect, useRef, useState } from "react";
import type { ObservationSample, Variable } from "@/lib/api/types";
import { loadPlotly } from "./loadPlotly";
import { profileSeries } from "./observationModel";
export function ProfilePlot({
  samples,
  variable,
  vertical,
}: {
  samples: ObservationSample[];
  variable: Variable;
  vertical: "depth_m" | "pressure_dbar";
}) {
  const host = useRef<HTMLDivElement>(null);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const series = profileSeries(samples, variable.name, vertical);
  const ylabel = vertical === "depth_m" ? "Depth (m)" : "Pressure (dbar)";
  useEffect(() => {
    const target = host.current;
    if (!target) return;
    let active = true;
    setError(false);
    const data = profileSeries(samples, variable.name, vertical);
    queue.current = queue.current
      .catch(() => undefined)
      .then(async () => {
        const P = await loadPlotly();
        if (!active) return;
        await P.react(
          target,
          [
            {
              type: "scatter",
              mode: data.y.some((value) => value === null)
                ? "markers"
                : "lines+markers",
              x: data.x,
              y: data.y,
              connectgaps: false,
              marker: { color: "#54d8e8", size: 5 },
              line: { color: "#54d8e8", width: 1.5 },
              hovertemplate: `%{x:.3f} ${variable.units}<br>%{y} ${vertical === "depth_m" ? "m" : "dbar"}<extra></extra>`,
            },
          ],
          {
            paper_bgcolor: "#0d1721",
            plot_bgcolor: "#0d1721",
            font: { family: "Arial, sans-serif", size: 10, color: "#c8d6df" },
            margin: { l: 55, r: 16, t: 25, b: 58 },
            height: 310,
            xaxis: {
              title: { text: `${variable.label} (${variable.units})` },
              gridcolor: "#263541",
              zeroline: false,
              automargin: true,
            },
            yaxis: {
              title: { text: ylabel },
              autorange: "reversed",
              gridcolor: "#263541",
              zeroline: false,
              automargin: true,
            },
            showlegend: false,
          },
          { displayModeBar: false, responsive: false, scrollZoom: false },
        );
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [samples, variable, vertical, attempt, ylabel]);
  useEffect(() => {
    const target = host.current;
    if (!target) return;
    const observer = new ResizeObserver(() => {
      if (window.Plotly && target.isConnected && target.clientWidth > 0 && target.clientHeight > 0 && target.querySelector(".svg-container"))
        void Promise.resolve(window.Plotly.Plots.resize(target)).catch(() => {
          if (target.isConnected && target.clientWidth > 0 && target.clientHeight > 0) setError(true);
        });
    });
    observer.observe(target);
    return () => {
      observer.disconnect();
      void queue.current.finally(() => window.Plotly?.purge(target));
    };
  }, []);
  return (
    <section
      className="profile-plot"
      aria-label={`${variable.label} versus ${ylabel}`}
    >
      <div
        ref={host}
        role="img"
        aria-label={`${variable.label} (${variable.units}) versus ${ylabel}, surface at top, missing values create gaps`}
      />
      {error && (
        <p role="status">
          Profile chart unavailable.{" "}
          <button onClick={() => setAttempt((v) => v + 1)}>Retry chart</button>
        </p>
      )}
      <p className="field-note">
        {samples.length} samples on this profile page · {series.missing} missing
        values or vertical coordinates. Surface at top; no depth/pressure
        conversion.
      </p>
      <details>
        <summary>Accessible sample values</summary>
        <table>
          <thead>
            <tr>
              <th>
                {variable.label} ({variable.units})
              </th>
              <th>{ylabel}</th>
            </tr>
          </thead>
          <tbody>
            {series.ids.map((id, i) => (
              <tr key={id}>
                <td>{series.x[i] ?? "Missing"}</td>
                <td>{series.y[i] ?? "Missing"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
