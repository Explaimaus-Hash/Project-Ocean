import type { Frame, Bounds } from "@/lib/api/types";
export const palettes = {
  temperature: [
    "#173c91",
    "#168bd2",
    "#24cdd0",
    "#67ce83",
    "#e5df55",
    "#f59635",
    "#cf303d",
  ],
  salinity: ["#291357", "#4149a6", "#177dbc", "#20c8d0", "#b7f3e2", "#f4f9bb"],
  chlorophyll: ["#10245c", "#136bab", "#15a99a", "#78ca62", "#f1e669"],
  speed: ["#112a63", "#127fb5", "#32c9cf", "#e9ed88"],
  anomaly: ["#254ba0", "#87b9dc", "#e9ede9", "#e78d78", "#b92c42"],
} as const;
export type Palette = keyof typeof palettes;
export interface Scale {
  min: number;
  max: number;
  palette: Palette;
  log: boolean;
}
export function defaultPalette(variable: string): Palette {
  return /sss|salin/i.test(variable)
    ? "salinity"
    : /chlor|^CHL$/i.test(variable)
      ? "chlorophyll"
      : /speed/i.test(variable)
        ? "speed"
        : /anomal|residu/i.test(variable)
          ? "anomaly"
          : "temperature";
}
export function dataRange(frame: Frame): [number, number] | null {
  let min = Infinity,
    max = -Infinity;
  for (const row of frame.values)
    for (const v of row)
      if (v !== null && Number.isFinite(v)) {
        min = Math.min(min, v);
        max = Math.max(max, v);
      }
  if (!Number.isFinite(min)) return null;
  if (min === max) {
    const pad = Math.max(Math.abs(min) * 0.01, 0.001);
    return [min - pad, max + pad];
  }
  return [min, max];
}
export function logAllowed(
  variable: string,
  units: string,
  range: [number, number] | null,
) {
  return (
    !!range &&
    range[0] > 0 &&
    /chlorophyll|chlor_a|current_speed|speed/i.test(variable) &&
    !/°|celsius|kelvin/i.test(units)
  );
}
export class ScientificColorScale {
  private stops: number[][];
  constructor(readonly settings: Scale) {
    if (
      !Number.isFinite(settings.min) ||
      !Number.isFinite(settings.max) ||
      settings.min >= settings.max ||
      (settings.log && settings.min <= 0)
    )
      throw new Error("Invalid color range");
    this.stops = palettes[settings.palette].map((hex) =>
      [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)),
    );
  }
  color(value: number | null): [number, number, number, number] {
    const target = new Uint8ClampedArray(4);
    this.write(value, target, 0);
    return Array.from(target) as [number, number, number, number];
  }
  /** Write directly to the raster: no per-pixel array allocation. */
  write(value: number | null, target: Uint8ClampedArray, offset: number) {
    const { min, max, log, palette } = this.settings;
    if (value === null || !Number.isFinite(value) || (log && value <= 0)) {
      target[offset] =
        target[offset + 1] =
        target[offset + 2] =
        target[offset + 3] =
          0;
      return;
    }
    const bounded = Math.max(min, Math.min(max, value));
    const fraction =
      palette === "anomaly" && !log
        ? bounded < 0
          ? 0.5 * (1 + bounded / Math.abs(Math.min(min, 0)))
          : 0.5 + (0.5 * bounded) / Math.max(max, Number.EPSILON)
        : log
          ? Math.log(bounded / min) / Math.log(max / min)
          : (bounded - min) / (max - min);
    const t = Math.max(0, Math.min(1, fraction));
    const pos = t * (this.stops.length - 1),
      i = Math.min(this.stops.length - 2, Math.floor(pos)),
      f = pos - i;
    for (let k = 0; k < 3; k++)
      target[offset + k] = Math.round(
        this.stops[i][k] * (1 - f) + this.stops[i + 1][k] * f,
      );
    target[offset + 3] = 255;
  }
  gradient() {
    const { min, max, log } = this.settings;
    return Array.from({ length: 33 }, (_, i) => {
      const t = i / 32,
        value = log ? min * (max / min) ** t : min + (max - min) * t;
      const [r, g, b] = this.color(value);
      return `rgb(${r},${g},${b})`;
    }).join(",");
  }
  ticks() {
    const { min, max, log } = this.settings;
    return [0, 0.25, 0.5, 0.75, 1].map((t) =>
      log ? min * (max / min) ** t : min + (max - min) * t,
    );
  }
}
export function intersect(a: Bounds, b: Bounds): Bounds | null {
  const result = {
    west: Math.max(a.west, b.west),
    east: Math.min(a.east, b.east),
    south: Math.max(a.south, b.south),
    north: Math.min(a.north, b.north),
  };
  return result.west < result.east && result.south < result.north
    ? result
    : null;
}
function axis(values: number[], longitude = false) {
  if (values.length < 2)
    throw new Error("At least two coordinates per axis are required");
  const indices = values.map((_, i) => i).sort((a, b) => values[a] - values[b]);
  const sorted = indices.map((i) => values[i]);
  if (
    sorted.some((v, i) => !Number.isFinite(v) || (i > 0 && v <= sorted[i - 1]))
  )
    throw new Error("Invalid coordinate axis");
  if (longitude && sorted.some((v, i) => i > 0 && v - sorted[i - 1] > 180))
    throw new Error("Cross-dateline grids require backend subsetting");
  if (longitude && sorted[0] >= 180)
    for (let i = 0; i < sorted.length; i++) sorted[i] -= 360;
  if (
    sorted[0] < (longitude ? -180 : -90) ||
    sorted.at(-1)! > (longitude ? 180 : 90)
  )
    throw new Error("Cross-dateline grids require backend subsetting");
  return { values: sorted, indices };
}
function bracket(axis: number[], value: number) {
  let low = 0,
    high = axis.length - 1;
  while (high - low > 1) {
    const mid = (low + high) >> 1;
    if (axis[mid] <= value) low = mid;
    else high = mid;
  }
  return {
    low,
    high,
    t: Math.max(0, Math.min(1, (value - axis[low]) / (axis[high] - axis[low]))),
  };
}
/** Display-only resampling. No measurement or comparison reads this buffer. */
export function rasterize(
  frame: Frame,
  scale: Scale,
  interpolation: "nearest" | "bilinear",
  clip: Bounds,
  size = 512,
) {
  if (frame.longitude.length * frame.latitude.length > 65536)
    throw new Error("Cell limit exceeded");
  const x = axis(frame.longitude, true),
    y = axis(frame.latitude);
  const bounds = intersect(clip, {
    west: x.values[0],
    east: x.values.at(-1)!,
    south: y.values[0],
    north: y.values.at(-1)!,
  });
  if (!bounds) throw new Error("No display overlap");
  const width = Math.min(512, Math.max(2, size)),
    height = Math.max(
      2,
      Math.round(
        width *
          Math.min(
            1,
            (bounds.north - bounds.south) / (bounds.east - bounds.west),
          ),
      ),
    );
  const pixels = new Uint8ClampedArray(width * height * 4);
  const color = new ScientificColorScale(scale);
  const xs = Array.from({ length: width }, (_, i) =>
    bracket(
      x.values,
      bounds.west + ((i + 0.5) / width) * (bounds.east - bounds.west),
    ),
  );
  const ys = Array.from({ length: height }, (_, i) =>
    bracket(
      y.values,
      bounds.north - ((i + 0.5) / height) * (bounds.north - bounds.south),
    ),
  );
  const read = (a: number, b: number) =>
    frame.values[y.indices[b]]?.[x.indices[a]] ?? null;
  for (let j = 0; j < height; j++)
    for (let i = 0; i < width; i++) {
      const a = xs[i],
        b = ys[j];
      let value: number | null = read(
        a.t < 0.5 ? a.low : a.high,
        b.t < 0.5 ? b.low : b.high,
      );
      if (interpolation === "bilinear") {
        const q00 = read(a.low, b.low),
          q10 = read(a.high, b.low),
          q01 = read(a.low, b.high),
          q11 = read(a.high, b.high);
        value =
          q00 !== null &&
          q10 !== null &&
          q01 !== null &&
          q11 !== null &&
          Number.isFinite(q00) &&
          Number.isFinite(q10) &&
          Number.isFinite(q01) &&
          Number.isFinite(q11)
            ? (q00 * (1 - a.t) + q10 * a.t) * (1 - b.t) +
              (q01 * (1 - a.t) + q11 * a.t) * b.t
            : null;
      }
      color.write(value, pixels, (j * width + i) * 4);
    }
  return { pixels, width, height, bounds };
}
