"use client";
import { AdvancedControls } from "@/features/advanced-rendering/AdvancedControls";
import { ScalarLayerPanel } from "@/features/scalar/ScalarLayerPanel";
import { useSelection, type RegionId } from "@/lib/selection";
import { useGlobe } from "@/features/globe/GlobeContext";
import { ScientificTooltip } from "@/components/ui/ScientificTooltip";
import { useData, ApiState } from "@/features/data-sources/DataProvider";
import { ApiError } from "@/lib/api/errors";
import { SourceTimeControl } from "./SourceTimeControl";
export function SelectionControls() {
  const { selection, dispatch } = useSelection();
  const d = useData();
  const { settings, updateSettings } = useGlobe();
  const p = d.product.value;
  return (
    <section className="selection-controls" aria-label="Shared selection">
      <div className="section-title">
        <h2>Workspace selection</h2>
        <ScientificTooltip label="About shared selection">
          Selections persist between routes. Project bounds do not imply common
          coverage.
        </ScientificTooltip>
      </div>
      <div className="demo-notice">
        LOCAL PREPARED DATA<p>Source resolution and scientific/display labels are preserved.</p>
      </div>
      <label htmlFor="region">REGION</label>
      <select
        id="region"
        value={selection.region}
        onChange={(e) =>
          dispatch({
            type: "select-region",
            region: e.target.value as RegionId,
          })
        }
      >
        <option value="indian-ocean">Indian Ocean</option>
        <option value="global">Global ocean</option>
      </select>
      <label htmlFor="dataset">DATASET</label>
      <select
        id="dataset"
        value={d.dataset?.dataset_id ?? ""}
        disabled={!d.catalogue.value?.datasets.length}
        onChange={(e) => d.selectDataset(e.target.value)}
      >
        <option value="">Select a dataset</option>
        {d.catalogue.value?.datasets.map((v) => (
          <option key={v.dataset_id} value={v.dataset_id}>
            {v.source_name} / {v.name} · {v.status.replaceAll("_", " ")}
          </option>
        ))}
      </select>
      <ApiState
        error={
          d.catalogue.error ??
          (d.catalogue.value && !d.catalogue.value.datasets.length
            ? new ApiError("empty_selection")
            : undefined)
        }
      />
      {d.dataset && (
        <p className="field-note">
          {d.dataset.dataset_id} · {d.dataset.mode}
          <br />
          {d.dataset.time_coverage
            ? `${d.dataset.time_coverage.start} – ${d.dataset.time_coverage.end}`
            : "Time coverage not advertised"}
        </p>
      )}
      <ApiState
        error={
          d.product.error ??
          (d.dataset && !d.dataset.product_id
            ? new ApiError(
                d.dataset.status === "provider_unavailable"
                  ? "provider_unavailable"
                  : "not_prepared",
              )
            : undefined)
        }
      />
      <label htmlFor="variable">VARIABLE</label>
      <select
        id="variable"
        disabled={!p}
        value={d.variable ?? ""}
        onChange={(e) => d.selectVariable(e.target.value)}
      >
        {!p && <option value="">Awaiting product metadata</option>}
        {p?.variables.map((v) => (
          <option key={v.name} value={v.name}>
            {v.label} ({v.units})
          </option>
        ))}
      </select>
      <div className="field-label">
        <label htmlFor="depth">DEPTH</label>
        <ScientificTooltip label="Depth unavailable">
          Only verified vertical metadata enables depth. BIO-ROMS V2 is
          surface-only.
        </ScientificTooltip>
      </div>
      <SourceTimeControl
        key={JSON.stringify([d.dataset?.dataset_id, d.timelineTimestamp])}
        times={d.times}
        timestamp={d.timelineTimestamp}
        onSelect={d.selectTime}
      />
      <AdvancedControls />
      <ApiState context="frame" error={d.frame.error} />
      {p && (
        <p className="field-note" role="status">
          {d.frame.value
            ? `Prepared frame loaded · ${d.frame.value.timestamp}`
            : d.frame.error
              ? "Frame unavailable"
              : "Loading prepared frame…"}
        </p>
      )}
      <label htmlFor="observation">OBSERVATIONS</label>
      <select
        id="observation"
        value={selection.observationSource ?? ""}
        disabled={!d.observations.value?.collections.length}
        onChange={(e) =>
          dispatch({ type: "select-observation", id: e.target.value })
        }
      >
        <option value="">No collection selected</option>
        {d.observations.value?.collections.map((c) => (
          <option key={c.collection_id} value={c.collection_id}>
            {c.name} · {c.source}
          </option>
        ))}
      </select>
      <ApiState
        context="observations"
        error={
          d.observations.error ?? d.collectionDetail.error ?? d.samples.error
        }
      />
      {d.collectionDetail.value && (
        <p className="field-note">
          {d.collectionDetail.value.sample_count} samples ·{" "}
          {d.collectionDetail.value.profile_count ?? "Unknown"} identified profiles
          <br />
          {d.collectionDetail.value.variables.map((v) => v.label).join(", ")}
          <br />
          QC: {d.collectionDetail.value.qc_status}
          <br />
          Capabilities:{" "}
          {Object.entries(d.collectionDetail.value.capabilities)
            .filter(([, enabled]) => enabled)
            .map(([name]) => name)
            .join(", ")}
          <br />
          {d.samples.value?.samples.length ?? 0} source samples loaded. Pressure
          (dbar) is not depth (m).
        </p>
      )}
      <h2 className="spaced">Geographic layers</h2>
      <label className="check-label">
        <input
          type="checkbox"
          checked={settings.basemapVisible}
          onChange={(e) => updateSettings({ basemapVisible: e.target.checked })}
        />
        Earth basemap
      </label>
      <label htmlFor="basemap-opacity">OPACITY</label>
      <input
        id="basemap-opacity"
        type="range"
        min="0"
        max="100"
        value={settings.basemapOpacity * 100}
        onChange={(e) =>
          updateSettings({ basemapOpacity: Number(e.target.value) / 100 })
        }
      />
      <ScalarLayerPanel />
      <button
        className="text-button"
        onClick={() => dispatch({ type: "reset" })}
      >
        Reset selection
      </button>
    </section>
  );
}
