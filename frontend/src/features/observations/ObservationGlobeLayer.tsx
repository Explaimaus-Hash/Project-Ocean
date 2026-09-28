"use client";
import { useEffect, useRef } from "react";
import type {
  PointPrimitive,
  PointPrimitiveCollection,
  Cartesian2,
} from "cesium";
import { useGlobe } from "@/features/globe/GlobeContext";
import { useData } from "@/features/data-sources/DataProvider";
import { useSelection } from "@/lib/selection";
import { loadCesium } from "@/lib/loadCesium";
import {
  markerSamples,
  trackSegments,
  observationDescription,
} from "./observationModel";
export function ObservationGlobeLayer() {
  const { viewer } = useGlobe();
  const d = useData();
  const { selection, dispatch } = useSelection();
  const tooltip = useRef<HTMLDivElement>(null);
  const points = useRef<Map<string, PointPrimitive>>(new Map());
  const ring = useRef<PointPrimitive | null>(null);
  const collection = d.collectionDetail.value;
  const samples = d.samples.value;
  const selected = selection.selectedObservation;
  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || !collection || !samples) return;
    let disposed = false;
    let cleanup: (() => void) | undefined;
    void loadCesium().then((C) => {
      if (disposed || viewer.isDestroyed()) return;
      const markers = markerSamples(samples.samples, collection.source);
      const pointCollection: PointPrimitiveCollection =
        viewer.scene.primitives.add(new C.PointPrimitiveCollection());
      const lines = viewer.scene.primitives.add(new C.PolylineCollection());
      const color =
        collection.source === "argo"
          ? C.Color.CYAN
          : C.Color.fromCssColorString("#ffba55");
      for (const sample of markers) {
        const point = pointCollection.add({
          position: C.Cartesian3.fromDegrees(
            sample.longitude,
            sample.latitude,
            600,
          ),
          pixelSize: collection.source === "argo" ? 9 : 3,
          color,
          outlineColor: color.withAlpha(0.25),
          outlineWidth: collection.source === "argo" ? 3 : 0.5,
          scaleByDistance: new C.NearFarScalar(1e5, 1.3, 3e7, 0.75),
          id: { kind: "ocean-observation", sampleId: sample.sample_id },
        });
        points.current.set(sample.sample_id, point);
      }
      ring.current = pointCollection.add({
        position: C.Cartesian3.ZERO,
        pixelSize: 19,
        color: C.Color.TRANSPARENT,
        outlineColor: C.Color.WHITE.withAlpha(0.95),
        outlineWidth: 1.5,
        show: false,
      });
      if (collection.source === "glider" && collection.capabilities.tracks) {
        const segments = trackSegments(samples.samples);
        for (const [index, [a, b]] of segments.entries())
          lines.add({
            positions: [
              C.Cartesian3.fromDegrees(a.longitude, a.latitude, 500),
              C.Cartesian3.fromDegrees(b.longitude, b.latitude, 500),
            ],
            width:
              index % 10 === 9 || index === segments.length - 1 ? 3.5 : 1.5,
            material: C.Material.fromType(
              index % 10 === 9 || index === segments.length - 1
                ? "PolylineArrow"
                : "Color",
              { color: color.withAlpha(0.8) },
            ),
          });
      }
      const handler = new C.ScreenSpaceEventHandler(viewer.canvas);
      let lastHover = 0;
      const pick = (position: Cartesian2) => {
        const hit = viewer.scene.pick(position);
        return hit?.id?.kind === "ocean-observation"
          ? samples.samples.find((s) => s.sample_id === hit.id.sampleId)
          : undefined;
      };
      handler.setInputAction(({ position }: { position: Cartesian2 }) => {
        const sample = pick(position);
        if (sample)
          dispatch({
            type: "select-observation-sample",
            value: {
              collectionId: collection.collection_id,
              sampleId: sample.sample_id,
              profileId: sample.profile_id,
              source: collection.source,
            },
          });
      }, C.ScreenSpaceEventType.LEFT_CLICK);
      handler.setInputAction(({ endPosition }: { endPosition: Cartesian2 }) => {
        if (performance.now() - lastHover < 40) return;
        lastHover = performance.now();
        const sample = pick(endPosition);
        const tip = tooltip.current;
        if (!tip) return;
        tip.hidden = !sample;
        if (sample) {
          tip.textContent = observationDescription(sample, collection);
          tip.style.left = `${Math.max(8, Math.min(endPosition.x + 14, viewer.canvas.clientWidth - 270))}px`;
          tip.style.top = `${Math.max(8, Math.min(endPosition.y + 14, viewer.canvas.clientHeight - 240))}px`;
        }
      }, C.ScreenSpaceEventType.MOUSE_MOVE);
      const leave = () => {
        if (tooltip.current) tooltip.current.hidden = true;
      };
      viewer.canvas.addEventListener("pointerleave", leave);
      viewer.scene.requestRender();
      cleanup = () => {
        handler.destroy();
        viewer.canvas.removeEventListener("pointerleave", leave);
        leave();
        points.current.clear();
        ring.current = null;
        if (!viewer.isDestroyed()) {
          viewer.scene.primitives.remove(pointCollection);
          viewer.scene.primitives.remove(lines);
          viewer.scene.requestRender();
        }
      };
    });
    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [viewer, collection, samples, dispatch]);
  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;
    const highlight = () => {
      if (viewer.isDestroyed()) return;
      let point = selected ? points.current.get(selected.sampleId) : undefined;
      if (!point && selected?.profileId && collection?.source === "argo") {
        const representative = samples?.samples.find(
          (s) => s.profile_id === selected.profileId,
        );
        if (representative)
          point = points.current.get(representative.sample_id);
      }
      if (ring.current) {
        ring.current.show = !!point;
        if (point) ring.current.position = point.position;
      }
      viewer.scene.requestRender();
    };
    void loadCesium().then(highlight);
  }, [viewer, selected, collection, samples]);
  return (
    <>
      <div className="observation-hover" ref={tooltip} role="tooltip" hidden />
      {collection && samples && (
        <div className="observation-map-key">
          {collection.source === "argo"
            ? collection.capabilities.profiles ? "● Argo profiles" : "● Argo samples"
            : "━ Glider samples"}{" "}
          · {collection.mode}
          <small>
            {samples.samples.length} samples on this page · discrete
            observations
            {collection.source === "glider"
              ? " · lines connect ordered samples only"
              : ""}
          </small>
        </div>
      )}
    </>
  );
}
