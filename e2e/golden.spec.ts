import {
  test,
  expect,
} from "../frontend/node_modules/@playwright/test/index.mjs";

test("mock golden path: guarded diagnosis, recovery, learning and audit", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("Ready for your next check.")).toBeVisible();
  await expect(page.getByText("All streams connected")).toBeVisible();
  await page.screenshot({
    path: "test-results/console-healthy.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Is ATM auth keeping up?" }).click();
  const firstCheck = page.getByRole("article", {
    name: "ATM authorization performance",
    exact: true,
  });
  await firstCheck
    .getByRole("button", { name: "Approve", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  await page.getByRole("button", { name: "Director", exact: true }).click();
  await page.getByRole("button", { name: "CPU 3 halt", exact: true }).click();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  const auditCard = page.getByRole("article", {
    name: "TMF audit trail status",
    exact: true,
  });
  await expect(auditCard).toBeVisible();
  await auditCard.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  const decision = page.getByRole("article", { name: "Options", exact: true });
  await expect(decision).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Recover service capacity",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".plan-step-link").first()).toHaveAttribute(
    "title",
    "SUSPEND $STMT1",
  );
  await expect(page.locator(".plan-step-link").nth(1)).toHaveAttribute(
    "title",
    /NUMSTATIC 28/,
  );
  await page.screenshot({
    path: "test-results/console-incident.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Review plan & approvals", exact: true })
    .click();
  await expect(decision).toBeVisible();
  await decision
    .getByRole("button", { name: "Approve selected", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("SUSPEND $STMT1");
  await expect(page.getByRole("dialog")).toContainText("NUMSTATIC 28");
  await page
    .getByRole("button", { name: "Confirm selected actions", exact: true })
    .click();
  await expect(decision).toContainText("1 of 2: needs Senior or Expert");
  await page.screenshot({
    path: "test-results/incident-two-person.png",
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Steps", exact: true }).click();
  await expect(page.locator(".trace-step").first()).toBeVisible();
  await page.locator(".trace-step").first().click();
  await expect(page.getByRole("dialog")).toContainText("Prompt hash");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("tab", { name: "Playbook", exact: true }).click();
  await expect(page.locator(".card-expert")).toContainText("Verified by");
  await page.getByRole("tab", { name: "Evidence", exact: true }).click();
  await expect(
    page.locator('[role="tabpanel"][aria-label="Evidence"]'),
  ).toContainText("TMFCOM");
  await page.getByRole("tab", { name: "Diagnosis", exact: true }).click();
  await page.getByLabel("Acting persona").selectOption("u_sam");
  await decision
    .getByRole("button", { name: "Approve selected", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm selected actions", exact: true })
    .click();
  await expect(
    page.getByRole("article", {
      name: "Recovered: ATM p95 in band for 60 s",
      exact: true,
    }),
  ).toBeVisible({ timeout: 25000 });
  await page.getByRole("button", { name: "Postmortem", exact: true }).click();
  await expect(page.locator(".postmortem-document")).toBeVisible();
  await page
    .locator(".incident-screen > .tabs")
    .getByRole("button", { name: "Overview", exact: true })
    .click();
  await page
    .locator(".undo-entry")
    .first()
    .getByRole("button", { name: "Undo", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Undo follows the same backend policy",
  );
  await expect(page.getByRole("dialog")).toContainText("ACTIVATE $STMT1");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("link", { name: /Knowledge/ }).click();
  await page.getByLabel("Acting persona").selectOption("u_dave");
  const dynamic = page
    .locator(".claim-card")
    .filter({ hasText: "When a CPU halts at peak" });
  await expect(dynamic).toBeVisible();
  await dynamic.getByRole("button", { name: "Confirm", exact: true }).click();
  await page.getByRole("button", { name: "Confirm & index claim" }).click();
  const scopeClaim = page
    .locator(".claim-card")
    .filter({ hasText: "Adding eight ATM-AUTH static servers" });
  await scopeClaim
    .getByRole("button", { name: "Edit & confirm", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Scope / condition", exact: true })
    .fill("TORBANK · Black Friday 11:00–13:00 · one CPU down");
  await page.getByLabel("Calendar scope", { exact: true }).fill("black_friday");
  await page.getByRole("button", { name: "Confirm & index claim" }).click();
  await page.getByRole("link", { name: "Trust Ledger", exact: true }).click();
  await page.getByRole("button", { name: "Review promotion" }).click();
  await page
    .getByLabel("Reason", { exact: true })
    .fill("20 clean read-only runs reviewed against the incident evidence.");
  await page.getByRole("button", { name: "Grant L2", exact: true }).click();
  await page.getByRole("link", { name: "Audit", exact: true }).click();
  await page.getByRole("button", { name: "Verify chain", exact: true }).click();
  await expect(page.getByText(/Chain verified ·/)).toBeVisible();
  await page
    .getByRole("button", { name: /^Inspect audit entry / })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toContainText("Recorded payload");
  await expect(page.getByRole("dialog")).toContainText("Previous hash");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.screenshot({
    path: "test-results/audit-verified.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("professional workspace: diagnostics, keyboard tabs and governed manual commands", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  await page.getByRole("button", { name: /N-1 at risk/ }).click();
  await expect(page.getByRole("dialog")).toContainText("N-1 capacity headroom");
  await expect(page.getByRole("dialog")).toContainText(/worst survivor/i);
  await page.getByRole("button", { name: "Close", exact: true }).click();
  const diagnosticTabs = page.getByRole("tablist", {
    name: "System diagnostics",
  });
  await diagnosticTabs
    .getByRole("tab", { name: "Service health", exact: true })
    .focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    diagnosticTabs.getByRole("tab", { name: "Servers", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByRole("columnheader", { name: "Running / max" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inspect ATM-AUTH", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("Source evidence");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await diagnosticTabs
    .getByRole("tab", { name: "Processors", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "TMF audit headroom" }),
  ).toBeVisible();
  await diagnosticTabs
    .getByRole("tab", { name: "Events", exact: true })
    .click();
  await expect(page.getByLabel("Filter event stream")).toBeVisible();
  await diagnosticTabs
    .getByRole("tab", { name: "Service health", exact: true })
    .click();
  await page.getByRole("button", { name: "1h", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "1h", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Expand command workspace" }).click();
  await expect(page.getByLabel("Catalog command")).toBeVisible();
  await page
    .getByLabel("Catalog command")
    .fill("PATHCOM $PM1; STATS SERVER ATM-AUTH");
  await page.getByLabel("Catalog command").press("Enter");
  const check = page.getByRole("article", {
    name: "ATM authorization performance",
    exact: true,
  });
  await expect(check).toContainText("STATS SERVER ATM-AUTH");
  await check.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("STATS SERVER ATM-AUTH");
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  await expect(check).toContainText("done");
  await page.getByRole("tab", { name: "Event stream", exact: true }).click();
  await expect(page.locator(".dock-scroll")).toContainText("Event stream");
  await page
    .getByRole("tab", { name: "Command workspace", exact: true })
    .click();
  await expect(page.locator(".terminal-host")).toContainText(
    "STATS SERVER ATM-AUTH",
    { timeout: 15000 },
  );
  await page.getByRole("button", { name: "Restore command workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Your services, at a glance." }),
  ).toBeVisible();
  await page.getByRole("button", { name: /View all \d+ cards/ }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Conversation & investigation",
  );
  await expect(page.getByRole("dialog")).toContainText(
    "ATM authorization performance",
  );
});

test("safety: destructive requests stay out of the terminal", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  await page.getByLabel("Ask Baton", { exact: true }).fill("reload CPU 3");
  await page.getByRole("button", { name: "Send message" }).click();
  const blocked = page.getByRole("article", {
    name: "Action blocked",
    exact: true,
  });
  await expect(blocked).toContainText("human-only");
  await expect(
    blocked.getByRole("button", { name: "Approve", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("switch", { name: "Read-only mode", exact: true })
    .check();
  await expect(page.getByText("Read-only safeguards active")).toBeVisible();
});

test("layout: compact viewport, local fonts and no page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await expect(page.getByText("Ready for your next check.")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(await page.evaluate(() => document.fonts.check("13px Inter"))).toBe(
    true,
  );
  await page.screenshot({
    path: "test-results/console-1280.png",
    fullPage: true,
  });
});

test("plain language, live parameter preview and cited teaching answer", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  await page.getByRole("button", { name: "Is ATM auth keeping up?" }).click();
  const card = page.getByRole("article", {
    name: "ATM authorization performance",
    exact: true,
  });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByText("Parameters validated by backend")).toBeVisible();
  await page
    .getByRole("button", { name: "Confirm as Priya", exact: true })
    .click();
  await expect(card).toContainText(
    "within the Black Friday late-morning range",
  );
  await page
    .getByLabel("Ask Baton", { exact: true })
    .fill("What's the difference between NUMSTATIC and MAXSERVERS?");
  await page.getByRole("button", { name: "Send message" }).click();
  const answer = page.getByRole("article", {
    name: "NUMSTATIC and MAXSERVERS",
    exact: true,
  });
  await expect(answer).toContainText("must not exceed");
  await answer
    .getByRole("button", { name: "Concept note", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "floor of static servers",
  );
});

test("all P0 routes render without browser exceptions", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  const screens = [
    ["Incidents", "Incident Room"],
    ["Knowledge", "Knowledge Studio"],
    ["Trust Ledger", "Trust Ledger"],
    ["Audit", "Audit"],
    ["Evaluation", "Evaluation"],
  ];
  for (const [link, heading] of screens) {
    await page.getByRole("link", { name: new RegExp(`^${link}`) }).click();
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: `test-results/route-${link.toLowerCase().replaceAll(" ", "-")}.png`,
      fullPage: true,
    });
  }
  expect(errors).toEqual([]);
});

// P1 what-if mini charts on the decision card (mock mode, recorded run).
test("decision card shows what-if predictions", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("All streams connected")).toBeVisible();
  await page.getByRole("button", { name: "Director", exact: true }).click();
  await page.getByRole("button", { name: "CPU 3 halt", exact: true }).click();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  const auditCard = page.getByRole("article", { name: "TMF audit trail status", exact: true });
  await auditCard.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByRole("button", { name: "Confirm as Priya" }).click();
  const decision = page.getByRole("article", { name: "Options", exact: true });
  await expect(decision).toBeVisible();
  await expect(decision.locator(".prediction-strip")).toContainText("Do nothing");
  await expect(decision.locator(".prediction").first()).toBeVisible();
  await decision.scrollIntoViewIfNeeded();
  await decision.screenshot({ path: "test-results/whatif-decision.png" });
});
