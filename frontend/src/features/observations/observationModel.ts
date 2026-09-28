import type {
  Variable,
  ObservationSample,
  ObservationCollection,
} from "@/lib/api/types";
export function markerSamples(
  samples: ObservationSample[],
  source: "argo" | "glider",
) {
  if (source === "glider") return samples;
  const seen = new Set<string>();
  return samples.filter((s) => {
    const key = s.profile_id ?? s.sample_id;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
export function trackSegments(samples: ObservationSample[]) {
  const segments: [ObservationSample, ObservationSample][] = [];
  for (let i = 1; i < samples.length; i++) {
    const a = samples[i - 1],
      b = samples[i];
    if (
      a.deployment_id &&
      a.deployment_id === b.deployment_id &&
      a.platform_id &&
      a.platform_id === b.platform_id &&
      a.sequence !== undefined &&
      b.sequence === a.sequence + 1 &&
      Date.parse(b.timestamp) > Date.parse(a.timestamp) &&
      Math.abs(b.longitude - a.longitude) < 180
    )
      segments.push([a, b]);
  }
  return segments;
}
export function profileSeries(
  samples: ObservationSample[],
  parameter: string,
  vertical: "depth_m" | "pressure_dbar",
) {
  // Sorting only the requested profile page for display; no conversion, interpolation or scientific filtering.
  const ordered = [...samples].sort(
    (a, b) => (a[vertical] ?? Infinity) - (b[vertical] ?? Infinity),
  );
  return {
    x: ordered.map((s) => s.values[parameter] ?? null),
    y: ordered.map((s) => s[vertical]),
    ids: ordered.map((s) => s.sample_id),
    missing: ordered.filter(
      (s) => s.values[parameter] == null || s[vertical] === null,
    ).length,
  };
}
export function observationDescription(
  sample: ObservationSample,
  collection: ObservationCollection,
) {
  return `${collection.source.toUpperCase()} · ${collection.mode}\nPlatform: ${sample.platform_id ?? "Not provided"}\nProfile / cycle: ${sample.profile_id ?? "Not provided"} / ${sample.cycle_id ?? "Not provided"}\n${sample.latitude.toFixed(4)}°, ${sample.longitude.toFixed(4)}°\n${sample.timestamp}\nParameters: ${
    Object.keys(sample.values)
      .filter((k) => sample.values[k] !== null)
      .join(", ") || "None"
  }\nQC: ${sample.qc}\nMode: ${sample.data_mode ?? "Not provided"}\nSource: ${collection.name}`;
}

export function profileVariableAllowed(v: Variable) {
  return (
    /^(TEMP|TEMPERATURE|PSAL|SALINITY)$/i.test(v.name) ||
    (v.normalized === true &&
      v.interpretation === "chlorophyll" &&
      !!v.units &&
      !/RFU|counts|relative/i.test(v.units))
  );
}
