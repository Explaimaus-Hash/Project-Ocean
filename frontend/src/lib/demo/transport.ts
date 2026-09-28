import type {
  Dataset,
  Product,
  ObservationCollection,
  ObservationSample,
} from "../api/types";
import { abortableDelay, type Transport } from "../dataClient";
export const scenarios = [
  "normal",
  "backend-offline",
  "observations-unavailable",
  "product-failure",
  "busy",
  "no-overlap",
  "too-large",
  "scientific-too-large",
  "timeseries-gaps",
  "missing-frame",
  "unsupported",
  "empty",
] as const;
export type Scenario = (typeof scenarios)[number];
const envelope = { schema_version: 1 as const, mode: "synthetic" as const };
const provenance =
  "Deterministic UI fixture. Not provider measurements; not for scientific use.";
const capabilities = {
  surface: true,
  timeseries: true,
  depth: false,
  volume: false,
  vectors: false,
  current_components: [],
};
const variables = [
  { name: "SST", label: "Sea surface temperature", units: "°C" },
  { name: "SSS", label: "Sea surface salinity", units: "1" },
];
export const times = [
  "2019-01-29T00:00:00Z",
  "2019-02-28T00:00:00Z",
  "2019-03-30T00:00:00Z",
];
export const datasets: Dataset[] = [
  {
    ...envelope,
    dataset_id: "demo-bioroms",
    source_name: "BIO-ROMS V2 · demo",
    name: "Surface fixture",
    status: "prepared",
    product_id: "demo-surface",
    variables,
    capabilities,
    time_coverage: { start: times[0], end: times[2] },
  },
  {
    ...envelope,
    dataset_id: "demo-salinity",
    source_name: "UI fixture",
    name: "Salinity-only fixture",
    status: "prepared",
    product_id: "demo-salinity",
    variables: [variables[1]],
    capabilities,
    time_coverage: { start: times[0], end: times[2] },
  },
  {
    ...envelope,
    dataset_id: "demo-unprepared",
    source_name: "Copernicus · demo",
    name: "Unprepared fixture",
    status: "not_prepared",
    product_id: null,
    variables: [],
    capabilities: { ...capabilities, surface: false, timeseries: false },
    time_coverage: null,
  },
  {
    ...envelope,
    dataset_id: "demo-unavailable",
    source_name: "GODAS · demo",
    name: "Unavailable provider fixture",
    status: "provider_unavailable",
    product_id: null,
    variables: [],
    capabilities: { ...capabilities, surface: false, timeseries: false },
    time_coverage: null,
  },
];
export const products: Product[] = datasets
  .filter((d) => d.product_id)
  .map((d) => ({
    ...d,
    product_id: d.product_id!,
    times,
    depths: [],
    depth_units: null,
    bounds: { west: 50, east: 80, south: -10, north: 10 },
    provenance,
  }));
export const collections: ObservationCollection[] = ["argo", "glider"].map(
  (source) => ({
    ...envelope,
    collection_id: `demo-${source}`,
    name: `${source === "argo" ? "Argo" : "Glider"} demo collection`,
    source: source as "argo" | "glider",
    variables: [
      { name: "TEMP", label: "Temperature", units: "°C" },
      { name: "PSAL", label: "Practical salinity", units: "1" },
      ...(source === "glider"
        ? [
            {
              name: "CHLA",
              label: "Chlorophyll",
              units: "mg/m³",
              normalized: true,
              interpretation: "chlorophyll" as const,
            },
          ]
        : []),
    ],
    sample_count: source === "argo" ? 72 : 60,
    profile_count: 3,
    qc_status: "Synthetic / not scientifically evaluated",
    capabilities: {
      samples: true,
      profiles: true,
      tracks: source === "glider",
    },
    provenance,
  }),
);
export function createDemoTransport(
  scenario: Scenario = "normal",
  latency = 120,
): Transport {
  const json = (value: unknown, status = 200) =>
    Response.json(value, { status });
  const error = (code: string, status: number) =>
    json({ error: { code } }, status);
  return async (url, init) => {
    await abortableDelay(latency, init.signal ?? new AbortController().signal);
    if (scenario === "backend-offline")
      throw new TypeError("Simulated offline");
    const u = new URL(url);
    const path = u.pathname;
    const q = u.searchParams;
    if (path === "/health")
      return json({ status: "ok", service: "Project Ocean Backend" });
    if (path === "/ready")
      return json(
        {
          schema_version: 1,
          ready: false,
          reason:
            "Real prepared products are not configured. Demo fixtures cannot establish readiness.",
          required_products: [],
        },
        503,
      );
    if (path === "/api/v1/datasets")
      return json({
        ...envelope,
        datasets: scenario === "empty" ? [] : datasets,
      });
    if (path === "/api/v1/acquisitions")
      return json({
        ...envelope,
        acquisitions: [
          {
            ...envelope,
            acquisition_id: "demo-input",
            source_name: "Demo input",
            status: "acquired_not_prepared",
            provenance,
          },
        ],
      });
    if (path.startsWith("/api/v1/observations")) {
      if (scenario === "observations-unavailable")
        return error("provider_unavailable", 503);
      if (path === "/api/v1/observations")
        return json({
          ...envelope,
          collections: scenario === "empty" ? [] : collections,
        });
      const [, , , , id, action] = path.split("/");
      const collection = collections.find((c) => c.collection_id === id);
      if (!collection) return error("empty_selection", 404);
      if (!action) return json(collection);
      if (action !== "samples") return error("unsupported_selection", 404);
      const offset = Number(q.get("offset") ?? 0),
        limit = Number(q.get("limit") ?? 50);
      if (limit > 500) return error("request_too_large", 413);
      if (
        !Number.isInteger(offset) ||
        offset < 0 ||
        !Number.isInteger(limit) ||
        limit < 1
      )
        return error("unsupported_selection", 422);
      const count = collection.source === "argo" ? 72 : 60;
      const samples: ObservationSample[] = Array.from(
        { length: count },
        (_, i) => {
          const perProfile = count / 3,
            profile = Math.floor(i / perProfile),
            level = i % perProfile;
          const timestamp = new Date(
            Date.UTC(
              2019,
              0,
              29,
              collection.source === "argo" ? profile * 24 : 0,
              collection.source === "argo" ? 0 : i * 10,
            ),
          ).toISOString();
          return {
            sample_id: `${id}-${i}`,
            profile_id: `${id}-profile-${profile + 1}`,
            platform_id:
              collection.source === "argo" ? "DEMO-FLOAT-01" : "DEMO-GLIDER-01",
            cycle_id: String(profile + 1),
            deployment_id:
              collection.source === "glider" ? "DEMO-DEPLOYMENT-01" : undefined,
            data_mode: "adjusted" as const,
            sequence: i,
            timestamp,
            longitude:
              collection.source === "argo" ? 65 + profile * 4 : 66 + i * 0.12,
            latitude:
              collection.source === "argo"
                ? 2 + profile
                : 1 + Math.sin(i / 12) * 1.8,
            depth_m: collection.source === "glider" ? level * 10 : null,
            pressure_dbar: collection.source === "argo" ? level * 10 : null,
            qc: "Synthetic / not scientifically evaluated",
            values: {
              TEMP:
                level === 6
                  ? null
                  : Number((27 - level * 0.27 + profile * 0.12).toFixed(3)),
              CHLA:
                collection.source === "glider"
                  ? level === 9
                    ? null
                    : Number(
                        (
                          0.1 +
                          0.6 * Math.exp(-(((level - 8) / 4) ** 2))
                        ).toFixed(4),
                      )
                  : null,
              PSAL:
                level === 11 ? null : Number((34.6 + level * 0.018).toFixed(3)),
            },
          };
        },
      ).filter(
        (s) => !q.get("profile_id") || s.profile_id === q.get("profile_id"),
      );
      return json({
        ...envelope,
        collection_id: id,
        offset,
        limit,
        total: samples.length,
        samples: samples.slice(offset, offset + limit),
      });
    }
    const [, , , , id, action] = path.split("/");
    const product = products.find((p) => p.product_id === id);
    if (!path.startsWith("/api/v1/products/") || !product)
      return error("not_prepared", 404);
    if (scenario === "product-failure" && id === "demo-surface")
      return error("not_prepared", 409);
    if (!action) return json(product);
    const variable = product.variables.find(
      (v) => v.name === q.get("variable"),
    );
    if (!variable) return error("unsupported_selection", 422);
    if (action === "frame") {
      if (scenario === "busy") return error("busy", 503);
      if (scenario === "no-overlap") return error("no_overlap", 422);
      if (scenario === "too-large") return error("request_too_large", 413);
      if (scenario === "unsupported")
        return error("unsupported_selection", 422);
      if (
        scenario === "scientific-too-large" &&
        q.get("quality") === "scientific"
      )
        return error("request_too_large", 413);
      const index = Number(q.get("time_index"));
      if (scenario === "missing-frame" && index === 1)
        return error("empty_selection", 404);
      if (!Number.isInteger(index) || !times[index])
        return error("unsupported_selection", 422);
      const n = q.get("quality") === "scientific" ? 64 : 32;
      const longitude = Array.from(
        { length: n },
        (_, i) => 50 + (30 * i) / (n - 1),
      ).filter(
        (v) =>
          v >= Number(q.get("west") ?? 50) && v <= Number(q.get("east") ?? 80),
      );
      const latitude = Array.from(
        { length: n / 2 },
        (_, i) => -10 + (20 * i) / (n / 2 - 1),
      ).filter(
        (v) =>
          v >= Number(q.get("south") ?? -10) &&
          v <= Number(q.get("north") ?? 10),
      );
      if (longitude.length < 2 || latitude.length < 2)
        return error("no_overlap", 422);
      const values = latitude.map((lat) =>
        longitude.map((lon) => syntheticValue(variable.name, lon, lat, index)),
      );
      return json({
        ...envelope,
        product_id: id,
        variable: variable.name,
        units: variable.units,
        time_index: index,
        timestamp: times[index],
        display_only: q.get("quality") !== "scientific",
        longitude,
        latitude,
        values,
      });
    }

    if (action === "timeseries") {
      const requestedLongitude = Number(q.get("longitude")),
        requestedLatitude = Number(q.get("latitude"));
      if (
        requestedLongitude < 50 ||
        requestedLongitude > 80 ||
        requestedLatitude < -10 ||
        requestedLatitude > 10
      )
        return error("no_overlap", 422);
      const longitude =
        50 + (Math.round(((requestedLongitude - 50) / 30) * 63) * 30) / 63;
      const latitude =
        -10 + (Math.round(((requestedLatitude + 10) / 20) * 31) * 20) / 31;
      const radians = Math.PI / 180;
      const h =
        Math.sin(((latitude - requestedLatitude) * radians) / 2) ** 2 +
        Math.cos(latitude * radians) *
          Math.cos(requestedLatitude * radians) *
          Math.sin(((longitude - requestedLongitude) * radians) / 2) ** 2;
      const distance_km = 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, h)));
      return json({
        ...envelope,
        product_id: id,
        variable: variable.name,
        units: variable.units,
        longitude,
        latitude,
        distance_km,
        timestamps: times,
        values: times.map((_, i) =>
          scenario === "timeseries-gaps" && i === 1
            ? null
            : syntheticValue(variable.name, longitude, latitude, i),
        ),
      });
    }
    return error("unsupported_selection", 404);
  };
}

/** Deliberately synthetic ocean-shaped fixture, including missing cells; never a real land mask. */
function syntheticValue(
  variable: string,
  lon: number,
  lat: number,
  index: number,
): number | null {
  if (
    (lon === 50 && lat === -10) ||
    (lon < 53 && lat > 2) ||
    (lon > 73 && lat > 5) ||
    (lon - 63) ** 2 + (lat + 2) ** 2 < 2
  )
    return null;
  const wave =
    Math.sin((lon - 50) / 9 + index * 0.22) * Math.cos(lat / 7) +
    0.25 * Math.sin((lon + lat) / 3);
  return Number(
    (
      (variable === "SST" ? 26 : 35) +
      wave * (variable === "SST" ? 3 : 1) +
      index * 0.15
    ).toFixed(4),
  );
}
