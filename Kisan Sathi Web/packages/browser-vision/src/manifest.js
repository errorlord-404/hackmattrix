const HASH = /^[a-f0-9]{64}$/i;

export class VisionManifestError extends Error {
  constructor(message, code = 'vision_manifest_invalid') {
    super(message);
    this.name = 'VisionManifestError';
    this.code = code;
  }
}

export function validateReleaseDescriptor(descriptor, now = Date.now()) {
  if (!descriptor || descriptor.status !== 'approved' || descriptor.activationAllowed !== true) {
    throw new VisionManifestError('No approved browser vision release is available.', 'release_not_approved');
  }
  if (!descriptor.releaseId || !descriptor.manifestSha256 || !HASH.test(descriptor.manifestSha256)) {
    throw new VisionManifestError('The release descriptor identity is incomplete.');
  }
  if (!descriptor.expiresAt || Date.parse(descriptor.expiresAt) <= now) {
    throw new VisionManifestError('The browser vision release descriptor is expired.', 'release_expired');
  }
  for (const [name, artifact] of Object.entries(descriptor.artifacts || {})) {
    if (!artifact?.url || !HASH.test(artifact.sha256) || !Number.isInteger(artifact.sizeBytes) || artifact.sizeBytes <= 0) {
      throw new VisionManifestError(`Artifact ${name} is incomplete.`);
    }
  }
  if (!descriptor.preprocessing || !Array.isArray(descriptor.cropIds) || !descriptor.cropIds.length) {
    throw new VisionManifestError('The release preprocessing or crop scope is missing.');
  }
  if (descriptor.signatureAlgorithm) {
    if (descriptor.signatureAlgorithm !== 'hmac-sha256' || !HASH.test(descriptor.signature)) {
      throw new VisionManifestError('The server release descriptor signature is invalid.', 'descriptor_signature_invalid');
    }
    if (!descriptor.preprocessingVersion) {
      throw new VisionManifestError('The signed release descriptor has no preprocessing version.');
    }
  }
  return Object.freeze(structuredClone(descriptor));
}

export async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

export async function verifyArtifactBytes(bytes, artifact) {
  if (bytes.byteLength !== artifact.sizeBytes) return false;
  return (await sha256Hex(bytes)).toLowerCase() === artifact.sha256.toLowerCase();
}
