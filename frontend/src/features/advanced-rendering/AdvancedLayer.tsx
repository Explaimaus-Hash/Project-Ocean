"use client";
import { useEffect, useState, useMemo } from "react";
import { useGlobe } from "@/features/globe/GlobeContext";
import { loadCesium } from "@/lib/loadCesium";
import { buildAdvanced, type RenderOptions } from "./cesiumAdvanced";
import type { AdvancedField } from "./advancedModel";
export function AdvancedLayer({
  field,
  mode,
  options,
}: {
  field: AdvancedField;
  mode: "depth-slice" | "vectors" | "volume";
  options: RenderOptions;
}) {
  const { viewer } = useGlobe();
  const [status, setStatus] = useState("Preparing bounded display");
  const key = JSON.stringify(options);
  const range = useMemo(() => {
    let min = Infinity,
      max = -Infinity;
    if (mode === "vectors" && field.currents) {
      min = 0;
      max = 0;
      field.currents.east.forEach((row, y) =>
        row.forEach((u, x) => {
          const v = field.currents!.north[y][x];
          if (u !== null && v !== null) max = Math.max(max, Math.hypot(u, v));
        }),
      );
    } else {
      field.values.forEach((plane, z) => {
        if (mode === "depth-slice" && z !== options.depthIndex) return;
        for (const row of plane)
          for (const value of row)
            if (value !== null) {
              min = Math.min(min, value);
              max = Math.max(max, value);
            }
      });
    }
    return Number.isFinite(min) ? [min, max] : null;
  }, [field, mode, options.depthIndex]);
  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;
    let active = true;
    let destroy: (() => void) | undefined;
    let removeListener: (() => void) | undefined;
    const globe = viewer.scene.globe;
    const old = {
      enabled: globe.translucency.enabled,
      front: globe.translucency.frontFaceAlpha,
      back: globe.translucency.backFaceAlpha,
    };
    void loadCesium()
      .then((C) => {
        if (!active || viewer.isDestroyed()) return;
        const render = () => {
          if (!active || viewer.isDestroyed()) return;
          try {
            destroy?.();
            destroy = undefined;
            const built = buildAdvanced(C, viewer, field, mode, options);
            destroy = built.destroy;
            setStatus(
              `${built.count} display samples · ${built.milliseconds.toFixed(1)} ms CPU preparation`,
            );
          } catch {
            setStatus(
              "Advanced field unavailable. No unvalidated data displayed.",
            );
          }
        };
        globe.translucency.enabled = true;
        globe.translucency.frontFaceAlpha = 0.35;
        globe.translucency.backFaceAlpha = 0.15;
        render();
        removeListener =
          mode === "vectors"
            ? viewer.camera.moveEnd.addEventListener(render)
            : () => {};
      })
      .catch(() => {
        if (active)
          setStatus(
            "Advanced field unavailable. No unvalidated data displayed.",
          );
      });
    return () => {
      active = false;
      removeListener?.();
      destroy?.();
      if (!viewer.isDestroyed()) {
        globe.translucency.enabled = old.enabled;
        globe.translucency.frontFaceAlpha = old.front;
        globe.translucency.backFaceAlpha = old.back;
        viewer.scene.requestRender();
      }
    };
  }, [viewer, field, mode, key]);
  return (
    <aside className="advanced-legend">
      <strong>
        {mode === "volume"
          ? "Bounded volume prototype · discrete samples"
          : mode === "vectors"
            ? "East / north currents"
            : "Depth slice · discrete source samples"}
      </strong>
      <p>
        {field.variable} ({field.units}) · {field.timestamp}
      </p>
      <small>
        Product {field.productId} ·{" "}
        {mode === "vectors"
          ? "Horizontal speed (m/s)"
          : `${field.variable} (${field.units})`}
      </small>
      {range && (
        <div aria-label="Advanced field color legend">
          <div
            style={{
              height: 8,
              background:
                mode === "vectors" && !options.speedColor
                  ? "cyan"
                  : `linear-gradient(to right, ${mode === "vectors" ? "#1a66cc" : "#1a66e6"}, ${mode === "vectors" ? "#f2f24d" : "#e6e666"})`,
            }}
          />
          <small>
            {Array.from({ length: 5 }, (_, i) =>
              (range[0] + ((range[1] - range[0]) * i) / 4).toPrecision(4),
            ).join(" · ")}
          </small>
          <small>
            Min {range[0].toPrecision(4)} · Max {range[1].toPrecision(4)} ·
            Linear ·{" "}
            {mode === "vectors" && !options.speedColor
              ? "Uniform cyan; color does not encode speed"
              : "Sequential blue–yellow palette"}{" "}
            · Missing omitted
          </small>
        </div>
      )}
      <p>Vertical exaggeration {options.exaggeration}× · display only</p>
      {mode === "vectors" && (
        <p>
          1 m/s → {(options.vectorScale / 1000).toFixed(1)} km displayed glyph.{" "}
          {options.speedColor
            ? "Blue → cyan/yellow: low → high speed in this field."
            : "Cyan glyphs."}{" "}
          Missing components omitted; no vertical velocity.
        </p>
      )}
      <p>{status}</p>
      <small>
        Display subsampling only. Scientific values are unchanged. Translucency
        preserves coastline context.
      </small>
    </aside>
  );
}
