"use client";
import { useEffect, useRef } from "react";
import type { Entity, Cartesian2 } from "cesium";
import { useGlobe } from "@/features/globe/GlobeContext";
import { loadCesium } from "@/lib/loadCesium";
export interface GeographicPoint {
  longitude: number;
  latitude: number;
}
/** Path interaction is dormant until a verified transect adapter explicitly enables it. */
export function useGeographicSelection({
  mode,
  allowPath = false,
  onPoint,
  onPath,
  requested,
  actual,
  highlight = false,
}: {
  mode: "none" | "point" | "path";
  allowPath?: boolean;
  onPoint: (point: GeographicPoint) => void;
  onPath?: (path: GeographicPoint[]) => void;
  requested?: GeographicPoint;
  actual?: GeographicPoint;
  highlight?: boolean;
}) {
  const { viewer } = useGlobe();
  const callbacks = useRef({ onPoint, onPath });
  callbacks.current = { onPoint, onPath };
  useEffect(() => {
    if (
      !viewer ||
      viewer.isDestroyed() ||
      mode === "none" ||
      (mode === "path" && !allowPath)
    )
      return;
    let active = true;
    let cleanup: (() => void) | undefined;
    void loadCesium().then((C) => {
      if (!active || viewer.isDestroyed()) return;
      const handler = new C.ScreenSpaceEventHandler(viewer.canvas);
      const point = new C.Cartesian3(),
        cartographic = new C.Cartographic();
      const path: GeographicPoint[] = [];
      let pathEntity: Entity | undefined;
      viewer.canvas.style.cursor = "crosshair";
      handler.setInputAction(({ position }: { position: Cartesian2 }) => {
        if (viewer.scene.pick(position)?.id?.kind === "ocean-observation")
          return;
        const hit = viewer.camera.pickEllipsoid(
          position,
          viewer.scene.globe.ellipsoid,
          point,
        );
        if (!hit) return;
        C.Cartographic.fromCartesian(
          hit,
          viewer.scene.globe.ellipsoid,
          cartographic,
        );
        const coordinate = {
          longitude: C.Math.toDegrees(cartographic.longitude),
          latitude: C.Math.toDegrees(cartographic.latitude),
        };
        if (mode === "point") callbacks.current.onPoint(coordinate);
        else if (path.length < 64) {
          path.push(coordinate);
          if (pathEntity) viewer.entities.remove(pathEntity);
          if (path.length >= 2)
            pathEntity = viewer.entities.add({
              polyline: {
                positions: path.map((p) =>
                  C.Cartesian3.fromDegrees(p.longitude, p.latitude, 600),
                ),
                width: 2,
                material: C.Color.ORANGE,
              },
            });
          callbacks.current.onPath?.([...path]);
          viewer.scene.requestRender();
        }
      }, C.ScreenSpaceEventType.LEFT_CLICK);
      cleanup = () => {
        handler.destroy();
        viewer.canvas.style.cursor = "";
        if (!viewer.isDestroyed() && pathEntity)
          viewer.entities.remove(pathEntity);
      };
    });
    return () => {
      active = false;
      cleanup?.();
    };
  }, [viewer, mode, allowPath]);
  const key = JSON.stringify({ requested, actual, highlight });
  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;
    let active = true;
    const entities: Entity[] = [];
    void loadCesium().then((C) => {
      if (!active || viewer.isDestroyed()) return;
      for (const [label, point, color] of [
        ["Requested coordinate", requested, C.Color.ORANGE],
        ["Returned grid cell", actual, C.Color.CYAN],
      ] as const) {
        if (point)
          entities.push(
            viewer.entities.add({
              name: label,
              position: C.Cartesian3.fromDegrees(
                point.longitude,
                point.latitude,
                900,
              ),
              point: {
                pixelSize: label === "Returned grid cell" && highlight ? 16 : 8,
                color,
                outlineColor: C.Color.WHITE,
                outlineWidth: 1,
              },
            }),
          );
      }
      viewer.scene.requestRender();
    });
    return () => {
      active = false;
      if (!viewer.isDestroyed()) {
        for (const entity of entities) viewer.entities.remove(entity);
        viewer.scene.requestRender();
      }
    };
  }, [viewer, key]);
}
