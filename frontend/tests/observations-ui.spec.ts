import { test, expect } from "@playwright/test";
test("Argo search opens Plotly pressure profiles, changes parameter and uses paging", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/profiles");
  await page.locator("#observation-collection").selectOption("demo-argo");
  await expect(page.locator(".observation-results button")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Inspect demo-argo-0", exact: true })
    .click();
  const inspector = page.getByRole("complementary", {
    name: "Observation profile inspector",
  });
  await expect(inspector).toContainText("DEMO-FLOAT-01");
  await expect(inspector).toContainText(
    "Synthetic / not scientifically evaluated",
  );
  await expect(inspector.locator(".js-plotly-plot")).toBeVisible();
  await expect(inspector.locator(".ytitle")).toHaveText("Pressure (dbar)");
  await expect(inspector.locator(".xtitle")).toHaveText("Temperature (°C)");
  await expect(inspector).toContainText(
    "24 samples on this profile page · 1 missing",
  );
  const data = await inspector.locator(".js-plotly-plot").evaluate((el) => {
    const plot = el as unknown as {
      data: { x: (number | null)[]; connectgaps: boolean }[];
      _fullLayout: { yaxis: { range: number[] } };
    };
    return {
      x: plot.data[0].x,
      gaps: plot.data[0].connectgaps,
      range: plot._fullLayout.yaxis.range,
    };
  });
  expect(data.x[6]).toBeNull();
  expect(data.gaps).toBe(false);
  expect(data.range[0]).toBeGreaterThan(data.range[1]);
  await page.locator("#profile-parameter").selectOption("PSAL");
  await expect(inspector.locator(".xtitle")).toHaveText(
    "Practical salinity (1)",
  );
  await inspector.screenshot({ path: "tests/part5-argo-profile.png" });
  await page.getByRole("button", { name: "Close observation" }).click();
  await page.getByRole("button", { name: "Next samples", exact: true }).click();
  await expect(page.locator(".observation-search")).toContainText(
    "51–72 of 72",
  );
  await page.locator("#profile-search").fill("demo-argo-profile-2");
  await page
    .getByRole("button", { name: "Search profile", exact: true })
    .click();
  await expect(page.locator(".observation-search")).toContainText("1–24 of 24");
  await page.locator("#profile-search").fill("missing");
  await page
    .getByRole("button", { name: "Search profile", exact: true })
    .click();
  await expect(page.locator(".observation-search")).toContainText(
    "No observations match",
  );
  expect(errors).toEqual([]);
});
test("Glider track, depth and supported BGC profile remain usable on mobile", async ({
  page,
}) => {
  await page.goto("/profiles");
  await page.locator("#observation-collection").selectOption("demo-glider");
  await expect(page.locator(".observation-map-key")).toContainText(
    "Glider samples",
  );
  await expect(page.locator(".observation-results button")).toHaveCount(50);
  await page
    .getByRole("button", { name: "Inspect demo-glider-0", exact: true })
    .click();
  const inspector = page.getByRole("complementary", {
    name: "Observation profile inspector",
  });
  await expect(inspector.locator(".ytitle")).toHaveText("Depth (m)");
  await page.locator("#profile-parameter").selectOption("CHLA");
  await expect(inspector.locator(".xtitle")).toHaveText("Chlorophyll (mg/m³)");
  await expect(inspector).toContainText("1 missing");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page
    .getByRole("button", { name: "Reset to project region", exact: true })
    .click();
  await page.screenshot({ path: "tests/part5-glider-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(inspector).toBeVisible();
  const bounds = await inspector.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(59);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  await inspector.locator(".profile-plot").scrollIntoViewIfNeeded();
  const plotBox=await inspector.locator('[role="img"]').boundingBox();
  const pagingBox=await inspector.locator('.observation-paging').boundingBox();
  expect(pagingBox!.y).toBeGreaterThanOrEqual(plotBox!.y+plotBox!.height);
  await page.screenshot({ path: "tests/part5-profile-mobile.png" });
  await page.keyboard.press("Escape");
  await expect(inspector).toHaveCount(0);
});
test("real Cesium marker hover and click select an observation without a reload", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/explorer");
  await page.locator("#observation").selectOption("demo-argo");
  await expect(page.locator(".observation-map-key")).toBeVisible();
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  const canvas = page.locator(".cesium-widget canvas");
  const box = (await canvas.boundingBox())!;
  let hit = false;
  for (let y = -12; y <= 76 && !hit; y += 8)
    for (let x = -100; x <= 8 && !hit; x += 8) {
      await page.mouse.move(
        box.x + box.width / 2 + x,
        box.y + box.height / 2 + y,
      );
      await page.waitForTimeout(45);
      hit = await page.locator(".observation-hover").isVisible();
    }
  expect(hit).toBe(true);
  await expect(page.locator(".observation-hover")).toContainText(
    "Platform: DEMO-FLOAT-01",
  );
  await page.mouse.down();
  await page.mouse.up();
  await expect(
    page.getByRole("complementary", { name: "Observation profile inspector" }),
  ).toBeVisible();
  await expect(page.locator(".js-plotly-plot")).toBeVisible();
  await expect(page.locator(".cesium-widget canvas")).toHaveCount(1);
});
