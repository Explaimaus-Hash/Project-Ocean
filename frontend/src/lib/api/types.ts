/** UI presentation contracts. backendAdapter explicitly maps FastAPI v1 responses. */
export type DataMode = "real" | "synthetic";
export interface Envelope {
  schema_version: 1;
  mode: DataMode;
}
export interface Health {
  status: "ok";
  service: "Project Ocean Backend";
}
export interface Readiness {
  schema_version: 1;
  ready: boolean;
  reason: string;
  required_products: string[];
}
export interface Variable {
  normalized?: boolean;
  interpretation?: "temperature" | "salinity" | "chlorophyll";
  name: string;
  label: string;
  units: string;
}
export interface Capabilities {
  surface: boolean;
  timeseries: boolean;
  depth: boolean;
  volume: boolean;
  vectors: boolean;
  current_components: string[];
}
export interface Bounds {
  west: number;
  east: number;
  south: number;
  north: number;
}
export interface Dataset extends Envelope {
  dataset_id: string;
  source_name: string;
  name: string;
  status:
    "prepared" | "not_prepared" | "not_configured" | "provider_unavailable";
  product_id: string | null;
  time_products?: { timestamp: string; product_id: string }[];
  variable_time_products?: { variable: string; times: { timestamp: string; product_id: string }[] }[];
  variables: Variable[];
  capabilities: Capabilities;
  time_coverage: { start: string; end: string } | null;
}
export interface DatasetCatalogue extends Envelope {
  datasets: Dataset[];
}
export interface Product extends Envelope {
  product_id: string;
  dataset_id: string;
  source_name: string;
  name: string;
  variables: Variable[];
  capabilities: Capabilities;
  times: string[];
  depths: number[];
  depth_units: "m" | "dbar" | null;
  bounds: Bounds;
  provenance: string;
}
export interface Frame extends Envelope {
  product_id: string;
  variable: string;
  units: string;
  time_index: number;
  timestamp: string;
  display_only: boolean;
  longitude: number[];
  latitude: number[];
  values: (number | null)[][];
}
export interface Timeseries extends Envelope {
  product_id: string;
  variable: string;
  units: string;
  longitude: number;
  latitude: number;
  distance_km: number;
  timestamps: string[];
  values: (number | null)[];
}
export interface Acquisition extends Envelope {
  acquisition_id: string;
  source_name: string;
  status: "acquired_not_prepared" | "not_configured";
  provenance: string;
}
export interface Acquisitions extends Envelope {
  acquisitions: Acquisition[];
}
export interface ObservationCollection extends Envelope {
  collection_id: string;
  name: string;
  source: "argo" | "glider";
  variables: Variable[];
  sample_count: number;
  profile_count: number | null;
  qc_status: string;
  capabilities: { samples: boolean; profiles: boolean; tracks: boolean };
  provenance: string;
}
export interface ObservationCollections extends Envelope {
  collections: ObservationCollection[];
}
export interface ObservationSample {
  provenance?: string;
  // Optional demo metadata. Must be reconciled with actual backend OpenAPI before live use.
  platform_id?: string;
  cycle_id?: string;
  deployment_id?: string;
  data_mode?: "raw" | "adjusted" | "unknown";
  sequence?: number;
  sample_id: string;
  profile_id: string | null;
  timestamp: string;
  longitude: number;
  latitude: number;
  depth_m: number | null;
  pressure_dbar: number | null;
  qc: string;
  values: Record<string, number | null>;
}
export interface ObservationSamples extends Envelope {
  collection_id: string;
  offset: number;
  limit: number;
  total: number;
  samples: ObservationSample[];
}
export interface FrameQuery {
  variable: string;
  time_index: number;
  quality?: "preview" | "scientific";
  bounds?: Bounds;
}
export interface TimeseriesQuery {
  variable: string;
  longitude: number;
  latitude: number;
}
export interface SampleQuery {
  offset?: number;
  limit?: number;
  profile_id?: string;
}
