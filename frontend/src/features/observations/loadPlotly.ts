export interface PlotlyAPI {
  relayout: (
    target: HTMLElement,
    layout: Record<string, unknown>,
  ) => Promise<unknown>;
  downloadImage: (
    target: HTMLElement,
    options: Record<string, unknown>,
  ) => Promise<unknown>;
  newPlot: (
    target: HTMLElement,
    data: unknown[],
    layout: Record<string, unknown>,
    config: Record<string, unknown>,
  ) => Promise<unknown>;
  react: (
    target: HTMLElement,
    data: unknown[],
    layout: Record<string, unknown>,
    config: Record<string, unknown>,
  ) => Promise<unknown>;
  purge: (target: HTMLElement) => void;
  Plots: { resize: (target: HTMLElement) => Promise<unknown> };
}
declare global {
  interface Window {
    Plotly?: PlotlyAPI;
  }
}
let pending: Promise<PlotlyAPI> | undefined;
export function loadPlotly() {
  if (window.Plotly) return Promise.resolve(window.Plotly);
  if (pending) return pending;
  pending = new Promise<PlotlyAPI>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/plotly/plotly-cartesian.min.js";
    script.async = true;
    script.onload = () =>
      window.Plotly
        ? resolve(window.Plotly)
        : reject(new Error("Plot library unavailable"));
    script.onerror = () => {
      script.remove();
      pending = undefined;
      reject(new Error("Plot library unavailable"));
    };
    document.head.appendChild(script);
  });
  return pending;
}
