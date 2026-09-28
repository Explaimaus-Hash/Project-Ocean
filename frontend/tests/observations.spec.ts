import { test, expect } from "@playwright/test";
import { DataClient } from "../src/lib/dataClient";
import { createDemoTransport } from "../src/lib/demo/transport";
import {
  markerSamples,
  trackSegments,
  profileSeries,
  profileVariableAllowed,
} from "../src/features/observations/observationModel";
test("observation requests are paged and profile-scoped with missing values and explicit units", async () => {
  const urls: string[] = [];
  const transport = createDemoTransport("normal", 0);
  const client = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: (url, init) => {
      urls.push(url);
      return transport(url, init);
    },
  });
  const collection = await client.getObservationCollection("demo-argo");
  expect(collection.variables[0].units).toBe("°C");
  const first = await client.getObservationSamples("demo-argo", { limit: 50 });
  const second = await client.getObservationSamples("demo-argo", {
    offset: 50,
    limit: 50,
  });
  expect(first.samples).toHaveLength(50);
  expect(second.samples).toHaveLength(22);
  expect(first.total).toBe(72);
  expect(markerSamples(first.samples, "argo")).toHaveLength(3);
  const profile = await client.getObservationSamples("demo-argo", {
    profile_id: "demo-argo-profile-1",
    limit: 50,
  });
  expect(profile.samples).toHaveLength(24);
  expect(profile.samples.every((s) => s.depth_m === null)).toBe(true);
  const series = profileSeries(profile.samples, "TEMP", "pressure_dbar");
  expect(series.y[0]).toBe(0);
  expect(series.y.at(-1)).toBe(230);
  expect(series.x[6]).toBeNull();
  expect(series.missing).toBe(1);
  expect(
    urls.every((u) => !u.includes("platform=") && !u.includes("parameter=")),
  ).toBe(true);
});
test("tracks require contiguous source ordering and metadata; no bridging page gaps", async () => {
  const client = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: createDemoTransport("normal", 0),
  });
  const { samples } = await client.getObservationSamples("demo-glider", {
    limit: 50,
  });
  expect(trackSegments(samples)).toHaveLength(49);
  expect(markerSamples(samples, "glider")).toHaveLength(50);
  expect(trackSegments([samples[0], samples[2]])).toHaveLength(0);
  expect(
    trackSegments([samples[0], { ...samples[1], deployment_id: "other" }]),
  ).toHaveLength(0);
  expect(
    trackSegments([samples[0], { ...samples[1], sequence: undefined }]),
  ).toHaveLength(0);
  expect(
    profileVariableAllowed({
      name: "fluorescence",
      label: "Fluorescence",
      units: "RFU",
    }),
  ).toBe(false);
  expect(
    profileVariableAllowed({
      name: "CHLA",
      label: "Chlorophyll",
      units: "mg/m³",
      normalized: true,
      interpretation: "chlorophyll",
    }),
  ).toBe(true);
});
test("mismatched profile responses are rejected instead of scientifically filtered in browser", async () => {
  const transport = createDemoTransport("normal", 0);
  const client = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: (url, init) =>
      transport(url.replace(/profile_id=[^&]+&?/, ""), init),
  });
  await expect(
    client.getObservationSamples("demo-argo", {
      profile_id: "demo-argo-profile-1",
    }),
  ).rejects.toMatchObject({ code: "invalid_response" });
});
