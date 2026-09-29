import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import test from 'node:test';

import { buildApprovedModelIndex, createLazyLoadPlan, selectHierarchicalRoute } from '../src/modelRouter.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const catalogPath = path.resolve(here, '../../../models/catalog.json');
const scaffold = JSON.parse(readFileSync(catalogPath, 'utf8'));

function approvedCatalog() {
  const catalog = structuredClone(scaffold);
  for (const entry of catalog.models.filter((item) => item.role === 'crop_identifier' || item.crop === 'tomato')) {
    entry.status = 'approved';
    entry.artifacts.release_manifest = `releases/${entry.model_id}/manifest.json`;
    entry.artifacts.model = { path: `releases/${entry.model_id}/model.onnx`, sha256: 'a'.repeat(64), size_bytes: 1024 };
    entry.artifacts.labels = { path: `releases/${entry.model_id}/labels.json`, sha256: 'b'.repeat(64), size_bytes: 128 };
  }
  return catalog;
}

test('research entries never become browser-loadable', () => {
  const index = buildApprovedModelIndex(scaffold);
  assert.equal(index.identifier, null);
  assert.equal(index.specialists.size, 0);
  assert.equal(index.coverage.length, 26);
});

test('the browser asks for crop confirmation when identifier weights are unavailable', () => {
  const route = selectHierarchicalRoute(scaffold, [{ crop: 'tomato', score: 0.99 }]);
  assert.deepEqual(route, {
    status: 'needs_crop_confirmation',
    crop: null,
    specialist: null,
    requiresFarmerConfirmation: true,
  });
});

test('an approved router lazily selects only the matching approved specialist', () => {
  const catalog = approvedCatalog();
  const route = selectHierarchicalRoute(catalog, [
    { crop: 'tomato', score: 0.93 },
    { crop: 'potato', score: 0.05 },
  ]);
  const plan = createLazyLoadPlan(catalog, route, { webGpuAvailable: true });

  assert.equal(route.status, 'routed');
  assert.deepEqual(plan.backends, ['webgpu', 'wasm']);
  assert.deepEqual(plan.stages.map((stage) => stage.modelId), [
    'crop-identifier-india-common',
    'disease-tomato',
  ]);
  assert.equal(plan.stages[1].lazy, true);
});

test('a high-confidence crop with no approved specialist falls back safely', () => {
  const catalog = approvedCatalog();
  const route = selectHierarchicalRoute(catalog, [{ crop: 'potato', score: 0.98 }]);
  const plan = createLazyLoadPlan(catalog, route);
  assert.equal(route.status, 'needs_expert_review');
  assert.deepEqual(plan, { status: 'fallback', reason: 'needs_expert_review', target: 'server' });
});

test('ambiguous crop scores do not load any specialist', () => {
  const catalog = approvedCatalog();
  const route = selectHierarchicalRoute(catalog, [
    { crop: 'tomato', score: 0.82 },
    { crop: 'potato', score: 0.75 },
  ]);
  assert.equal(route.status, 'needs_crop_confirmation');
  assert.equal(route.specialist, null);
});
