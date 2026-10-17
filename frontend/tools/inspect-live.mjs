import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:5174");
  await page.getByText("All streams connected").waitFor({ timeout: 15000 });
  await page.waitForTimeout(1500);
  await fs.mkdir("test-results", { recursive: true });
  await page.screenshot({
    path: "test-results/console-live.png",
    fullPage: true,
  });
  const alert = await page.getByRole("alert").allTextContents();
  console.log(
    JSON.stringify(
      {
        errors,
        alert,
        body: (await page.locator("body").innerText()).slice(0, 2200),
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
