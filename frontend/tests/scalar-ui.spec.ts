import { test, expect } from "@playwright/test";
test("scalar field renders with API units, stable limits, manual grading and retained timestamps", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/explorer");
  await page.locator("#dataset").selectOption("demo-bioroms");
  const bar = page.getByRole("complementary", { name: "Scientific colorbar" });
  await expect(bar).toBeVisible();
  await expect(bar).toContainText("°C");
  await expect(bar).toContainText("SYNTHETIC DEMO");
  const min = await bar.getAttribute("data-min");
  await page.getByRole("button", { name: "Next frame", exact: true }).click();
  await expect(bar).toHaveAttribute("data-timestamp", "2019-01-29T00:00:00Z");
  await expect(bar).toHaveAttribute("data-timestamp", "2019-02-28T00:00:00Z");
  await expect(bar).toHaveAttribute("data-min", min!);
  await page.locator("#scalar-range").selectOption("manual");
  await page.getByLabel("Manual minimum").fill("20");
  await page.getByLabel("Manual maximum").fill("32");
  await expect(bar).toHaveAttribute("data-min", "20");
  await expect(bar).toHaveAttribute("data-max", "32");
  await page.locator("#scalar-palette").selectOption("anomaly");
  await page.locator("#scalar-interpolation").selectOption("nearest");
  await expect(bar).toContainText("nearest display");
  await page.getByLabel("Show scalar layer").uncheck();
  await expect(bar).toHaveCount(0);
  await page.getByLabel("Show scalar layer").check();
  await expect(bar).toBeVisible();
  await page.getByRole("button", { name: "Reset color scale" }).click();
  await expect(bar).not.toHaveAttribute("data-min", "20");
  await page.screenshot({ path: "tests/part4-scalar-desktop.png" });
  await page.locator("#variable").selectOption("SSS");
  await expect(bar).toContainText("Sea surface salinity (1)");
  await page.getByRole("link", { name: "Comparison", exact: true }).click();
  await expect(bar).toBeVisible();
  expect(errors).toEqual([]);
});
test("oversized scientific requests recover to labeled preview and mobile colorbar fits", async ({
  page,
}) => {
  await page.goto("/explorer");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Display settings" })
    .getByLabel("DEMO SCENARIO")
    .selectOption("scientific-too-large");
  await page.keyboard.press("Escape");
  await page.locator("#dataset").selectOption("demo-bioroms");
  await page.locator("#scalar-quality").selectOption("scientific");
  await expect(page.locator(".scalar-panel")).toContainText(
    "Using bounded preview",
  );
  await expect(page.locator(".scientific-colorbar")).toContainText("Preview");
  await page.setViewportSize({ width: 1800, height: 1000 });
  const gradient = await page.locator(".colorbar-gradient").boundingBox();
  expect(gradient!.height).toBeGreaterThan(gradient!.width);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page
    .getByRole("button", { name: "Reset to project region", exact: true })
    .click();
  const box = await page.locator(".scientific-colorbar").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "tests/part4-scalar-mobile.png" });
});
