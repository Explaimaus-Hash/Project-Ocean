"use client";
import {
  useGlobe,
  type GlobeSettings,
  type Quality,
} from "@/features/globe/GlobeContext";
export function DisplayPreferences() {
  const { settings: s, updateSettings: update } = useGlobe();
  return (
    <div className="display-preferences">
      <p className="field-note">
        Saved on this browser when local storage is available. Technical dark
        theme. No credentials are stored here.
      </p>
      <label htmlFor="quality">Rendering quality</label>
      <select
        id="quality"
        value={s.quality}
        onChange={(e) => update({ quality: e.target.value as Quality })}
      >
        <option value="preview">Preview</option>
        <option value="balanced">Balanced</option>
        <option value="high">High</option>
      </select>
      <p className="field-note">
        Default display quality: viewer and raster resolution plus display
        sample budgets; backend scientific quality is unchanged.
      </p>
      <label htmlFor="default-palette">Default palette</label>
      <select
        id="default-palette"
        value={s.defaultPalette}
        onChange={(e) =>
          update({
            defaultPalette: e.target.value as GlobeSettings["defaultPalette"],
          })
        }
      >
        {[
          "auto",
          "temperature",
          "salinity",
          "chlorophyll",
          "speed",
          "anomaly",
        ].map((v) => (
          <option key={v} value={v}>
            {v === "auto" ? "Automatic by quantity" : v}
          </option>
        ))}
      </select>
      <p className="field-note">
        Applies to new layer defaults and the current layer when changed.
        Values, units and scientific limits remain unchanged.
      </p>
      <label htmlFor="animation-speed">Camera animation speed</label>
      <select
        id="animation-speed"
        value={s.animationSpeed}
        onChange={(e) => update({ animationSpeed: Number(e.target.value) })}
      >
        {[0.25, 0.5, 1, 2, 4].map((v) => (
          <option key={v} value={v}>
            {v}×
          </option>
        ))}
      </select>
      <label htmlFor="settings-exaggeration">
        Vertical exaggeration · {s.exaggeration}×
      </label>
      <input
        id="settings-exaggeration"
        type="range"
        min="1"
        max="10"
        step="1"
        value={s.exaggeration}
        onChange={(e) => update({ exaggeration: Number(e.target.value) })}
      />
      <p className="field-note">
        Display only; no effect on surface-only products or scientific depth
        values.
      </p>
      {(
        [
          ["lighting", "Sun lighting"],
          ["atmosphere", "Atmosphere"],
          ["earthRotation", "Earth rotation"],
          ["keepCentered", "Keep region centered"],
          ["reducedAnimation", "Reduced animation"],
        ] as const
      ).map(([key, label]) => (
        <label className="check-label" key={key}>
          <input
            type="checkbox"
            checked={s[key]}
            onChange={(e) => update({ [key]: e.target.checked })}
          />
          {label}
        </label>
      ))}
      <p className="field-note">
        Sun lighting uses the globe clock, not dataset time. Rotation is a
        display orbit, pauses on globe interaction and is suppressed by reduced
        motion or region centering. Toggle it off/on to resume.
      </p>
      <p className="field-note">
        Keep region centered resets the project view and locks free
        pan/rotation; zoom remains available. Home and project reset remain
        explicit overrides. System reduced-motion preference always takes
        priority.
      </p>
    </div>
  );
}
