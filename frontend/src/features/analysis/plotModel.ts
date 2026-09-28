export interface PlotMetadata {
  title: string;
  source: string;
  dataset: string;
  quantity: string;
  units: string;
  selection: string;
  timeRange: string;
  note: string;
  mode: "real" | "synthetic";
}
export type CsvCell = string | number | null;
export function plottedCSV(headers: string[], rows: CsvCell[][]) {
  if (rows.length > 10000 || rows.some((r) => r.length !== headers.length))
    throw new Error("CSV is not bounded");
  const encode = (value: CsvCell) => {
    let text = value === null ? "" : String(value);
    if (typeof value === "string" && /^[=+@\-\t\r]/.test(text))
      text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return [headers, ...rows]
    .map((row) => row.map(encode).join(","))
    .join("\r\n");
}
export function escapePlotText(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
export function analysisAvailability(timeseries: boolean) {
  return {
    timeseries: {
      enabled: timeseries,
      reason: timeseries
        ? ""
        : "Time series requires a prepared product that advertises this capability.",
    },
    profile: {
      enabled: false,
      reason: "Vertical profile not available for this dataset.",
    },
    timeDepth: {
      enabled: false,
      reason:
        "Time–depth not available: no verified product time–depth endpoint or adapter is connected.",
    },
    transect: {
      enabled: false,
      reason:
        "Transect not available: no suitable depth-resolved backend source or endpoint is connected.",
    },
  };
}
