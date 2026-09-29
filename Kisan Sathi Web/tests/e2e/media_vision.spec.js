import { test, expect } from '@playwright/test';

test('vision descriptor fails closed without an approved release', async ({ request }) => {
  const response = await request.get('/api/v1/vision/descriptor');
  expect([401, 403, 503]).toContain(response.status());
  if (response.headers()['content-type']?.includes('application/json')) {
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/diagnosis.*authoritative/i);
  }
});
