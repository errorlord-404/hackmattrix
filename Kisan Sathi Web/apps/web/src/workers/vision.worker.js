import * as ort from 'onnxruntime-web';
import { loadApprovedSession, topCandidates } from '../../../../packages/browser-vision/src/runtime.js';

let active = null;

self.onmessage = async ({ data }) => {
  if (data?.type === 'cancel') {
    active = null;
    return;
  }
  if (data?.type !== 'screen') return;
  try {
    active = await loadApprovedSession(data.descriptor, { ortModule: ort });
    const tensor = new ort.Tensor('float32', data.tensor, [1, 3, data.height, data.width]);
    const output = await active.session.run({ [active.session.inputNames[0]]: tensor });
    const logits = Array.from(output[active.session.outputNames[0]].data);
    self.postMessage({
      type: 'candidate',
      releaseId: active.descriptor.releaseId,
      preprocessingVersion: active.descriptor.preprocessingVersion,
      descriptorSignature: active.descriptor.signature,
      descriptorExpiresAt: active.descriptor.expiresAt,
      providers: active.providers,
      candidates: topCandidates(logits, data.labels, 3),
    });
  } catch (error) {
    self.postMessage({ type: 'fallback', reason: error?.code || 'browser_inference_failed' });
  } finally {
    active = null;
  }
};
