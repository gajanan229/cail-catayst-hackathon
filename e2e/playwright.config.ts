import { defineConfig } from "../frontend/node_modules/@playwright/test/index.mjs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const live = process.env.BATON_LIVE === "1";
const url = live ? "http://127.0.0.1:5174" : "http://127.0.0.1:5173";
export default defineConfig({
  testDir: ".",
  testMatch: live ? "live.spec.ts" : "golden.spec.ts",
  timeout: live ? 180000 : 90000,
  fullyParallel: false,
  workers: 1,
  outputDir: path.join(root, "frontend/test-results"),
  reporter: [["list"]],
  use: {
    baseURL: url,
    viewport: { width: 1440, height: 900 },
    channel: "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: live ? "npm run dev -- --port 5174" : "npm run dev:mock",
    cwd: path.join(root, "frontend"),
    url,
    reuseExistingServer: true,
    timeout: 30000,
  },
});
