"use client";
import { useEffect, useRef, useState } from "react";
import { useData } from "@/features/data-sources/DataProvider";
import { useSelection } from "@/lib/selection";
import type { Timeseries } from "@/lib/api/types";
import { LatestRequest } from "@/lib/dataClient";
import { asApiError, errorCopy, ApiError } from "@/lib/api/errors";
import { TimeSeriesPlot } from "./TimeSeriesPlot";
import { analysisAvailability } from "./plotModel";
import { useGeographicSelection } from "./useGeographicSelection";
export function AnalysisWorkspace() {
  const d = useData();
  const { selection, dispatch } = useSelection();
  const product = d.product.value;
  const variable = product?.variables.find((v) => v.name === d.variable);
  const [revision, setRevision] = useState(0);
  const [picking, setPicking] = useState(false);
  const [inputError, setInputError] = useState("");
  const [draft, setDraft] = useState<{
    id: string;
    longitude: string;
    latitude: string;
  } | null>(null);
  const point = selection.analysisPoint ?? {
    longitude: product ? (product.bounds.west + product.bounds.east) / 2 : 75,
    latitude: product ? (product.bounds.south + product.bounds.north) / 2 : 0,
  };
  const longitude =
    draft?.id === product?.product_id
      ? (draft?.longitude ?? String(point.longitude))
      : String(point.longitude);
  const latitude =
    draft?.id === product?.product_id
      ? (draft?.latitude ?? String(point.latitude))
      : String(point.latitude);
  const supported = !!product?.capabilities.timeseries && !!variable;
  const key = JSON.stringify([
    d.connectionKey,
    product?.product_id,
    variable?.name,
    point.longitude,
    point.latitude,
    revision,
  ]);
  const [result, setResult] = useState<{
    key: string;
    value?: Timeseries;
    error?: ApiError;
  }>({ key: "" });
  const gate = useRef(new LatestRequest());
  useEffect(() => {
    if (!supported || !product || !variable) return;
    let active = true;
    const requestGate = gate.current;
    requestGate
      .run((signal) =>
        d.requestTimeseries(
          product.product_id,
          { variable: variable.name, ...point },
          signal,
        ),
      )
      .then((value) => {
        if (value.units !== variable.units || !value.units)
          throw new ApiError("invalid_response");
        if (active) setResult({ key, value });
      })
      .catch((error) => {
        if (active) setResult({ key, error: asApiError(error) });
      });
    return () => {
      active = false;
      requestGate.cancel();
    };
  }, [key, supported, d.requestTimeseries]);
  const current = result.key === key && supported ? result : undefined;
  const data = current?.value;
  const availability = analysisAvailability(supported);
  useGeographicSelection({
    mode: picking && supported ? "point" : "none",
    requested: product ? point : undefined,
    actual: data
      ? { longitude: data.longitude, latitude: data.latitude }
      : undefined,
    onPoint: (coordinate) => {
      dispatch({ type: "select-observation-sample", value: null });
      dispatch({ type: "select-analysis-point", point: coordinate });
      setDraft(null);
      setPicking(false);
      setInputError("");
    },
  });
  const submit = () => {
    const lon = Number(longitude),
      lat = Number(latitude);
    if (
      !longitude.trim() ||
      !latitude.trim() ||
      !Number.isFinite(lon) ||
      !Number.isFinite(lat) ||
      Math.abs(lon) > 180 ||
      Math.abs(lat) > 90
    ) {
      setInputError("Enter longitude −180 to 180 and latitude −90 to 90.");
      return;
    }
    dispatch({
      type: "select-analysis-point",
      point: { longitude: lon, latitude: lat },
    });
    setInputError("");
  };
  return (
    <div className="analysis-workspace">
      <header>
        <span className="eyebrow">PROJECT OCEAN / SCIENTIFIC ANALYSIS</span>
        <h1>Analysis</h1>
        <p>Geographic context and source-resolved measurements. This time-series chart covers the selected prepared batch; use Explorer date selection to view other archive dates.</p>
      </header>
      <div className="analysis-selectors">
        <label>
          Dataset
          <select
            aria-label="Analysis dataset"
            value={d.dataset?.dataset_id ?? ""}
            onChange={(e) => d.selectDataset(e.target.value)}
          >
            <option value="">Select a prepared dataset</option>
            {d.catalogue.value?.datasets.map((p) => (
              <option key={p.dataset_id} value={p.dataset_id}>
                {p.source_name} / {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Quantity
          <select
            aria-label="Analysis quantity"
            disabled={!d.variables.length}
            value={d.variable ?? ""}
            onChange={(e) => d.selectVariable(e.target.value)}
          >
            {d.variables.map((v) => (
              <option key={v.name} value={v.name}>
                {v.label} ({v.units})
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="analysis-tabs" role="tablist" aria-label="Analysis types">
        {(["timeseries", "profile", "timeDepth", "transect"] as const).map(
          (kind, i) => (
            <button
              key={kind}
              role="tab"
              aria-selected={kind === "timeseries"}
              disabled={!availability[kind].enabled}
              title={availability[kind].reason}
              aria-describedby={
                availability[kind].enabled
                  ? undefined
                  : `analysis-reason-${kind}`
              }
            >
              {["Time Series", "Vertical Profile", "Time–Depth", "Transect"][i]}
            </button>
          ),
        )}
      </div>
      <form
        className="analysis-coordinate-form"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label>
          Longitude
          <input
            aria-label="Requested longitude"
            type="number"
            step="any"
            value={longitude}
            onChange={(e) =>
              setDraft({
                id: product?.product_id ?? "",
                longitude: e.target.value,
                latitude,
              })
            }
          />
        </label>
        <label>
          Latitude
          <input
            aria-label="Requested latitude"
            type="number"
            step="any"
            value={latitude}
            onChange={(e) =>
              setDraft({
                id: product?.product_id ?? "",
                longitude,
                latitude: e.target.value,
              })
            }
          />
        </label>
        <button disabled={!supported} type="submit">
          Load time series
        </button>
        <button
          disabled={!supported}
          type="button"
          onClick={() => setPicking((v) => !v)}
        >
          {picking ? "Cancel point picking" : "Pick point on globe"}
        </button>
      </form>
      {picking && (
        <p role="status">
          Click the globe to request a point. Orange is requested; cyan is the
          API-returned grid cell.
        </p>
      )}
      {inputError && <p role="status">{inputError}</p>}
      {current?.error ? (
        <div className="api-state" role="status">
          <strong>{errorCopy[current.error.code][0]}</strong>
          <p>{errorCopy[current.error.code][1]}</p>
          <button onClick={() => setRevision((v) => v + 1)}>
            Retry time series
          </button>
        </div>
      ) : supported && !data ? (
        <p role="status">Loading the selected point’s time series…</p>
      ) : null}
      {data && product && variable ? (
        <>
          <dl className="analysis-location">
            <div>
              <dt>Requested</dt>
              <dd>
                {point.longitude.toFixed(4)}°, {point.latitude.toFixed(4)}°
              </dd>
            </div>
            <div>
              <dt>Actual grid cell</dt>
              <dd>
                {data.longitude.toFixed(4)}°, {data.latitude.toFixed(4)}°
              </dd>
            </div>
            <div>
              <dt>Distance (API)</dt>
              <dd>{data.distance_km.toFixed(3)} km</dd>
            </div>
            <div>
              <dt>Vertical selection</dt>
              <dd>
                {product.capabilities.depth
                  ? "Depth not supplied by this endpoint"
                  : "Surface field · no water column"}
              </dd>
            </div>
          </dl>
          <TimeSeriesPlot
            data={data}
            requested={point}
            metadata={{
              title: `${variable.label} time series`,
              source: product.source_name,
              dataset: product.name,
              quantity: variable.label,
              units: data.units,
              selection: `Cell ${data.longitude.toFixed(4)}°, ${data.latitude.toFixed(4)}°`,
              timeRange: data.timestamps.length
                ? `${data.timestamps[0]} → ${data.timestamps.at(-1)}`
                : "No timestamps returned",
              mode: data.mode,
              note: `${product.provenance} Actual cell and distance come from the API. Grid row/column indices are not supplied. Missing values remain gaps; no frontend smoothing or scientific interpolation.`,
            }}
          />
        </>
      ) : (
        !supported && (
          <p id="analysis-reason-timeseries" className="analysis-unavailable">
            {availability.timeseries.reason}{" "}
            {d.product.error
              ? errorCopy[d.product.error.code][0]
              : d.dataset?.status === "not_prepared"
                ? "Dataset not prepared."
                : ""}
          </p>
        )
      )}
      <div className="analysis-limits">
        {(["profile", "timeDepth", "transect"] as const).map((kind) => (
          <p id={`analysis-reason-${kind}`} key={kind}>
            {availability[kind].reason}
          </p>
        ))}
      </div>
    </div>
  );
}
