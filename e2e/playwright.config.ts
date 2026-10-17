import { defineConfig } from '../frontend/node_modules/@playwright/test/index.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export default defineConfig({
  testDir:'.',timeout:60000,fullyParallel:false,workers:1,
  outputDir:path.join(root,'frontend/test-results'),
  reporter:[['list']],
  use:{baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:900},channel:'chrome',trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:{command:'npm run dev:mock',cwd:path.join(root,'frontend'),url:'http://127.0.0.1:5173',reuseExistingServer:true,timeout:30000},
});
