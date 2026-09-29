import { test, expect } from '@playwright/test';

test('web shell and liveness are reachable', async ({ page, request }) => {
  const health = await request.get('/healthz');
  expect(health.ok()).toBeTruthy();
  await page.goto('/');
  await expect(page).toHaveTitle(/Kisan Sathi/i);
});

test('device setup route stays protected and non-authoritative', async ({ page }) => {
  await page.goto('/device-setup');
  await expect(page.getByRole('heading', { name: /Sign in to Kisan Sathi/i })).toBeVisible();
  await expect(page.getByText(/hardware control|pairing|device action/i)).toHaveCount(0);
});
