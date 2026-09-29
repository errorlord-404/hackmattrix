import { validateReleaseDescriptor, verifyArtifactBytes } from './manifest.js';

export async function loadApprovedSession(descriptor, { ortModule, fetchImpl = globalThis.fetch } = {}) {
  const validated = validateReleaseDescriptor(descriptor);
  if (!ortModule) throw new Error('onnxruntime-web is required for browser inference');
  const modelResponse = await fetchImpl(validated.artifacts.model.url, { credentials: 'same-origin' });
  if (!modelResponse.ok) throw new Error(`model download failed (${modelResponse.status})`);
  const modelBytes = await modelResponse.arrayBuffer();
  if (!(await verifyArtifactBytes(modelBytes, validated.artifacts.model))) throw new Error('model checksum mismatch');
  ortModule.env.wasm.wasmPaths = validated.runtime?.wasmPaths || ortModule.env.wasm.wasmPaths;
  const providers = globalThis.navigator?.gpu && validated.runtime?.webgpu ? ['webgpu', 'wasm'] : ['wasm'];
  const session = await ortModule.InferenceSession.create(modelBytes, { executionProviders: providers });
  return { session, descriptor: validated, providers };
}

export function topCandidates(logits, labels, topK = 3) {
  if (!Array.isArray(labels) || labels.length !== logits.length) throw new Error('labels and logits are not aligned');
  const max = Math.max(...logits);
  const exponentials = logits.map((value) => Math.exp(value - max));
  const denominator = exponentials.reduce((sum, value) => sum + value, 0);
  return logits.map((_, index) => ({ label: labels[index], confidence: exponentials[index] / denominator, index }))
    .sort((left, right) => right.confidence - left.confidence).slice(0, Math.max(1, topK));
}
