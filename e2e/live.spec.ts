import {
  test,
  expect,
} from "../frontend/node_modules/@playwright/test/index.mjs";

test("real backend golden path through the governed UI", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  await expect(page.locator(".environment-label")).toContainText(
    "Simulator backend",
  );
  await page.getByRole("button", { name: "Director", exact: true }).click();
  await page
    .getByRole("button", { name: "Start scenario", exact: true })
    .click();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByLabel("Acting persona").selectOption("u_priya");
  if (
    await page
      .getByRole("switch", { name: "Read-only mode", exact: true })
      .isChecked()
  )
    await page
      .getByRole("switch", { name: "Read-only mode", exact: true })
      .uncheck();
  await page
    .getByLabel("Ask Baton", { exact: true })
    .fill("Is ATM auth keeping up?");
  await page.getByRole("button", { name: "Send message" }).click();
  const stats = page
    .locator(".card-command")
    .filter({ hasText: "STATS SERVER ATM-AUTH" })
    .last();
  await expect(stats).toBeVisible({ timeout: 65000 });
  await stats.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByText("Parameters validated by backend")).toBeVisible();
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  await expect(stats).toContainText("done", { timeout: 15000 });
  await page.getByRole("button", { name: "Director", exact: true }).click();
  await page.getByRole("button", { name: "CPU 3 halt", exact: true }).click();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  const check = page
    .locator(".card-command")
    .filter({ hasText: "TMFCOM; STATUS AUDITTRAIL" })
    .last();
  await expect(check).toBeVisible({ timeout: 20000 });
  await check.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  const decision = page.locator(".card-decision").last();
  await expect(decision).toBeVisible({ timeout: 20000 });
  await decision
    .getByRole("button", { name: "Approve selected", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm selected actions" }).click();
  await expect(page.getByText(/1 of 2/).first()).toBeVisible({
    timeout: 15000,
  });
  await page.screenshot({
    path: "test-results/live-two-person.png",
    fullPage: true,
  });
  await page.getByLabel("Acting persona").selectOption("u_sam");
  await decision
    .getByRole("button", { name: "Approve selected", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm selected actions" }).click();
  await expect(page.locator(".card-verification")).toContainText(
    /Recovered|recovered/,
    { timeout: 90000 },
  );
  const incidents = await (await page.request.get("/api/incidents")).json();
  const incident = incidents.incidents.at(-1);
  expect(incident.status).toBe("resolved");
  await page.getByRole("link", { name: /^Knowledge/ }).click();
  await page.getByLabel("Acting persona").selectOption("u_dave");
  const result = await (
    await page.request.get("/api/claims?status=pending_review")
  ).json();
  const drafts = result.claims.filter(
    (c: { provenance: { source_type: string; source_id: string } }) =>
      c.provenance.source_type === "incident" &&
      c.provenance.source_id === incident.id,
  );
  expect(drafts.length).toBeGreaterThanOrEqual(2);
  const first = page
    .locator(".claim-card")
    .filter({ hasText: drafts[0].statement });
  await first.getByRole("button", { name: "Confirm", exact: true }).click();
  await page.getByRole("button", { name: "Confirm & index claim" }).click();
  const second = page
    .locator(".claim-card")
    .filter({ hasText: drafts[1].statement });
  await second
    .getByRole("button", { name: "Edit & confirm", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Scope / condition", exact: true })
    .fill("TORBANK · Black Friday peak · one CPU down");
  await page.getByLabel("Calendar scope", { exact: true }).fill("black_friday");
  await page.getByRole("button", { name: "Confirm & index claim" }).click();
  await page.getByRole("link", { name: "Trust Ledger", exact: true }).click();
  await page.getByRole("button", { name: "Review promotion" }).click();
  await page
    .getByLabel("Reason", { exact: true })
    .fill("20 clean read-only approvals reviewed after INC-0001.");
  await page.getByRole("button", { name: "Grant L2", exact: true }).click();
  await page.getByRole("link", { name: "Audit", exact: true }).click();
  await page.getByRole("button", { name: "Verify chain", exact: true }).click();
  await expect(page.getByText(/Chain verified ·/)).toBeVisible();
  await page.screenshot({
    path: "test-results/live-audit.png",
    fullPage: true,
  });
  const verification = await (
    await page.request.get("/api/audit/verify")
  ).json();
  expect(verification.valid).toBe(true);
  expect(errors).toEqual([]);
});
