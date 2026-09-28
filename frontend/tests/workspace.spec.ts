import { test, expect } from "@playwright/test";

test("all routes navigate without replacing the document, shell, globe or selection", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/explorer");
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await page.locator(".context-panel #region").selectOption("global");
  await page.evaluate(() => {
    document.documentElement.dataset.documentIdentity = "original";
    document.querySelector("canvas")!.dataset.identity = "original-globe";
  });
  for (const name of [
    "Analysis",
    "Profiles",
    "Comparison",
    "Data Sources",
    "Explorer",
  ]) {
    await page.getByRole("link", { name, exact: true }).click();
    await expect(page.locator(".context-panel h1")).toHaveText(name);
    await expect(page.locator(".context-panel #region")).toHaveValue("global");
    await expect(page.locator("html")).toHaveAttribute(
      "data-document-identity",
      "original",
    );
    await expect(page.locator("canvas")).toHaveAttribute(
      "data-identity",
      "original-globe",
    );
    await expect(page.getByRole("link", { name, exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
  }
  await expect(page.locator("canvas")).toHaveCount(1);
  await expect(page.locator(".cesium-viewer-bottom")).toBeVisible();
  expect(errors).toEqual([]);
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-camera-motion",
    "idle",
  );
  await page.screenshot({ path: "tests/workspace-desktop.png" });
});

test("direct routes and Cesium assets are served", async ({ request }) => {
  for (const route of [
    "explorer",
    "analysis",
    "profiles",
    "comparison",
    "data-sources",
  ])
    expect((await request.get(`/${route}`)).status()).toBe(200);
  expect(
    (
      await request.get(
        "/cesium/Assets/Textures/NaturalEarthII/tilemapresource.xml",
      )
    ).status(),
  ).toBe(200);
});

test("small screen drawer is keyboard accessible, selection persists and timeline fits", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/explorer");
  const opener = page.getByRole("button", { name: "Open contextual panel" });
  await opener.focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await drawer.getByLabel("REGION", { exact: true }).selectOption("global");
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(opener).toBeFocused();
  await page.getByRole("link", { name: "Analysis", exact: true }).click();
  await opener.click();
  await expect(drawer.getByLabel("REGION", { exact: true })).toHaveValue(
    "global",
  );
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("contentinfo", { name: "Time controls" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const scrubber = await page.getByRole("slider", { name: "Time frame", exact: true }).boundingBox();
  expect(scrubber!.y + scrubber!.height + 8).toBeLessThanOrEqual(844);
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await page.screenshot({ path: "tests/workspace-mobile.png" });
});

test("graphics context loss has a working retry", async ({ page }) => {
  await page.goto("/explorer");
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await page
    .locator("canvas")
    .evaluate((canvas) =>
      canvas.dispatchEvent(new Event("webglcontextlost", { cancelable: true })),
    );
  await expect(page.locator(".globe-scene").getByRole("alert")).toContainText(
    "Globe unavailable",
  );
  await page.getByRole("button", { name: "Retry globe" }).click();
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await expect(page.locator("canvas")).toHaveCount(1);
});

test("missing basemap preserves a usable globe with an explicit notice", async ({
  page,
}) => {
  await page.route("**/cesium/Assets/Textures/NaturalEarthII/**", (route) =>
    route.abort(),
  );
  await page.goto("/explorer");
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await expect(page.locator(".scene-caption")).toContainText(
    "Imagery unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Zoom in", exact: true }),
  ).toBeEnabled();
});
