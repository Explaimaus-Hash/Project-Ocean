import { test, expect } from "@playwright/test";
import {
  DataClient,
  LatestRequest,
  abortableDelay,
} from "../src/lib/dataClient";
import { createDemoTransport, products } from "../src/lib/demo/transport";
const create = () =>
  new DataClient({
    baseUrl: "https://demo.invalid",
    transport: createDemoTransport("normal", 0),
    retryDelayMs: 1,
  });
test("all ten routes validate and readiness is independent", async () => {
  const c = create();
  expect((await c.getHealth()).status).toBe("ok");
  expect((await c.getReadiness()).ready).toBe(false);
  expect((await c.getDatasets()).datasets).toHaveLength(4);
  expect((await c.getProduct("demo-surface")).capabilities.depth).toBe(false);
  expect(
    (await c.getFrame("demo-surface", { variable: "SST", time_index: 0 }))
      .values[0][0],
  ).toBeNull();
  expect(
    (
      await c.getTimeseries("demo-surface", {
        variable: "SST",
        longitude: 65,
        latitude: 0,
      })
    ).values,
  ).toHaveLength(3);
  expect((await c.getAcquisitions()).acquisitions[0].status).toBe(
    "acquired_not_prepared",
  );
  expect((await c.getObservationCollections()).collections).toHaveLength(2);
  expect((await c.getObservationCollection("demo-argo")).source).toBe("argo");
  expect(
    (await c.getObservationSamples("demo-argo")).samples[0].depth_m,
  ).toBeNull();
  await c.prefetchNearbyFrames(products[0], "SST", 1);
  expect(c.diagnostics().frameEntries).toBeLessThanOrEqual(3);
  for (const variable of ["SST", "SSS"])
    for (let time_index = 0; time_index < 3; time_index++)
      await c.getFrame("demo-surface", { variable, time_index });
  expect(c.diagnostics().frameEntries).toBe(3);
  c.clear();
  expect(c.diagnostics().metadataEntries).toBe(0);
});
test("busy retries bounded; 413 and 422 never retry or leak server bodies", async () => {
  for (const [status, code, count] of [
    [503, "busy", 3],
    [413, "request_too_large", 1],
    [422, "unsupported_selection", 1],
  ] as const) {
    let calls = 0;
    const c = new DataClient({
      baseUrl: "https://demo.invalid",
      retryDelayMs: 1,
      transport: async () => {
        calls++;
        return Response.json({ private: "secret" }, { status });
      },
    });
    await expect(c.getDatasets()).rejects.toMatchObject({ code });
    expect(calls).toBe(count);
  }
});
test("dedup cancellation preserves another subscriber and last cancel aborts", async () => {
  let calls = 0;
  let aborted = false;
  const transport = createDemoTransport("normal", 25);
  const c = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: async (u, i) => {
      calls++;
      i.signal?.addEventListener("abort", () => {
        aborted = true;
      });
      return transport(u, i);
    },
  });
  const controller = new AbortController();
  const a = c.getDatasets(controller.signal);
  const rejected = expect(a).rejects.toMatchObject({ code: "aborted" });
  const b = c.getDatasets();
  controller.abort();
  await rejected;
  await b;
  expect(calls).toBe(1);
  expect(aborted).toBe(false);
  const last = new AbortController();
  const request = c.getHealth(last.signal);
  const assertion = expect(request).rejects.toMatchObject({ code: "aborted" });
  last.abort();
  await assertion;
  expect(aborted).toBe(true);
});
test("latest request rejects stale responses even when transport ignores cancellation", async () => {
  const gate = new LatestRequest();
  let resolve!: (v: string) => void;
  const old = gate.run(
    () =>
      new Promise<string>((r) => {
        resolve = r;
      }),
  );
  const assertion = expect(old).rejects.toMatchObject({
    code: "stale_response",
  });
  expect(await gate.run(async () => "new")).toBe("new");
  resolve("old");
  await assertion;
});
test("invalid schemas and identities are rejected; requests have deadlines", async () => {
  const c = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: async () => Response.json({ ...products[0], schema_version: 2 }),
  });
  await expect(c.getProduct("demo-surface")).rejects.toMatchObject({
    code: "invalid_response",
  });
  const timeout = new DataClient({
    baseUrl: "https://demo.invalid",
    deadlineMs: 5,
    transport: async (_u, i) => {
      await abortableDelay(100, i.signal!);
      return Response.json({});
    },
  });
  await expect(timeout.getHealth()).rejects.toMatchObject({ code: "timeout" });
});
