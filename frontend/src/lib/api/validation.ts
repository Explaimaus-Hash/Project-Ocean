import type * as T from "./types";
export type Guard<T> = (value: unknown) => value is T;
const text: Guard<string> = (v): v is string =>
  typeof v === "string" && v.length <= 4096;
const number: Guard<number> = (v): v is number =>
  typeof v === "number" && Number.isFinite(v);
const integer: Guard<number> = (v): v is number =>
  number(v) && Number.isInteger(v) && v >= 0;
const bool: Guard<boolean> = (v): v is boolean => typeof v === "boolean";
function literal<const V extends string | number>(value: V): Guard<V> {
  return (v): v is V => v === value;
}
function oneOf<const V extends string>(...values: V[]): Guard<V> {
  return (v): v is V => typeof v === "string" && values.includes(v as V);
}
function optional<T>(guard: Guard<T>): Guard<T | undefined> {
  return (v): v is T | undefined => v === undefined || guard(v);
}
function nullable<T>(guard: Guard<T>): Guard<T | null> {
  return (v): v is T | null => v === null || guard(v);
}
function array<T>(guard: Guard<T>, max = 500): Guard<T[]> {
  return (v): v is T[] => Array.isArray(v) && v.length <= max && v.every(guard);
}
function shape<T extends object>(fields: {
  [K in keyof T]-?: Guard<T[K]>;
}): Guard<T> {
  return (v): v is T =>
    !!v &&
    typeof v === "object" &&
    !Array.isArray(v) &&
    Object.entries(fields).every(([key, guard]) =>
      (guard as Guard<unknown>)((v as Record<string, unknown>)[key]),
    );
}
const timestamp: Guard<string> = (v): v is string =>
  text(v) &&
  /^\d{4}-\d{2}-\d{2}T.*Z$/.test(v) &&
  Number.isFinite(Date.parse(v));
const envelope = {
  schema_version: literal(1),
  mode: oneOf("real", "synthetic"),
};
const variable = shape<T.Variable>({
  name: text,
  label: text,
  units: text,
  normalized: optional(bool),
  interpretation: optional(oneOf("temperature", "salinity", "chlorophyll")),
});
const capabilities = shape<T.Capabilities>({
  surface: bool,
  timeseries: bool,
  depth: bool,
  volume: bool,
  vectors: bool,
  current_components: array(text, 3),
});
const boundsShape = shape<T.Bounds>({
  west: number,
  east: number,
  south: number,
  north: number,
});
export const validBounds: Guard<T.Bounds> = (v): v is T.Bounds =>
  boundsShape(v) &&
  v.west >= -180 &&
  v.east <= 180 &&
  v.west < v.east &&
  v.south >= -90 &&
  v.north <= 90 &&
  v.south < v.north;
const dataset = shape<T.Dataset>({
  ...envelope,
  dataset_id: text,
  source_name: text,
  name: text,
  status: oneOf(
    "prepared",
    "not_prepared",
    "not_configured",
    "provider_unavailable",
  ),
  product_id: nullable(text),
  time_products: optional(array(shape({timestamp, product_id:text}),1536)),
  variable_time_products: optional(array(shape({variable:text, times:array(shape({timestamp,product_id:text}),1536)}),64)),
  variables: array(variable, 64),
  capabilities,
  time_coverage: nullable(shape({ start: timestamp, end: timestamp })),
});
const productShape = shape<T.Product>({
  ...envelope,
  product_id: text,
  dataset_id: text,
  source_name: text,
  name: text,
  variables: array(variable, 64),
  capabilities,
  times: array(timestamp, 10000),
  depths: array(number, 10000),
  depth_units: nullable(oneOf("m", "dbar")),
  bounds: validBounds,
  provenance: text,
});
const frameShape = shape<T.Frame>({
  ...envelope,
  product_id: text,
  variable: text,
  units: text,
  time_index: integer,
  timestamp,
  display_only: bool,
  longitude: array(number, 65536),
  latitude: array(number, 65536),
  values: array(array(nullable(number), 65536), 65536),
});
const timeseriesShape = shape<T.Timeseries>({
  ...envelope,
  product_id: text,
  variable: text,
  units: text,
  longitude: number,
  latitude: number,
  distance_km: number,
  timestamps: array(timestamp, 10000),
  values: array(nullable(number), 10000),
});
const collection = shape<T.ObservationCollection>({
  ...envelope,
  collection_id: text,
  name: text,
  source: oneOf("argo", "glider"),
  variables: array(variable, 64),
  sample_count: integer,
  profile_count: nullable(integer),
  qc_status: text,
  capabilities: shape({ samples: bool, profiles: bool, tracks: bool }),
  provenance: text,
});
const numericRecord: Guard<Record<string, number | null>> = (
  v,
): v is Record<string, number | null> =>
  !!v &&
  typeof v === "object" &&
  !Array.isArray(v) &&
  Object.keys(v).length <= 64 &&
  Object.values(v).every(nullable(number));
const sample = shape<T.ObservationSample>({
  provenance: optional(text),
  platform_id: optional(text),
  cycle_id: optional(text),
  deployment_id: optional(text),
  data_mode: optional(oneOf("raw", "adjusted", "unknown")),
  sequence: optional(integer),
  sample_id: text,
  profile_id: nullable(text),
  timestamp,
  longitude: (v): v is number => number(v) && Math.abs(v) <= 180,
  latitude: (v): v is number => number(v) && Math.abs(v) <= 90,
  depth_m: nullable(number),
  pressure_dbar: nullable(number),
  qc: text,
  values: numericRecord,
});
const samplesShape = shape<T.ObservationSamples>({
  ...envelope,
  collection_id: text,
  offset: integer,
  limit: integer,
  total: integer,
  samples: array(sample, 500),
});
export const validators = {
  health: shape<T.Health>({
    status: literal("ok"),
    service: literal("Project Ocean Backend"),
  }),
  readiness: shape<T.Readiness>({
    schema_version: literal(1),
    ready: bool,
    reason: text,
    required_products: array(text, 16),
  }),
  datasets: shape<T.DatasetCatalogue>({
    ...envelope,
    datasets: array(dataset, 128),
  }),
  product: ((v): v is T.Product =>
    productShape(v) &&
    new Set(v.times).size === v.times.length &&
    v.times.every((time, i) => i === 0 || time > v.times[i - 1]) &&
    new Set(v.variables.map((x) => x.name)).size === v.variables.length &&
    (!v.capabilities.depth ||
      (v.depths.length > 0 && v.depth_units !== null))) as Guard<T.Product>,
  frame: ((v): v is T.Frame =>
    frameShape(v) &&
    v.longitude.length * v.latitude.length <= 65536 &&
    v.values.length === v.latitude.length &&
    v.values.every(
      (row) => row.length === v.longitude.length,
    )) as Guard<T.Frame>,
  timeseries: ((v): v is T.Timeseries =>
    timeseriesShape(v) &&
    v.timestamps.length === v.values.length &&
    Math.abs(v.longitude) <= 180 &&
    Math.abs(v.latitude) <= 90 &&
    v.distance_km >= 0 &&
    v.timestamps.every(
      (time, i) =>
        i === 0 || Date.parse(time) > Date.parse(v.timestamps[i - 1]),
    )) as Guard<T.Timeseries>,
  acquisitions: shape<T.Acquisitions>({
    ...envelope,
    acquisitions: array(
      shape<T.Acquisition>({
        ...envelope,
        acquisition_id: text,
        source_name: text,
        status: oneOf("acquired_not_prepared", "not_configured"),
        provenance: text,
      }),
      128,
    ),
  }),
  collections: shape<T.ObservationCollections>({
    ...envelope,
    collections: array(collection, 128),
  }),
  collection,
  samples: ((v): v is T.ObservationSamples =>
    samplesShape(v) &&
    v.limit <= 500 &&
    v.samples.length <= v.limit &&
    (v.samples.length === 0 ||
      v.offset + v.samples.length <= v.total)) as Guard<T.ObservationSamples>,
};
