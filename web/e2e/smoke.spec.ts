import { expect, test } from "@playwright/test";

test("cached run, route navigation, and review actions work", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Active saved run")).toBeVisible();
  await expect(page.locator(".active-run-line strong")).toHaveText("run_20260412_110302");
  await expect(page.getByText("Upload completed run files")).toBeVisible();
  await expect(page.getByText("Paste your Anthropic key here")).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles([
    "../outputs/sample_runs/run_20260412_110302/run_metadata.json",
    "../outputs/sample_runs/run_20260412_110302/ticker_summary.csv",
    "../outputs/sample_runs/run_20260412_110302/sentiment_results.csv",
    "../outputs/sample_runs/run_20260412_110302/rumour_alerts.csv",
  ]);
  await expect(page.getByText("Loaded run_20260412_110302 from uploaded run files.")).toBeVisible();

  await page.getByRole("button", { name: "SPY · TSLA" }).click();
  await expect(page.getByText("Confidence delta")).toBeVisible();
  await expect(page.getByText("High sarcasm rate")).toBeVisible();

  await page.getByRole("button", { name: "Review Queue", exact: true }).click();
  await expect(page.getByText("Every rumor with rumour_confidence ≥ 0.70")).toBeVisible();
  await page.getByRole("button", { name: /Approve for publication/ }).click();
  await expect(page.getByRole("button", { name: "Approved 1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Pending 2" })).toBeVisible();
});
