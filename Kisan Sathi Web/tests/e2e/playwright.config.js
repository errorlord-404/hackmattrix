import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: ['**/*.spec.js'],
  timeout: 15000,
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: [['line']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8080',
    trace: 'retain-on-failure',
    ignoreHTTPSErrors: false,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'webgpu-approved', use: { ...devices['Desktop Chrome'] } },
  ],
});
