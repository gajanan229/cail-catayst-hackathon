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
  await expect(page.getByText("Experience on your side.")).toBeVisible();
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
  await page.screenshot({
    path: "test-results/audit-verified.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
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
  await expect(page.getByText("Experience on your side.")).toBeVisible();
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
    ["Audit", "Every action, accounted for."],
    ["Evaluation", "Trust, measured."],
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
