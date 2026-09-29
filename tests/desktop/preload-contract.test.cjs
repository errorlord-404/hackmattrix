const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '../..');

test('preload exposes only the farmer harness contract', () => {
  const preload = fs.readFileSync(path.join(root, 'desktop/preload.cjs'), 'utf8');
  assert.match(preload, /contextBridge\.exposeInMainWorld\('kisanHarness'/);
  assert.match(preload, /farmerId:\s*ipcRenderer\.sendSync\('kisansathi:farmer-id'\)/);
  assert.match(preload, /backendUrl:\s*ipcRenderer\.sendSync\('kisansathi:backend-url'\)/);
  assert.match(preload, /session-restart/);
  for (const key of ['session', 'chat', 'notifications', 'voice', 'approval', 'clarification', 'onEvent']) assert.match(preload, new RegExp(`\\b${key}\\b`));
  assert.doesNotMatch(preload, /require\(['"]node:/);
  assert.doesNotMatch(preload, /process\./);
});

test('desktop window keeps Node APIs out of the renderer', () => {
  const main = fs.readFileSync(path.join(root, 'desktop/main.cjs'), 'utf8');
  assert.match(main, /contextIsolation:\s*true/);
  assert.match(main, /nodeIntegration:\s*false/);
  assert.match(main, /sandbox:\s*true/);
  assert.match(main, /event\.returnValue = farmerId/);
  assert.match(main, /event\.returnValue = backendUrl/);
  assert.match(main, /KISANSATHI_BACKEND_URL \|\| 'http:\/\/127\.0\.0\.1:8001'/);
  assert.match(main, /kisansathi:show-alert-notification/);
  assert.match(main, /Notification\.isSupported/);
});
