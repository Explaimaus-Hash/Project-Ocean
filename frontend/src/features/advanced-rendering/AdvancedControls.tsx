"use client";
import { useData } from "@/features/data-sources/DataProvider";
import { useGlobe, type Quality } from "@/features/globe/GlobeContext";
import { useSelection } from "@/lib/selection";
import {
  capabilityModes,
  advancedUnavailable,
  type AdvancedMode,
} from "./advancedModel";
export function AdvancedControls() {
  const d = useData(),
    { settings, updateSettings } = useGlobe(),
    { selection, dispatch } = useSelection();
  const modes = capabilityModes(d.product.value, d.advancedField, {
    variable: d.variable,
    timestamp: d.timestamp,
  });
  const mode = modes[selection.renderMode] ? selection.renderMode : "surface";
  const levels = modes["depth-slice"] ? d.advancedField!.depths : [];
  return (
    <section
      className="advanced-controls"
      aria-label="Advanced rendering controls"
    >
      <label htmlFor="render-mode">RENDER MODE</label>
      <select
        id="render-mode"
        value={mode}
        disabled={!modes.surface}
        onChange={(e) => {
          const value = e.target.value as AdvancedMode;
          if (modes[value]) dispatch({ type: "select-render-mode", value });
        }}
      >
        {(
          [
            ["surface", "Surface"],
            ["depth-slice", "Depth Slice"],
            ["vectors", "Currents"],
            ["volume", "Volume"],
          ] as const
        ).map(([value, label]) => (
          <option key={value} value={value} disabled={!modes[value]}>
            {label}
          </option>
        ))}
      </select>
      <p id="advanced-reason" className="field-note">
        {advancedUnavailable}
      </p>
      <label htmlFor="depth">DEPTH · actual metadata levels</label>
      <input
        id="depth"
        aria-label="Depth slice level"
        aria-describedby="advanced-reason"
        type="range"
        min="0"
        max={Math.max(0, levels.length - 1)}
        value={Math.max(0, levels.indexOf(selection.depth?.value ?? levels[0]))}
        disabled={!levels.length}
        onChange={(e) =>
          dispatch({
            type: "select-depth",
            value: { value: levels[Number(e.target.value)], unit: "m" },
          })
        }
      />
      <p className="field-note">
        {levels.length
          ? levels.map((z) => `${z} m`).join(" · ")
          : "No served depth levels. Pressure is never converted to depth."}
      </p>
      <label htmlFor="vertical-exaggeration">
        Vertical exaggeration · {settings.exaggeration}× (display only)
      </label>
      <input
        id="vertical-exaggeration"
        type="range"
        min="1"
        max="10"
        step="1"
        value={settings.exaggeration}
        onChange={(e) =>
          updateSettings({ exaggeration: Number(e.target.value) })
        }
      />
      <p className="field-note">
        Only changes rendered subsurface height; no effect on surface fields or
        scientific depth values.
      </p>
      <label>
        Current display density
        <input
          aria-label="Current display density"
          type="range"
          min="10"
          max="100"
          value={settings.vectorDensity * 100}
          disabled={!modes.vectors}
          onChange={(e) =>
            updateSettings({ vectorDensity: Number(e.target.value) / 100 })
          }
        />
      </label>
      <label>
        Vector scale · display metres per m/s
        <input
          aria-label="Vector scale"
          type="range"
          min="100"
          max="20000"
          step="100"
          value={settings.vectorScale}
          disabled={!modes.vectors}
          onChange={(e) =>
            updateSettings({ vectorScale: Number(e.target.value) })
          }
        />
      </label>
      <label className="check-label">
        <input
          type="checkbox"
          disabled={!modes.vectors}
          checked={settings.speedColor}
          onChange={(e) => updateSettings({ speedColor: e.target.checked })}
        />
        Speed-based vector color
      </label>
      <label>
        DISPLAY QUALITY
        <select
          aria-label="Advanced display quality"
          value={settings.quality}
          onChange={(e) =>
            updateSettings({ quality: e.target.value as Quality })
          }
        >
          <option value="preview">Preview</option>
          <option value="balanced">Balanced</option>
          <option value="high">High</option>
        </select>
      </label>
      <p className="field-note">
        GPU resolution, scalar raster resolution and advanced display sample
        budget only. Backend frame quality remains preview/scientific.
      </p>
      {mode !== "surface" && (
        <button
          onClick={() =>
            dispatch({ type: "select-render-mode", value: "surface" })
          }
        >
          Return to surface globe
        </button>
      )}
    </section>
  );
}
