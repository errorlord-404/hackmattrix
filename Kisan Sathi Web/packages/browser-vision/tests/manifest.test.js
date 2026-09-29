import assert from 'node:assert/strict';
import test from 'node:test';

import { VisionManifestError, validateReleaseDescriptor } from '../src/manifest.js';
import { topCandidates } from '../src/runtime.js';

const valid = {
  status: 'approved', activationAllowed: true, releaseId: 'release-1',
  manifestSha256: 'a'.repeat(64), expiresAt: '2099-01-01T00:00:00Z',
  cropIds: ['tomato'], preprocessing: { width: 2, height: 2 },
  artifacts: { model: { url: '/model.onnx', sha256: 'b'.repeat(64), sizeBytes: 4 } },
};

test('descriptor validation rejects unapproved releases', () => {
  assert.throws(() => validateReleaseDescriptor({ ...valid, status: 'candidate' }), VisionManifestError);
});

test('descriptor validation freezes a complete release', () => {
  const descriptor = validateReleaseDescriptor(valid);
  assert.equal(descriptor.releaseId, 'release-1');
  assert.equal(Object.isFrozen(descriptor), true);
});

test('signed descriptors require a valid signature and preprocessing version', () => {
  assert.throws(() => validateReleaseDescriptor({ ...valid, signatureAlgorithm: 'hmac-sha256', signature: 'bad', preprocessingVersion: 'v1' }), VisionManifestError);
  const descriptor = validateReleaseDescriptor({ ...valid, signatureAlgorithm: 'hmac-sha256', signature: 'c'.repeat(64), preprocessingVersion: 'v1' });
  assert.equal(descriptor.preprocessingVersion, 'v1');
});

test('top candidates returns normalized probabilities', () => {
  const candidates = topCandidates([0, 2], ['healthy', 'disease']);
  assert.equal(candidates[0].label, 'disease');
  assert.ok(Math.abs(candidates.reduce((sum, item) => sum + item.confidence, 0) - 1) < 1e-6);
});
