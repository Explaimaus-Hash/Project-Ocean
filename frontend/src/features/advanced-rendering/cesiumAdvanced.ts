import type { Viewer, PrimitiveCollection } from "cesium";
import type { AdvancedField } from "./advancedModel";
import { validateField, detailBudgets } from "./advancedModel";
type C = typeof import("cesium");
export interface RenderOptions {
  quality: keyof typeof detailBudgets;
  exaggeration: number;
  depthIndex: number;
  density: number;
  vectorScale: number;
  speedColor: boolean;
}
/** Longitude/latitude -> WGS84 ECEF at ellipsoid height -depth(m)*display exaggeration. */
export function buildAdvanced(
  C: C,
  viewer: Viewer,
  field: AdvancedField,
  mode: "depth-slice" | "volume" | "vectors",
  options: RenderOptions,
) {
  if (!validateField(field)) throw new Error("Invalid bounded advanced field");
  if (
    !Number.isFinite(options.exaggeration) ||
    options.exaggeration < 1 ||
    options.exaggeration > 10 ||
    !Number.isInteger(options.depthIndex) ||
    options.depthIndex < 0 ||
    options.depthIndex >= field.depths.length ||
    !Number.isFinite(options.density) ||
    options.density < 0.1 ||
    options.density > 1 ||
    !Number.isFinite(options.vectorScale) ||
    options.vectorScale < 100 ||
    options.vectorScale > 20000
  )
    throw new Error("Invalid display settings");
  const started = performance.now();
  const primitives: PrimitiveCollection = viewer.scene.primitives.add(
    new C.PrimitiveCollection(),
  );
  const budget = detailBudgets[options.quality];
  let count = 0;
  try {
    if (mode === "vectors") {
      const currents = field.currents;
      if (!currents) throw new Error("Verified east/north fields required");
      const collection = primitives.add(new C.PolylineCollection());
      const total = field.longitude.length * field.latitude.length;
      const adaptive = Math.min(
        1,
        Math.max(
          0.2,
          2000000 / Math.max(viewer.camera.positionCartographic.height, 1),
        ),
      );
      const stride = Math.max(
        1,
        Math.ceil(total / (budget.vectors * options.density * adaptive)),
      );
      let maxSpeed = 0;
      for (let y = 0; y < field.latitude.length; y++)
        for (let x = 0; x < field.longitude.length; x++) {
          const u = currents.east[y][x],
            v = currents.north[y][x];
          if (u !== null && v !== null)
            maxSpeed = Math.max(maxSpeed, Math.hypot(u, v));
        }
      for (let i = 0; i < total; i += stride) {
        const y = Math.floor(i / field.longitude.length),
          x = i % field.longitude.length;
        const u = currents.east[y][x],
          v = currents.north[y][x];
        if (u === null || v === null || (u === 0 && v === 0)) continue;
        const start = C.Cartesian3.fromDegrees(
          field.longitude[x],
          field.latitude[y],
          -currents.depth * options.exaggeration,
        );
        // Local east and north basis, zero up component; never invent w.
        const enu = C.Transforms.eastNorthUpToFixedFrame(start);
        const end = C.Matrix4.multiplyByPoint(
          enu,
          new C.Cartesian3(u * options.vectorScale, v * options.vectorScale, 0),
          new C.Cartesian3(),
        );
        const speed = Math.hypot(u, v),
          t = maxSpeed ? speed / maxSpeed : 0;
        const color = options.speedColor
          ? new C.Color(0.1 + 0.85 * t, 0.4 + 0.55 * t, 0.8 - 0.5 * t, 1)
          : C.Color.CYAN;
        collection.add({
          positions: [start, end],
          width: 2,
          material: C.Material.fromType("PolylineArrow", { color }),
        });
        count++;
      }
    } else {
      const points = primitives.add(new C.PointPrimitiveCollection());
      const levels =
        mode === "depth-slice"
          ? [options.depthIndex]
          : field.depths.map((_, i) => i);
      const total =
        field.longitude.length * field.latitude.length * levels.length;
      const stride = Math.max(1, Math.ceil(total / budget.points));
      let min = Infinity,
        max = -Infinity;
      for (const z of levels)
        for (const row of field.values[z])
          for (const v of row)
            if (v !== null) {
              min = Math.min(min, v);
              max = Math.max(max, v);
            }
      for (let i = 0; i < total; i += stride) {
        const plane = field.longitude.length * field.latitude.length,
          z = levels[Math.floor(i / plane)],
          y = Math.floor((i % plane) / field.longitude.length),
          x = i % field.longitude.length,
          v = field.values[z][y][x];
        if (v === null) continue;
        const t = max > min ? (v - min) / (max - min) : 0.5;
        points.add({
          position: C.Cartesian3.fromDegrees(
            field.longitude[x],
            field.latitude[y],
            -field.depths[z] * options.exaggeration,
          ),
          pixelSize: mode === "volume" ? 5 : 7,
          color: new C.Color(
            0.1 + 0.8 * t,
            0.4 + 0.5 * t,
            0.9 - 0.5 * t,
            mode === "volume" ? 0.55 : 1,
          ),
          id: {
            kind: "ocean-advanced-sample",
            value: v,
            units: field.units,
            depth: field.depths[z],
            timestamp: field.timestamp,
          },
        });
        count++;
      }
    }
    viewer.scene.requestRender();
    return {
      count,
      milliseconds: performance.now() - started,
      destroy: () => {
        if (!viewer.isDestroyed()) {
          viewer.scene.primitives.remove(primitives);
          viewer.scene.requestRender();
        }
      },
    };
  } catch (error) {
    if (!viewer.isDestroyed()) viewer.scene.primitives.remove(primitives);
    throw error;
  }
}
