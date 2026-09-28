import type { Frame } from "@/lib/api/types";
/** Reads a returned frame cell, never the rendered canvas or interpolated pixels. */
export function modelCell(
  frame: Frame,
  point: { longitude: number; latitude: number },
) {
  const xs = frame.longitude,
    ys = frame.latitude;
  if (
    !xs.length ||
    !ys.length ||
    !Number.isFinite(point.longitude) ||
    !Number.isFinite(point.latitude) ||
    point.longitude < Math.min(xs[0], xs.at(-1)!) ||
    point.longitude > Math.max(xs[0], xs.at(-1)!) ||
    point.latitude < Math.min(ys[0], ys.at(-1)!) ||
    point.latitude > Math.max(ys[0], ys.at(-1)!)
  )
    return null;
  const nearest = (axis: number[], n: number) =>
    axis.reduce(
      (best, v, i) => (Math.abs(v - n) < Math.abs(axis[best] - n) ? i : best),
      0,
    );
  const x = nearest(xs, point.longitude),
    y = nearest(ys, point.latitude);
  const value = frame.values[y]?.[x];
  return {
    longitude: xs[x],
    latitude: ys[y],
    value: typeof value === "number" && Number.isFinite(value) ? value : null,
    row: y,
    column: x,
  };
}
