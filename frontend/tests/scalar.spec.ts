import { test, expect } from "@playwright/test";
import {
  ScientificColorScale,
  rasterize,
  dataRange,
  logAllowed,
} from "../src/features/scalar/ScientificColorScale";
import { BoundedFrameLoader } from "../src/features/scalar/BoundedFrameLoader";
import { DataClient } from "../src/lib/dataClient";
import { createDemoTransport } from "../src/lib/demo/transport";
import type { Frame } from "../src/lib/api/types";
const frame: Frame = {
  schema_version: 1,
  mode: "synthetic",
  product_id: "test",
  variable: "SST",
  units: "°C",
  timestamp: "2019-01-29T00:00:00Z",
  time_index: 0,
  display_only: true,
  longitude: [50, 60],
  latitude: [-10, 10],
  values: [
    [0, 1],
    [2, null],
  ],
};
const scale = { min: 0, max: 2, palette: "temperature" as const, log: false };
const bounds = { west: 50, east: 60, south: -10, north: 10 };
test("north-up placement, zero preservation, NaN/null masking and descending axes", () => {
  const result = rasterize(frame, scale, "nearest", bounds, 2);
  expect([...result.pixels.slice(0, 4)]).toEqual(
    new ScientificColorScale(scale).color(2),
  );
  expect(result.pixels[7]).toBe(0);
  expect(result.pixels[11]).toBe(255);
  expect(dataRange(frame)).toEqual([0, 2]);
  const reversed = {
    ...frame,
    longitude: [60, 50],
    latitude: [10, -10],
    values: [
      [null, 2],
      [1, 0],
    ],
  };
  expect(rasterize(reversed, scale, "nearest", bounds, 2).pixels).toEqual(
    result.pixels,
  );
  const nan = {
    ...frame,
    values: [
      [NaN, null],
      [null, null],
    ],
  };
  expect(dataRange(nan)).toBeNull();
  expect(
    rasterize(nan, scale, "nearest", bounds, 2).pixels.every((v) => v === 0),
  ).toBe(true);
});
test("bilinear never bridges a missing neighbor; bounds clip without extrapolation", () => {
  expect(
    rasterize(frame, scale, "bilinear", bounds, 16).pixels.every(
      (v) => v === 0,
    ),
  ).toBe(true);
  const valid = {
    ...frame,
    values: [
      [0, 1],
      [2, 3],
    ],
  };
  const r = rasterize(
    valid,
    scale,
    "bilinear",
    { west: 52, east: 58, south: -5, north: 5 },
    16,
  );
  expect(r.bounds).toEqual({ west: 52, east: 58, south: -5, north: 5 });
  expect(r.pixels.filter((_, i) => i % 4 === 3).every((v) => v === 255)).toBe(
    true,
  );
  expect(() =>
    rasterize(frame, scale, "nearest", {
      west: 90,
      east: 100,
      south: 0,
      north: 10,
    }),
  ).toThrow("No display overlap");
});
test("color scale supports valid log transforms but not Celsius, missing values or bad limits", () => {
  expect(logAllowed("SST", "°C", [20, 30])).toBe(false);
  expect(logAllowed("chlorophyll", "mg/m³", [0.1, 10])).toBe(true);
  expect(logAllowed("speed", "m/s", [0, 2])).toBe(false);
  expect(
    new ScientificColorScale({
      ...scale,
      min: 0.1,
      max: 10,
      log: true,
    }).ticks()[2],
  ).toBeCloseTo(1);
  expect(new ScientificColorScale(scale).color(null)[3]).toBe(0);
  expect(
    new ScientificColorScale({
      ...scale,
      min: -1,
      max: 3,
      palette: "anomaly",
    }).color(0),
  ).toEqual([233, 237, 233, 255]);
  expect(() => new ScientificColorScale({ ...scale, min: 3 })).toThrow();
});
test("scientific 413 falls back once and remembered extent requests only preview", async () => {
  const requests: string[] = [];
  const transport = createDemoTransport("scientific-too-large", 0);
  const client = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: (url, init) => {
      requests.push(url);
      return transport(url, init);
    },
  });
  const loader = new BoundedFrameLoader(client);
  const signal = new AbortController().signal;
  for (const time_index of [0, 1])
    expect(
      (
        await loader.load(
          "demo-surface",
          { variable: "SST", quality: "scientific", bounds, time_index },
          signal,
        )
      ).display_only,
    ).toBe(true);
  expect(
    requests.filter((url) => url.includes("quality=scientific")),
  ).toHaveLength(1);
  expect(
    requests.filter((url) => url.includes("quality=preview")),
  ).toHaveLength(2);
  expect(
    requests.every((url) => url.includes("west=50") && url.includes("east=60")),
  ).toBe(true);
});
test("bounded raster preparation stays within memory and latency budget", () => {
  const dense = {
    ...frame,
    longitude: Array.from({ length: 256 }, (_, i) => 50 + i / 25.5),
    latitude: Array.from({ length: 256 }, (_, i) => -10 + i / 12.75),
    values: Array.from({ length: 256 }, (_, y) =>
      Array.from(
        { length: 256 },
        (_, x) => Math.sin(x / 20) + Math.cos(y / 20),
      ),
    ),
  };
  const start = performance.now();
  const raster = rasterize(
    dense,
    { ...scale, min: -2, max: 2 },
    "bilinear",
    bounds,
  );
  const elapsed = performance.now() - start;
  console.log(
    `Scalar raster 65,536 cells: ${elapsed.toFixed(1)} ms; ${raster.pixels.byteLength} bytes`,
  );
  expect(raster.pixels.byteLength).toBeLessThanOrEqual(1024 * 1024);
  expect(elapsed).toBeLessThan(1000);
});

test("dateline-crossing cells are rejected instead of stretched across the globe", () => {
  expect(() =>
    rasterize({ ...frame, longitude: [170, -170] }, scale, "nearest", {
      west: -180,
      east: 180,
      south: -10,
      north: 10,
    }),
  ).toThrow("Cross-dateline grids require backend subsetting");
});
