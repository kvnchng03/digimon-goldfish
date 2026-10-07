import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export default defineConfig({
  testDir: './tests',
  outputDir: join(tmpdir(), 'glowing-dawn-guide-tests'),
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    channel: process.env.CI ? undefined : 'chrome',
    viewport: { width: 1440, height: 1000 },
    colorScheme: 'light',
    screenshot: 'only-on-failure',
  },
  webServer: [{
    command: 'npm run preview -- --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
  }, {
    command: 'npm run preview -- --port 4174 --base /pages-check/',
    url: 'http://127.0.0.1:4174/pages-check/',
    reuseExistingServer: !process.env.CI,
  }],
});
