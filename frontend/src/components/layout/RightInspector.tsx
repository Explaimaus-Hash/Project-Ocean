"use client";
import { useScalar } from "@/features/scalar/ScalarContext";
import { modelCell } from "@/features/scalar/modelPoint";
import { publicText } from "@/features/data-sources/sourceInventory";
import { ObservationInspector } from "@/features/observations/ObservationInspector";
import { useData } from "@/features/data-sources/DataProvider";
import { useState, useEffect } from "react";
import { ScanLine } from "lucide-react";
import { useSelection } from "@/lib/selection";
import { EmptyState } from "@/components/ui/EmptyState";
type InspectorMode =
  "model-point" | "argo-profile" | "glider-sample" | "dataset-metadata";
const descriptions: Record<InspectorMode, string> = {
  "model-point":
    "Select a model point when a scientific field is connected. Values, units and provenance will appear here.",
  "argo-profile":
    "Select an Argo profile when prepared observations are connected. No profile is loaded.",
  "glider-sample":
    "Select a glider sample when prepared observations are connected. No sample is loaded.",
  "dataset-metadata":
    "Choose a prepared dataset to inspect its identity, coverage, units and provenance.",
};
export function RightInspector() {
  const { selection, dispatch } = useSelection();
  const data = useData();
  const scalar = useScalar();
  const frame = scalar.renderInfo?.frame;
  const point = selection.analysisPoint;
  const cell = frame && point ? modelCell(frame, point) : null;
  const [mode, setMode] = useState<InspectorMode>("model-point");
  useEffect(()=>{ if(point) setMode("model-point"); }, [point]);
  if (selection.selectedObservation) return <ObservationInspector />;
  return (
    <aside
      className="right-inspector"
      aria-label="Selection inspector"
      data-model-selected={!!point && !!frame && scalar.settings.visible}
    >
      <div className="section-title">
        <ScanLine size={16} />
        <h2>Inspector</h2>
        <span className="eyebrow">SELECTION</span>
      </div>
      {point && (
        <button
          className="text-button"
          onClick={() =>
            dispatch({ type: "select-analysis-point", point: null })
          }
        >
          Clear model point
        </button>
      )}
      <label htmlFor="inspector-mode">INSPECTOR VIEW</label>
      <select
        id="inspector-mode"
        value={mode}
        onChange={(event) => setMode(event.target.value as InspectorMode)}
      >
        <option value="model-point">Model point</option>
        <option value="argo-profile">Argo profile</option>
        <option value="glider-sample">Glider sample</option>
        <option value="dataset-metadata">Dataset metadata</option>
      </select>
      {mode === "model-point" &&
      point &&
      frame &&
      scalar.settings.visible &&
      selection.renderMode === "surface" ? (
        <section
          className="model-point-inspector"
          aria-label="Model point values"
        >
          <h3>Returned frame cell</h3>
          <p>
            {frame.mode === "synthetic" ? "SYNTHETIC DEMO" : "Source frame"} ·{" "}
            {publicText(data.product.value?.source_name)}
          </p>
          <dl>
            <dt>Requested coordinate</dt>
            <dd>
              {point.longitude.toFixed(4)}°, {point.latitude.toFixed(4)}°
            </dd>
            <dt>Actual frame cell</dt>
            <dd>
              {cell
                ? `${cell.longitude.toFixed(4)}°, ${cell.latitude.toFixed(4)}° · row ${cell.row}, column ${cell.column}`
                : "Outside returned frame"}
            </dd>
            <dt>
              {data.product.value?.variables.find(
                (v) => v.name === frame.variable,
              )?.label ?? frame.variable}{" "}
              ({frame.units})
            </dt>
            <dd>
              {cell
                ? cell.value === null
                  ? "Missing / land — no measurement"
                  : cell.value
                : "No data in region"}
            </dd>
            <dt>Displayed source timestamp</dt>
            <dd>{frame.timestamp}</dd>
            <dt>Product</dt>
            <dd>{publicText(frame.product_id)}</dd>
          </dl>
          <p className="field-note">
            Nearest returned frame cell; no interpolation.{" "}
            {frame.display_only
              ? "Preview values are for display, not scientific matching."
              : "Scientific-quality frame values; no matching performed."}
          </p>
        </section>
      ) : mode === "dataset-metadata" && data.product.value ? (
        <div className="inspector-note">
          <strong>{data.product.value.mode === "synthetic" ? "Demo metadata · synthetic" : "Source metadata"}</strong>
          <p>{publicText(data.product.value.provenance)}</p>
          <p>
            Coverage: {data.product.value.bounds.west}°E–
            {data.product.value.bounds.east}°E,{" "}
            {data.product.value.bounds.south}°–{data.product.value.bounds.north}
            °
          </p>
          <p>{data.timestamp} · surface only</p>
        </div>
      ) : (
        <EmptyState
          title="No point selected"
          description={descriptions[mode]}
        />
      )}
      <dl>
        <dt>Selected region</dt>
        <dd>
          {selection.region === "indian-ocean"
            ? "Indian Ocean"
            : "Global ocean"}
        </dd>
        <dt>Dataset / variable</dt>
        <dd>
          {data.dataset?.name ?? "Not selected"} / {data.variable ?? "—"}
        </dd>
        <dt>Time / depth</dt>
        <dd>
          {data.timestamp ?? "Not selected"} /{" "}
          {data.product.value ? "Surface" : "—"}
        </dd>
        <dt>Coverage / QC</dt>
        <dd>Not available</dd>
      </dl>
      <div className="inspector-note">
        <span className="mini-line" />
        {point && frame ? "Returned frame values; no scientific matching." : "Geographic context only."}
        <br />
        Picking Earth does not create scientific observations.
      </div>
    </aside>
  );
}
