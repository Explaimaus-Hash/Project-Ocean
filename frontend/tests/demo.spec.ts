import { test, expect, type Page } from "@playwright/test";
async function scenario(page: Page, value: string) {
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Display settings" })
    .getByLabel("DEMO SCENARIO")
    .selectOption(value);
  await page.keyboard.press("Escape");
}
test("demo controls follow metadata and persist across routes", async ({
  page,
}) => {
  await page.goto("/explorer");
  await expect(page.locator("#dataset")).toBeEnabled();
  await page.locator("#dataset").selectOption("demo-bioroms");
  await expect(page.locator("#variable option")).toHaveCount(2);
  await expect(page.locator("#depth")).toBeDisabled();
  await expect(page.locator("#render-mode")).toBeDisabled();
  await expect(page.locator(".bottom-timeline time")).toHaveText(
    "2019-01-29T00:00:00Z",
  );
  await expect(
    page.getByRole("button", { name: "Next frame", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Next frame", exact: true }).click();
  await expect(page.locator(".bottom-timeline time")).toHaveText(
    "2019-02-28T00:00:00Z",
  );
  await page.locator("#variable").selectOption("SSS");
  await page.getByRole("link", { name: "Analysis", exact: true }).click();
  await expect(page.locator("#variable")).toHaveValue("SSS");
  await page.getByRole("button", { name: "Open contextual panel" }).click();
  await page.locator("#dataset").selectOption("demo-salinity");
  await expect(page.locator("#variable option")).toHaveCount(1);
  await expect(page.locator("#variable")).toHaveValue("SSS");
  await page.locator("#observation").selectOption("demo-argo");
  await expect(page.locator(".selection-controls")).toContainText(
    "50 demo samples loaded",
  );
  await page.screenshot({ path: "tests/part3-demo-desktop.png" });
});
test("unprepared products, unavailable observations and readiness 503 preserve workspace", async ({
  page,
}) => {
  await page.goto("/explorer");
  await expect(page.locator(".top-status")).toContainText(
    "Readiness: not ready",
  );
  await page.locator("#dataset").selectOption("demo-unprepared");
  await expect(page.locator(".selection-controls")).toContainText(
    "Dataset not prepared",
  );
  await expect(page.locator("#variable")).toBeDisabled();
  await scenario(page, "observations-unavailable");
  await expect(page.locator(".selection-controls")).toContainText(
    "Provider unavailable",
  );
  await page.locator("#dataset").selectOption("demo-bioroms");
  await expect(page.locator("#variable")).toBeEnabled();
  await scenario(page, "product-failure");
  await page.locator("#dataset").selectOption("demo-bioroms");
  await expect(page.locator(".selection-controls")).toContainText(
    "Dataset not prepared",
  );
  await page.locator("#dataset").selectOption("demo-salinity");
  await expect(page.locator("#variable")).toBeEnabled();
  await scenario(page, "backend-offline");
  await expect(page.locator(".backend-status")).toContainText(
    "Demo process offline",
  );
  await expect(
    page.getByRole("button", { name: "Zoom in", exact: true }),
  ).toBeEnabled();
});
test("error scenarios show safe states without applying frames", async ({
  page,
}) => {
  await page.goto("/explorer");
  for (const [value, message] of [
    ["busy", "Service busy"],
    ["too-large", "Request too large"],
    ["no-overlap", "No overlap"],
    ["unsupported", "Selection unsupported"],
  ]) {
    await scenario(page, value);
    await page.locator("#dataset").selectOption("demo-bioroms");
    await expect(page.locator(".selection-controls")).toContainText(message);
    await expect(
      page.getByRole("button", { name: "Next frame", exact: true }),
    ).toBeDisabled();
  }
  await scenario(page, "empty");
  await expect(page.locator(".selection-controls")).toContainText(
    "Empty selection",
  );
});
