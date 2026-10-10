import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

const venvPython = process.platform === "win32"
  ? "../backend/.venv/Scripts/python.exe"
  : "../backend/.venv/bin/python";
const python = process.env.VCW_TEST_PYTHON || (existsSync(venvPython) ? venvPython : "python");

export default defineConfig({
  testDir: "./tests/integration",
  outputDir: "./.local/integration-results",
  workers: 1,
  timeout: 45000,
  use: { baseURL: externalBaseUrl || "http://127.0.0.1:5174", trace: "retain-on-failure" },
  webServer: externalBaseUrl ? undefined : [
    {
      command: `"${python}" tests/serve_api.py`,
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
