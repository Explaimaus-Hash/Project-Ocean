"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { loadPlotly } from "@/features/observations/loadPlotly";
import {
  plottedCSV,
  escapePlotText,
  type CsvCell,
  type PlotMetadata,
} from "./plotModel";
export function ScientificPlotShell({
  metadata,
  traces,
  layout,
  csv,
  children,
  onGeographicHover,
}: {
  metadata: PlotMetadata;
  traces: Record<string, unknown>[];
  layout: Record<string, unknown>;
  csv?: { headers: string[]; rows: CsvCell[][] };
  children?: ReactNode;
  onGeographicHover?: (active: boolean) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const hover = useRef(onGeographicHover);
  hover.current = onGeographicHover;
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [actionError, setActionError] = useState("");
  const [attempt, setAttempt] = useState(0);
  // Stable serializable plot inputs prevent non-data context renders from resetting zoom.
  const signature = JSON.stringify({ metadata, traces, layout });
  useEffect(() => {
    const target = host.current;
    if (!target) return;
    let active = true;
    let removeHover: (() => void) | undefined;
    setStatus("loading");
    queue.current = queue.current
      .catch(() => undefined)
      .then(async () => {
        const P = await loadPlotly();
        if (!active) return;
        await P.react(
          target,
          traces,
          {
            paper_bgcolor: "#101923",
            plot_bgcolor: "#0b151f",
            font: { family: "Arial, sans-serif", color: "#c9d9e4", size: 11 },
            height: 360,
            margin: { l: 80, r: 24, t: 24, b: 72 },
            title: {text:""},
            showlegend: traces.length > 1,
            legend: { orientation: "h", y: -0.25 },
            hovermode: "x unified",
            dragmode: "zoom",
            ...layout,
            xaxis: {automargin:true,...(layout.xaxis as object ?? {})},
            yaxis: {automargin:true,...(layout.yaxis as object ?? {})},
          },
          {
            displaylogo: false,
            responsive: false,
            scrollZoom: false,
            modeBarButtonsToRemove: ["lasso2d", "select2d", "toImage"],
          },
        );
        if (active) {
          setStatus("ready");
          const plot = target as HTMLElement & {
            on?: (event: string, handler: () => void) => void;
            removeListener?: (event: string, handler: () => void) => void;
          };
          const enter = () => hover.current?.(true),
            leave = () => hover.current?.(false);
          plot.on?.("plotly_hover", enter);
          plot.on?.("plotly_unhover", leave);
          removeHover = () => {
            plot.removeListener?.("plotly_hover", enter);
            plot.removeListener?.("plotly_unhover", leave);
          };
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
      removeHover?.();
    };
    // The signature contains every plot input; presentation context does not drive plot redraws.
  }, [signature, attempt]);
  useEffect(() => {
    const target = host.current;
    if (!target) return;
    const observer = new ResizeObserver(() => {
      if (window.Plotly && target.isConnected && target.clientWidth > 0 && target.clientHeight > 0 && target.querySelector(".svg-container"))
        void Promise.resolve(window.Plotly.Plots.resize(target)).catch(() => {
          // Plotly resizes asynchronously; navigation may detach the plot meanwhile.
          if (target.isConnected && target.clientWidth > 0 && target.clientHeight > 0) setStatus("error");
        });
    });
    observer.observe(target);
    return () => {
      observer.disconnect();
      void queue.current.finally(() => window.Plotly?.purge(target));
    };
  }, []);
  const action = async (kind: "reset" | "png") => {
    if (!host.current) return;
    try {
      setActionError("");
      const P = await loadPlotly();
      if (kind === "png") {
        // HTML metadata wraps responsively on screen; include it in PNG exports too.
        try {
          await P.relayout(host.current, {
            title: {text:`${escapePlotText(metadata.title)}<br><sup>${escapePlotText(metadata.source)} · ${escapePlotText(metadata.dataset)} · ${metadata.mode}<br>${escapePlotText(metadata.selection)}<br>${escapePlotText(metadata.timeRange)}</sup>`,font:{size:12},x:0.04,y:0.98,xanchor:"left",yanchor:"top"},
            "margin.t":140,
          });
          await P.downloadImage(host.current, {
            format: "png", filename: "project-ocean-analysis", width: 1400, height: 850,
          });
        } finally {
          if (host.current?.isConnected) await P.relayout(host.current,{title:{text:""},"margin.t":24});
        }
      }
      else {
        const y = layout.yaxis as { autorange?: unknown } | undefined;
        await P.relayout(host.current, {
          "xaxis.autorange": true,
          "yaxis.autorange": y?.autorange === "reversed" ? "reversed" : true,
        });
      }
    } catch {
      setActionError("Graph action failed. Retry after the chart loads.");
    }
  };
  const exportCSV = () => {
    if (!csv) return;
    try {
      const value = plottedCSV(csv.headers, csv.rows);
      const url = URL.createObjectURL(
        new Blob([value], { type: "text/csv;charset=utf-8" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "project-ocean-plotted-data.csv";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setActionError("CSV export exceeds the supported bounded size.");
    }
  };
  return (
    <section className="scientific-plot-shell" aria-label={metadata.title}>
      <header>
        <h2>{metadata.title}</h2>
        <span className="eyebrow">
          {metadata.mode === "synthetic" ? "SYNTHETIC DEMO" : "SOURCE DATA"}
        </span>
      </header>
      <p className="plot-context">
        {metadata.source} / {metadata.dataset}
        <br />
        {metadata.quantity} ({metadata.units}) · {metadata.selection}
        <br />
        {metadata.timeRange}
      </p>
      <div className="plot-toolbar">
        <button
          disabled={status !== "ready"}
          onClick={() => void action("reset")}
        >
          Reset zoom
        </button>
        <button
          disabled={status !== "ready"}
          onClick={() => void action("png")}
        >
          Download PNG
        </button>
        {onGeographicHover && (
          <button
            disabled={status !== "ready"}
            onFocus={() => hover.current?.(true)}
            onBlur={() => hover.current?.(false)}
            onMouseEnter={() => hover.current?.(true)}
            onMouseLeave={() => hover.current?.(false)}
          >
            Highlight actual grid cell
          </button>
        )}
        {csv && (
          <button
            disabled={status !== "ready" || csv.rows.length > 10000}
            onClick={exportCSV}
          >
            Export plotted CSV
          </button>
        )}
      </div>
      <div
        className="scientific-plot"
        ref={host}
        role="img"
        aria-label={`${metadata.quantity} (${metadata.units}); ${metadata.selection}; ${metadata.timeRange}`}
      />
      {status === "loading" && <p role="status">Preparing scientific graph…</p>}
      {status === "error" && (
        <p role="status">
          Graph unavailable.{" "}
          <button onClick={() => setAttempt((v) => v + 1)}>Retry graph</button>
        </p>
      )}
      {actionError && <p role="status">{actionError}</p>}
      <p className="scientific-note">{metadata.note}</p>
      {children}
    </section>
  );
}
export const scientificAxis = {
  gridcolor: "#263746",
  zeroline: false,
  showspikes: true,
  spikecolor: "#7299ac",
  spikethickness: 1,
  spikemode: "across",
  spikesnap: "cursor",
  automargin: true,
};
