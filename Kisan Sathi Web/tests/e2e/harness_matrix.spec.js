import { test, expect } from '@playwright/test';

test('harness liveness is same-origin and does not expose credentials', async ({ request }) => {
  const response = await request.get('/harness/healthz');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.service).toBe('kisansathi-harness');
  expect(JSON.stringify(body)).not.toMatch(/api[_-]?key|authorization|secret/i);
});
