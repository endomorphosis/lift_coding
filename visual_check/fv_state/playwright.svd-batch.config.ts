import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

// Scratch config for the gap-pass SVD-132 batch harness (fv_state only).
// Mirrors build-tools/configs/playwright.app-audit-runner.config.ts: the
// webServer boots the repo's own `npm run desktop` on the leased port
// with --strictPort and never reuses a foreign server.
const here = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.SWISSKNIFE_APP_AUDIT_RUNNER_E2E_PORT || '3419');

export default defineConfig({
  testDir: here,
  testMatch: ['svd132-batch.spec.ts'],
  outputDir: resolve(here, 'playwright-batch-artifacts'),
  timeout: 30 * 60 * 1000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run desktop -- --port ${port} --strictPort`,
    cwd: '/home/hatch/workspace/lift_coding/swissknife',
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    timeout: 120 * 1000,
  },
});
