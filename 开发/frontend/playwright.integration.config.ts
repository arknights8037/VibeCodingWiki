import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/integration",
  outputDir: "./.local/integration-results",
  workers: 1,
  timeout: 45000,
  use: { baseURL: "http://127.0.0.1:5174", trace: "retain-on-failure" },
  webServer: [
    {
      command: '"../backend/.venv/Scripts/python.exe" tests/serve_api.py',
      url: "http://127.0.0.1:8001/healthz",
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { VCW_API_TARGET: "http://127.0.0.1:8001" },
      reuseExistingServer: false,
    },
  ],
});
