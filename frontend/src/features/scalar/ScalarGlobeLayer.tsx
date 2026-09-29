"use client";
import {
  detailBudgets,
  capabilityModes,
} from "@/features/advanced-rendering/advancedModel";
import { useSelection } from "@/lib/selection";
import { useEffect, useRef, useState } from "react";
import type { ImageryLayer, Entity } from "cesium";
import { loadCesium } from "@/lib/loadCesium";
import { useGlobe } from "@/features/globe/GlobeContext";
import { useData } from "@/features/data-sources/DataProvider";
import { useScalar } from "./ScalarContext";
import { rasterize, ScientificColorScale } from "./ScientificColorScale";
export function ScalarGlobeLayer() {
  const { viewer, settings } = useGlobe();
  const { selection } = useSelection();
  const d = useData();
  const advanced =
    selection.renderMode !== "surface" &&
    capabilityModes(d.product.value, d.advancedField, {
      variable: d.variable,
      timestamp: d.timestamp,
    })[selection.renderMode];
  const s = useScalar();
  const current = useRef<ImageryLayer | null>(null);
  const currentTime = useRef<string | null>(null);
  const fade = useRef<{ finish: (publish?: boolean) => void; refresh: () => void } | null>(null);
  const [transition, setTransition] = useState<{family: string; from: string; to: string} | null>(null);
  const motion = useRef(settings.reducedAnimation);
  motion.current = settings.reducedAnimation;
  const frame = d.displayedFrame;
  const scaleKey = JSON.stringify(s.scale);
  const boundsKey = JSON.stringify(d.bounds);
  const { setRenderInfo, setRenderError } = s;
  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || !d.bounds || !s.settings.visible)
      return;
    let disposed = false;
    let outline: Entity | undefined;
    const bounds = d.bounds;
    void loadCesium().then((C) => {
      if (disposed || viewer.isDestroyed()) return;
      outline = viewer.entities.add({
        name: "Requested scalar extent; valid cells determine coverage",
        rectangle: {
          coordinates: C.Rectangle.fromDegrees(
            bounds.west,
            bounds.south,
            bounds.east,
            bounds.north,
          ),
          height: 100,
          fill: false,
          outline: true,
          outlineColor: C.Color.CYAN.withAlpha(0.45),
        },
      });
      viewer.scene.requestRender();
    });
    return () => {
      disposed = true;
      if (outline && !viewer.isDestroyed()) {
        viewer.entities.remove(outline);
        viewer.scene.requestRender();
      }
    };
  }, [viewer, boundsKey, s.settings.visible]);

  useEffect(() => {
    return () => {
      fade.current?.finish(false);
      if (viewer && !viewer.isDestroyed() && current.current)
        viewer.imageryLayers.remove(current.current, true);
      current.current = null;
      currentTime.current = null;
    };
  }, [viewer, d.family]);
  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || !frame || !d.bounds || !s.scale)
      return;
    let cancelled = false;
    let url: string | undefined;
    const started = performance.now();
    const scale = s.scale;
    const bounds = d.bounds;
    const interpolation = s.settings.interpolation;
    setRenderError("");
    void (async () => {
      try {
        const C = await loadCesium();
        if (cancelled || viewer.isDestroyed()) return;
        const raster = rasterize(
          frame,
          scale,
          interpolation,
          bounds,
          detailBudgets[settings.quality].raster,
        );
        const canvas = document.createElement("canvas");
        canvas.width = raster.width;
        canvas.height = raster.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("Canvas unavailable");
        const image = ctx.createImageData(raster.width, raster.height);
        image.data.set(raster.pixels);
        ctx.putImageData(image, 0, 0);
        const blob = await new Promise<Blob>((resolve, reject) =>
          canvas.toBlob(
            (b) =>
              b ? resolve(b) : reject(new Error("Raster encoding failed")),
            "image/png",
          ),
        );
        if (cancelled || viewer.isDestroyed()) return;
        url = URL.createObjectURL(blob);
        const provider = await C.SingleTileImageryProvider.fromUrl(url, {
          rectangle: C.Rectangle.fromDegrees(
            raster.bounds.west,
            raster.bounds.south,
            raster.bounds.east,
            raster.bounds.north,
          ),
          credit: new C.Credit(
            frame.mode === "synthetic"
              ? "Project Ocean · synthetic scalar demonstration"
              : "Project Ocean scalar field",
          ),
        });
        if (cancelled || viewer.isDestroyed()) return;
        // Finish any superseded fade before adding another layer: at most two
        // scalar rasters coexist, even during rapid scrubbing.
        fade.current?.finish();
        const previous = current.current;
        const animate = previous && currentTime.current !== frame.timestamp &&
          latest.current.visible && !motion.current &&
          !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const layer = new C.ImageryLayer(provider, {
          alpha: animate ? 0.001 : latest.current.opacity,
          show: latest.current.visible,
          minificationFilter: C.TextureMinificationFilter.NEAREST,
          magnificationFilter: C.TextureMagnificationFilter.NEAREST,
        });
        viewer.imageryLayers.add(layer);
        current.current = layer;
        viewer.scene.requestRender();
        const info = {
          family: d.family,
          frame,
          scale,
          interpolation,
          milliseconds: performance.now() - started,
          width: raster.width,
          height: raster.height,
        };
        const publish = () => {
          currentTime.current = frame.timestamp;
          setRenderInfo(info);
          setTransition(null);
        };
        if (!animate) {
          if (previous) viewer.imageryLayers.remove(previous, true);
          publish();
        } else {
          setTransition({family:d.family, from:currentTime.current!, to:frame.timestamp});
          let raf = 0;
          let start: number | undefined;
          let warmup = 2;
          let progress = 0;
          let done = false;
          const refresh = () => {
            if (viewer.isDestroyed() || done) return;
            const opacity = latest.current.opacity;
            layer.alpha = Math.max(0.001, opacity * progress);
            // Compensate source-over compositing to avoid a brightness dip
            // where both frames are valid; missing masks remain transparent.
            previous.alpha = opacity * (1-progress) / Math.max(1-opacity*progress, 0.0001);
            layer.show = previous.show = latest.current.visible;
            viewer.scene.requestRender();
          };
          const finish = (commit = true) => {
            if (done) return;
            done = true;
            cancelAnimationFrame(raf);
            if (!viewer.isDestroyed()) {
              viewer.imageryLayers.remove(previous, true);
              layer.alpha = latest.current.opacity;
              layer.show = latest.current.visible;
              viewer.scene.requestRender();
            }
            fade.current = null;
            if (commit) publish();
          };
          const tick = (now: number) => {
            if (viewer.isDestroyed()) { finish(false); return; }
            if (motion.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { finish(); return; }
            // Let Cesium attach/upload the new raster before fading the old one.
            if (warmup-- > 0) {
              viewer.scene.requestRender();
              raf = requestAnimationFrame(tick);
              return;
            }
            start ??= now;
            const t = Math.min(1, (now-start)/480);
            progress = t*t*(3-2*t);
            refresh();
            if (t === 1) finish();
            else raf = requestAnimationFrame(tick);
          };
          fade.current = {finish, refresh};
          raf = requestAnimationFrame(tick);
        }
      } catch (error) {
        if (!cancelled) {
          setRenderError(
            error instanceof Error &&
              error.message ===
                "Cross-dateline grids require backend subsetting"
              ? "This grid crosses the dateline. Request a bounded region before rendering."
              : "The field could not be rendered. The previous labeled frame is retained.",
          );
        }
      } finally {
        if (url) URL.revokeObjectURL(url);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Immutable frame/serialized settings are the render inputs, not camera frames.
  }, [
    viewer,
    frame,
    d.family,
    boundsKey,
    scaleKey,
    s.settings.interpolation,
    settings.quality,
    setRenderInfo,
    setRenderError,
  ]);
  const latest = useRef(s.settings);
  latest.current = { ...s.settings, visible: s.settings.visible && !advanced };
  useEffect(() => {
    if (viewer && !viewer.isDestroyed() && current.current) {
      if (fade.current) {
        fade.current.refresh();
        return;
      }
      current.current.alpha = s.settings.opacity;
      current.current.show =
        s.settings.visible &&
        (selection.renderMode === "surface" ||
          !capabilityModes(d.product.value, d.advancedField, {
            variable: d.variable,
            timestamp: d.timestamp,
          })[selection.renderMode]);
      viewer.scene.requestRender();
    }
  }, [
    viewer,
    s.settings.opacity,
    s.settings.visible,
    selection.renderMode,
    d.advancedField,
    d.product.value,
    d.variable,
    d.timestamp,
  ]);
  const info = s.renderInfo;
  if (!info || !s.settings.visible || advanced) return null;
  const ticks = new ScientificColorScale(info.scale).ticks();
  const loading = !d.frame.value || info.frame !== d.frame.value;
  const blending = transition?.family === d.family ? transition : null;
  const variable = d.displayProduct?.variables.find(
    (v) => v.name === info.frame.variable,
  );
  return (
    <aside
      className="scientific-colorbar"
      aria-label="Scientific colorbar"
      data-product={info.frame.product_id}
      data-variable={info.frame.variable}
      data-timestamp={info.frame.timestamp}
      data-min={info.scale.min}
      data-max={info.scale.max}
      data-transition={blending ? "blending" : "idle"}
      data-transition-to={blending?.to}
    >
      <strong>
        {variable?.label ?? info.frame.variable}{" "}
        <span>({info.frame.units})</span>
      </strong>
      <div
        className="colorbar-gradient"
        style={{
          background: `linear-gradient(var(--bar-direction, to right), ${new ScientificColorScale(info.scale).gradient()})`,
        }}
      />
      <div className="colorbar-ticks">
        {ticks.map((t, i) => (
          <span key={i}>{Number(t.toPrecision(4))}</span>
        ))}
      </div>
      <small className="colorbar-dataset">
        Dataset: {d.displayProduct?.source_name ?? "incois_bio_roms"}
      </small>
      <div className="visually-hidden">
        <small>
          <span className="missing-swatch" /> Missing / land: transparent ·{" "}
          {info.scale.log ? "Log" : "Linear"}
        </small>
        <small>
          {info.frame.mode === "synthetic" ? "SYNTHETIC DEMO · " : ""}
          {info.frame.display_only ? "Preview" : "Scientific quality"} ·{" "}
          {info.frame.longitude.length}×{info.frame.latitude.length} frame cells
        </small>
        <small>
          {d.displayProduct?.source_name} · {info.frame.product_id} · Palette:{" "}
          {info.scale.palette}
        </small>
        <time dateTime={info.frame.timestamp}>{info.frame.timestamp}</time>
        {blending && <small role="status">Visual fade: {blending.from} → {blending.to} · display only, not intermediate measurements</small>}
        <small role="status">
          {d.frame.error || d.product.error
            ? "Frame request failed — previous frame shown"
            : blending
              ? "Transitioning to next source frame"
            : loading
              ? "Loading next frame — previous timestamp retained"
              : s.renderError || "Displayed frame"}{" "}
          · {info.interpolation} display
        </small>
      </div>
    </aside>
  );
}
