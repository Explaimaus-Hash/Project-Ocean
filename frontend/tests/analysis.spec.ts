import { test, expect } from "@playwright/test";
import {
  plottedCSV,
  analysisAvailability,
} from "../src/features/analysis/plotModel";
import { DataClient } from "../src/lib/dataClient";
import { createDemoTransport } from "../src/lib/demo/transport";

test("time series preserves returned cell, units and missing samples", async () => {
  const client = new DataClient({
    baseUrl: "https://demo.invalid",
    transport: createDemoTransport("timeseries-gaps", 0),
  });
  const data = await client.getTimeseries("demo-surface", {
    variable: "SST",
    longitude: 65,
    latitude: 0,
  });
  expect(data.mode).toBe("synthetic");
  expect(data.units).toBe("°C");
  expect(data.latitude).not.toBe(0);
  expect(data.distance_km).toBeGreaterThan(0);
  expect(data.values[1]).toBeNull();
  expect(data.values.length).toBe(data.timestamps.length);
  await expect(
    client.getTimeseries("demo-surface", {
      variable: "SST",
      longitude: 0,
      latitude: 0,
    }),
  ).rejects.toMatchObject({ code: "no_overlap" });
});

test("exports are bounded, preserve gaps and escape spreadsheet formulas", () => {
  expect(
    plottedCSV(["quantity", "missing", "source"], [[-2, null, "=SUM(A1)"]]),
  ).toContain('"-2","","\'=SUM(A1)"');
  expect(() =>
    plottedCSV(
      ["x"],
      Array.from({ length: 10001 }, () => [1]),
    ),
  ).toThrow();
  expect(analysisAvailability(true).profile.enabled).toBe(false);
  expect(analysisAvailability(true).timeDepth.enabled).toBe(false);
  expect(analysisAvailability(true).transect.enabled).toBe(false);
});

test("analysis split, truthful chart, exports and persistent globe", async ({
  page,
}) => {
  await page.goto("/explorer");
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await page.locator("#dataset").selectOption("demo-bioroms");
  await page
    .locator(".cesium-widget canvas")
    .evaluate((el) => el.setAttribute("data-persistent", "yes"));
  await page.getByRole("link", { name: "Analysis", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Download PNG", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("tab", { name: "Vertical Profile", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".analysis-location")).toContainText(
    "Actual grid cell",
  );
  await expect(page.locator(".scientific-plot-shell")).toContainText(
    "SYNTHETIC DEMO",
  );
  const divider = page.getByRole("separator", {
    name: "Resize geographic context",
  });
  await expect(divider).toHaveAttribute("aria-valuenow", "45");
  await divider.focus();
  await page.keyboard.press("ArrowRight");
  await expect(divider).toHaveAttribute("aria-valuenow", "50");
  await page.keyboard.press("Home");
  const csv = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export plotted CSV" }).click();
  expect((await csv).suggestedFilename()).toBe(
    "project-ocean-plotted-data.csv",
  );
  const png = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PNG", exact: true }).click();
  expect((await png).suggestedFilename()).toContain(".png");
  await page.getByRole("button", { name: "Reset zoom", exact: true }).click();
  const heatmapWorks = await page.evaluate(async () => {
    const host = document.createElement("div");
    host.style.cssText = "position:absolute;width:300px;height:300px";
    document.body.append(host);
    await window.Plotly!.newPlot(
      host,
      [
        {
          type: "heatmap",
          x: [0, 1],
          y: [0, 10],
          z: [
            [1, null],
            [2, 3],
          ],
          connectgaps: false,
        },
      ],
      { yaxis: { autorange: "reversed" } },
      {},
    );
    const rendered = !!host.querySelector(".heatmaplayer image");
    window.Plotly!.purge(host);
    host.remove();
    return rendered;
  });
  expect(heatmapWorks).toBe(true);
  await page.screenshot({ path: "tests/part6-analysis-desktop.png" });
  await page.getByLabel("Requested longitude").fill("0");
  await page
    .getByRole("button", { name: "Load time series", exact: true })
    .click();
  await expect(page.locator(".analysis-workspace")).toContainText("No overlap");
  await expect(page.locator(".scientific-plot-shell")).toHaveCount(0);
  await page.getByRole("link", { name: "Explorer", exact: true }).click();
  await expect(page.locator(".cesium-widget canvas")).toHaveAttribute(
    "data-persistent",
    "yes",
  );
});

test("analysis mobile remains bounded and missing values remain plot gaps", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/analysis");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Display settings" })
    .getByLabel("DEMO SCENARIO")
    .selectOption("timeseries-gaps");
  await page.keyboard.press("Escape");
  await page.getByLabel("Analysis dataset").selectOption("demo-bioroms");
  await expect(
    page.getByRole("button", { name: "Download PNG", exact: true }),
  ).toBeEnabled();
  const trace = await page.locator(".scientific-plot").evaluate((el) => {
    const p = el as HTMLElement & {
      data: { y: (number | null)[]; connectgaps: boolean }[];
    };
    return { y: p.data[0].y, connectgaps: p.data[0].connectgaps };
  });
  expect(trace.y[1]).toBeNull();
  expect(trace.connectgaps).toBe(false);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.locator(".scientific-plot").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "tests/part6-analysis-mobile.png" });
});
