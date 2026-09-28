import { test, expect } from "@playwright/test";

test("Indian Ocean launch, cursor coordinates and camera commands", async ({
  page,
}) => {
  await page.goto("/explorer");
  const scene = page.locator(".globe-scene");
  await expect(scene).toHaveAttribute("data-scene-status", "ready");
  await expect(scene).toHaveAttribute("data-camera-motion", "idle");
  const box = await page.locator("canvas").boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await expect(page.locator(".geographic-readout")).toContainText(
    /7[45]\.\d{3}°E/,
  );
  const altitude = page.locator(".geographic-readout span").nth(1);
  const before = await altitude.innerText();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect(altitude).not.toHaveText(before);
  await page.getByLabel("More camera controls").click();
  for (const name of [
    "Rotate left",
    "Rotate right",
    "Pan left",
    "Pan right",
    "Pan up",
    "Pan down",
    "Tilt up",
    "Tilt down",
  ])
    await page.getByRole("button", { name, exact: true }).click();
  await page.getByRole("button", { name: "Reset north", exact: true }).click();
  await page
    .getByRole("button", { name: "Reset to project region", exact: true })
    .click();
  await expect(scene).toHaveAttribute("data-camera-motion", "idle");
  await page.getByLabel("More camera controls").click();
  await page.screenshot({ path: "tests/part2-explorer-desktop.png" });
});

test("flights can be interrupted and reduced motion avoids flights", async ({
  page,
}) => {
  await page.goto("/explorer");
  const scene = page.locator(".globe-scene");
  await expect(scene).toHaveAttribute("data-scene-status", "ready");
  await page.getByRole("button", { name: "Home view", exact: true }).click();
  await expect(scene).toHaveAttribute("data-camera-motion", "flying");
  await page.getByRole("button", { name: "Stop flight", exact: true }).click();
  await expect(scene).toHaveAttribute("data-camera-motion", "idle");
  await page.getByRole("button", { name: "Home view", exact: true }).click();
  await page.locator("canvas").press("Escape");
  await expect(scene).toHaveAttribute("data-camera-motion", "idle");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page
    .getByRole("button", { name: "Reset to project region", exact: true })
    .click();
  await expect(scene).toHaveAttribute("data-camera-motion", "idle");
});

test("display controls persist; unavailable science has reasons and no dates", async ({
  page,
}) => {
  await page.goto("/explorer");
  await expect(page.locator(".globe-scene")).toHaveAttribute(
    "data-scene-status",
    "ready",
  );
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const settings = page.getByRole("dialog", { name: "Display settings" });
  await settings.getByLabel("Rendering quality").selectOption("high");
  await settings.getByLabel("Sun lighting").check();
  await page.keyboard.press("Escape");
  await page.getByRole("link", { name: "Analysis", exact: true }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(settings.getByLabel("Rendering quality")).toHaveValue("high");
  await expect(settings.getByLabel("Sun lighting")).toBeChecked();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Help", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "Explorer help" }),
  ).toContainText("Interrupt a flight");
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Play timeline", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".bottom-timeline time")).toHaveCount(0);
  await expect(page.getByLabel("Playback speed").locator("option")).toHaveCount(
    5,
  );
  await page.getByLabel("Playback speed").selectOption("0.25");
  await page.getByRole("button", { name: "Open contextual panel" }).click();
  await page
    .getByRole("button", { name: "Depth unavailable", exact: true })
    .focus();
  await expect(
    page.getByRole("tooltip").filter({ hasText: "verified vertical metadata" }),
  ).toBeVisible();
  await expect(page.locator(".backend-status")).toContainText(
    "Demo process reachable",
  );
  await expect(page.locator(".right-inspector")).toContainText(
    "No point selected",
  );
});
