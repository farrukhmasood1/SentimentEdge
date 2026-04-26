import { expect, test } from "@playwright/test";

test("cached run, route navigation, and review actions work", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Active saved run")).toBeVisible();
  await expect(page.locator(".active-run-line strong")).toHaveText("run_20260425_174443");
  await expect(page.getByText("Upload completed run files")).toBeVisible();
  await expect(page.getByText("Paste your Anthropic key here")).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles([
    "../outputs/runs/run_20260425_174443/run_metadata.json",
    "../outputs/runs/run_20260425_174443/ticker_summary.csv",
    "../outputs/runs/run_20260425_174443/sentiment_results.csv",
    "../outputs/runs/run_20260425_174443/rumour_alerts.csv",
  ]);
  await expect(page.getByText("Loaded run_20260425_174443 from uploaded run files.")).toBeVisible();

  await page.getByRole("button", { name: "SPY · TSLA" }).click();
  await expect(page.getByText("Confidence delta")).toBeVisible();
  await expect(page.getByText("High sarcasm rate")).toBeVisible();

  await page.getByRole("button", { name: "Review Queue", exact: true }).click();
  await expect(page.getByText("High-confidence rumors enter the governance track.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approved 7" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Pending 0" })).toBeVisible();
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByRole("button", { name: "Approved 6" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Rejected 1" })).toBeVisible();
});
