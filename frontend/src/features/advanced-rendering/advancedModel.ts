import type { Product, Bounds } from "@/lib/api/types";
export type AdvancedMode = "surface" | "depth-slice" | "vectors" | "volume";
/** Internal renderer input, NOT a backend contract. A documented adapter must verify all metadata before supplying it. */
export interface AdvancedField {
  productId: string;
  variable: string;
  timestamp: string;
  units: string;
  bounds: Bounds;
  longitude: number[];
  latitude: number[];
  depths: number[];
  verticalUnit: "m";
  values: (number | null)[][][];
  currents?: {
    eastComponent: string;
    northComponent: string;
    east: (number | null)[][];
    north: (number | null)[][];
    units: "m/s";
    orientation: "east-north";
    depth: number;
  };
}
export const detailBudgets = {
  preview: { points: 1500, vectors: 150, raster: 128 },
  balanced: { points: 6000, vectors: 600, raster: 256 },
  high: { points: 16000, vectors: 1600, raster: 512 },
} as const;
export function validateField(f: AdvancedField): boolean {
  const xs = f.longitude,
    ys = f.latitude,
    zs = f.depths;
  const increasing = (v: number[]) =>
    v.length > 0 &&
    v.every((n, i) => Number.isFinite(n) && (i === 0 || n > v[i - 1]));
  const nullable = (n: number | null) => n === null || Number.isFinite(n);
  const plane = (p: (number | null)[][]) =>
    p.length === ys.length &&
    p.every((r) => r.length === xs.length && r.every(nullable));
  return (
    !!f.productId &&
    !!f.variable &&
    !!f.units &&
    Number.isFinite(Date.parse(f.timestamp)) &&
    f.verticalUnit === "m" &&
    increasing(xs) &&
    increasing(ys) &&
    increasing(zs) &&
    zs[0] >= 0 &&
    zs.at(-1)! <= 12000 &&
    xs[0] >= -180 &&
    xs.at(-1)! <= 180 &&
    ys[0] >= -90 &&
    ys.at(-1)! <= 90 &&
    xs.length * ys.length * zs.length <= 65536 &&
    Object.values(f.bounds).every(Number.isFinite) &&
    f.bounds.west >= -180 &&
    f.bounds.east <= 180 &&
    f.bounds.south >= -90 &&
    f.bounds.north <= 90 &&
    f.bounds.west <= xs[0] &&
    f.bounds.east >= xs.at(-1)! &&
    f.bounds.south <= ys[0] &&
    f.bounds.north >= ys.at(-1)! &&
    f.values.length === zs.length &&
    f.values.every(plane) &&
    (!f.currents ||
      (f.currents.orientation === "east-north" &&
        !!f.currents.eastComponent &&
        !!f.currents.northComponent &&
        f.currents.eastComponent !== f.currents.northComponent &&
        f.currents.units === "m/s" &&
        zs.includes(f.currents.depth) &&
        plane(f.currents.east) &&
        plane(f.currents.north)))
  );
}
export function capabilityModes(
  product?: Product,
  field?: AdvancedField,
  identity?: { variable?: string; timestamp?: string },
) {
  const served =
    !!product &&
    !!field &&
    validateField(field) &&
    field.productId === product.product_id &&
    field.variable === identity?.variable &&
    field.timestamp === identity?.timestamp &&
    field.units ===
      product.variables.find((v) => v.name === field.variable)?.units &&
    product.depth_units === "m" &&
    field.depths.every((z) => product.depths.includes(z));
  return {
    surface: !!product?.capabilities.surface,
    "depth-slice": served && !!product?.capabilities.depth,
    volume:
      served && !!product?.capabilities.volume && field!.depths.length > 1,
    vectors:
      served &&
      !!product?.capabilities.vectors &&
      !!field?.currents &&
      product.capabilities.current_components.includes(
        field.currents.eastComponent,
      ) &&
      product.capabilities.current_components.includes(
        field.currents.northComponent,
      ),
  };
}
export const advancedUnavailable =
  "No verified depth/current/volume payload is served by the current API. Surface-only products cannot enable these modes.";
