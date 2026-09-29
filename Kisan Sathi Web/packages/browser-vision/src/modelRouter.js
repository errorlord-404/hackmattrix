const isApproved = (entry) => Boolean(
  entry?.status === 'approved'
  && entry?.artifacts?.release_manifest
  && entry?.artifacts?.model?.path
  && entry?.artifacts?.labels?.path
);

export function buildApprovedModelIndex(catalog) {
  const models = Array.isArray(catalog?.models) ? catalog.models : [];
  const identifier = models.find((entry) => entry.role === 'crop_identifier');
  const specialists = new Map(
    models
      .filter((entry) => entry.role === 'disease_specialist')
      .map((entry) => [entry.crop, entry]),
  );
  return {
    identifier: isApproved(identifier) ? identifier : null,
    specialists: new Map([...specialists].filter(([, entry]) => isApproved(entry))),
    coverage: [...(catalog?.coverage?.crop_ids ?? [])],
  };
}

export function selectHierarchicalRoute(
  catalog,
  candidates,
  { confirmedCrop = null, minimumScore = 0.75, minimumMargin = 0.12 } = {},
) {
  const index = buildApprovedModelIndex(catalog);
  if (confirmedCrop) {
    const specialist = index.specialists.get(confirmedCrop);
    return specialist
      ? { status: 'routed', crop: confirmedCrop, specialist, requiresFarmerConfirmation: false }
      : { status: 'needs_expert_review', crop: confirmedCrop, specialist: null, requiresFarmerConfirmation: false };
  }
  if (!index.identifier) {
    return { status: 'needs_crop_confirmation', crop: null, specialist: null, requiresFarmerConfirmation: true };
  }
  const ordered = [...(candidates ?? [])].sort((left, right) => right.score - left.score);
  if (!ordered.length) {
    return { status: 'needs_crop_confirmation', crop: null, specialist: null, requiresFarmerConfirmation: true };
  }
  const winner = ordered[0];
  const margin = winner.score - (ordered[1]?.score ?? 0);
  if (winner.score < minimumScore || margin < minimumMargin) {
    return { status: 'needs_crop_confirmation', crop: winner.crop, specialist: null, requiresFarmerConfirmation: true };
  }
  const specialist = index.specialists.get(winner.crop);
  return specialist
    ? { status: 'routed', crop: winner.crop, specialist, requiresFarmerConfirmation: false }
    : { status: 'needs_expert_review', crop: winner.crop, specialist: null, requiresFarmerConfirmation: false };
}

export function createLazyLoadPlan(catalog, route, { webGpuAvailable = false } = {}) {
  const index = buildApprovedModelIndex(catalog);
  if (!index.identifier || route?.status !== 'routed' || !route.specialist) {
    return { status: 'fallback', reason: route?.status ?? 'identifier_unavailable', target: 'server' };
  }
  const backends = webGpuAvailable ? ['webgpu', 'wasm'] : ['wasm'];
  return {
    status: 'ready',
    backends,
    stages: [
      { role: 'crop_identifier', modelId: index.identifier.model_id, lazy: false },
      { role: 'disease_specialist', modelId: route.specialist.model_id, crop: route.crop, lazy: true },
    ],
  };
}
