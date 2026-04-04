import { defineConfig, devices } from '@playwright/test';

const backendPort = 17846;
const frontendPort = 1421;

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure'
  },
  webServer: [
    {
      command:
        "rm -rf .playwright && mkdir -p .playwright/data .playwright/config .playwright/cache && cd backend && PYTHON_BIN=.venv/bin/python && if [ ! -x \"$PYTHON_BIN\" ]; then PYTHON_BIN=python; fi && ONCOWATCH_ENV=test ONCOWATCH_BACKEND_HOST=127.0.0.1 ONCOWATCH_BACKEND_PORT=17846 ONCOWATCH_DATA_DIR=$PWD/../.playwright/data ONCOWATCH_CONFIG_DIR=$PWD/../.playwright/config ONCOWATCH_CACHE_DIR=$PWD/../.playwright/cache \"$PYTHON_BIN\" -m uvicorn app.main:app --host 127.0.0.1 --port 17846",
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000
    },
    {
      command: 'VITE_API_BASE=http://127.0.0.1:17846 npm --workspace apps/desktop run dev -- --host 127.0.0.1 --port 1421',
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 120_000
    }
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
