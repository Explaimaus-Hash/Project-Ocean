"use client";
import { useState } from "react";
import { useData } from "@/features/data-sources/DataProvider";
import { useGlobe } from "@/features/globe/GlobeContext";
import { useScalar } from "./ScalarContext";
import { palettes, type Palette } from "./ScientificColorScale";
export function ScalarLayerPanel() {
  const d = useData(),
    s = useScalar(),
    { viewer } = useGlobe();
  const [regionError, setRegionError] = useState("");
  const viewport = () => {
    const rectangle = viewer?.camera.computeViewRectangle();
    if (!rectangle || rectangle.east <= rectangle.west) {
      setRegionError(
        "Viewport bounds are unavailable or cross the dateline. Use the project region.",
      );
      return;
    }
    const degrees = 180 / Math.PI;
    d.setViewportBounds({
      west: rectangle.west * degrees,
      east: rectangle.east * degrees,
      south: rectangle.south * degrees,
      north: rectangle.north * degrees,
    });
    setRegionError("");
  };
  return (
    <section className="scalar-panel" aria-label="Scalar layer controls">
      <div className="section-title">
        <h2>Ocean scalar layer</h2>
        <span className="eyebrow">{d.displayedFrame?.mode ?? "NO FIELD"}</span>
      </div>
      <label className="check-label">
        <input
          type="checkbox"
          checked={s.settings.visible}
          onChange={(e) => s.update({ visible: e.target.checked })}
        />
        Show scalar layer
      </label>
      <p className="field-note">
        {d.dataset?.source_name ?? "Select a source"}
        <br />
        {d.dataset?.name ?? "No dataset"} · {d.variable ?? "No variable"}
        <br />
        Product: {d.product.value?.product_id ?? "—"}
      </p>
      <label htmlFor="scalar-opacity">
        LAYER OPACITY · {Math.round(s.settings.opacity * 100)}%
      </label>
      <input
        id="scalar-opacity"
        type="range"
        min="0"
        max="100"
        value={s.settings.opacity * 100}
        onChange={(e) => s.update({ opacity: Number(e.target.value) / 100 })}
      />
      <label htmlFor="scalar-quality">RENDER QUALITY</label>
      <select
        id="scalar-quality"
        value={d.quality}
        onChange={(e) =>
          d.setQuality(e.target.value as "preview" | "scientific")
        }
      >
        <option value="preview">Preview · bounded</option>
        <option value="scientific">Scientific · source samples</option>
      </select>
      {d.quality === "scientific" && d.frame.value?.display_only && (
        <p className="field-note" role="status">
          Scientific request exceeded limits. Using bounded preview; this extent
          will stay in preview.
        </p>
      )}
      <label htmlFor="scalar-palette">COLOR PALETTE</label>
      <select
        id="scalar-palette"
        value={s.settings.palette}
        onChange={(e) => s.update({ palette: e.target.value as Palette })}
      >
        {Object.keys(palettes).map((p) => (
          <option key={p}>{p}</option>
        ))}
      </select>
      <label htmlFor="scalar-range">COLOR RANGE</label>
      <select
        id="scalar-range"
        value={s.settings.manual ? "manual" : "auto"}
        onChange={(e) =>
          s.update({
            manual: e.target.value === "manual",
            min: String(s.stableRange?.[0] ?? ""),
            max: String(s.stableRange?.[1] ?? ""),
          })
        }
      >
        <option value="auto">Auto · stable across frames</option>
        <option value="manual">Manual limits</option>
      </select>
      <div className="paired-fields">
        <label>
          MIN
          <input
            aria-label="Manual minimum"
            type="number"
            step="any"
            disabled={!s.settings.manual}
            value={
              s.settings.manual ? s.settings.min : (s.stableRange?.[0] ?? "")
            }
            onChange={(e) => s.update({ min: e.target.value })}
          />
        </label>
        <label>
          MAX
          <input
            aria-label="Manual maximum"
            type="number"
            step="any"
            disabled={!s.settings.manual}
            value={
              s.settings.manual ? s.settings.max : (s.stableRange?.[1] ?? "")
            }
            onChange={(e) => s.update({ max: e.target.value })}
          />
        </label>
      </div>
      <label className="check-label">
        <input
          type="checkbox"
          disabled={s.settings.manual}
          checked={s.settings.perFrame}
          onChange={(e) => s.update({ perFrame: e.target.checked })}
        />
        Auto per frame
      </label>
      <label htmlFor="scalar-transform">SCALE TRANSFORM</label>
      <select
        id="scalar-transform"
        value={s.settings.log ? "log" : "linear"}
        onChange={(e) => s.update({ log: e.target.value === "log" })}
      >
        <option value="linear">Linear</option>
        <option value="log" disabled={!s.allowed}>
          Log · positive ratio quantities only
        </option>
      </select>
      <p className="field-note">
        Log is disabled for temperature, salinity and unverified quantities.
      </p>
      <label htmlFor="scalar-interpolation">DISPLAY INTERPOLATION</label>
      <select
        id="scalar-interpolation"
        value={s.settings.interpolation}
        onChange={(e) =>
          s.update({ interpolation: e.target.value as "nearest" | "bilinear" })
        }
      >
        <option value="nearest">Nearest · frame cells</option>
        <option value="bilinear">Bilinear · valid neighbors only</option>
      </select>
      <p className="field-note">
        Display smoothing only. Missing neighbors stay transparent. Scientific
        values and comparisons never use the display raster.
      </p>
      <div className="scalar-actions">
        <button
          className="text-button"
          onClick={() => {
            d.setViewportBounds(null);
            setRegionError("");
          }}
        >
          Project selection box
        </button>
        <button className="text-button" disabled={!viewer} onClick={viewport}>
          Use current viewport
        </button>
        <button className="text-button" onClick={s.reset}>
          Reset color scale
        </button>
      </div>
      <p className="field-note">
        {d.viewportBounds ? "Viewport snapshot" : "Project box"} · clipped to
        product coverage
        {d.bounds
          ? ` (${d.bounds.west.toFixed(1)}° to ${d.bounds.east.toFixed(1)}°, ${d.bounds.south.toFixed(1)}° to ${d.bounds.north.toFixed(1)}°)`
          : ""}
      </p>
      <p className="field-note" role="status">
        {regionError ||
          s.renderError ||
          (s.invalid && d.displayedFrame
            ? "Choose finite limits with minimum below maximum; the displayed scale is retained."
            : s.renderInfo
              ? `${s.settings.visible ? "Displayed" : "Hidden"} · ${s.renderInfo.frame.timestamp} · ${s.renderInfo.milliseconds.toFixed(0)} ms raster/upload preparation`
              : "Awaiting a valid field")}
      </p>
    </section>
  );
}

