export const UNKNOWN_CROP = 'unknown';

export function cropRoutingState(crop, confirmed) {
  if (!confirmed) return { status: 'needs_confirmation', message: 'Confirm the crop before a disease specialist is selected.' };
  if (!crop || crop === UNKNOWN_CROP) return { status: 'unknown_crop', message: 'The crop is unknown. Save the photo for follow-up; do not select a disease specialist.' };
  return { status: 'ready', message: `A ${crop} specialist can be selected when a released model is available.` };
}

export function cropOptions(currentCrop) {
  const defaults = ['tomato', 'rice', 'cotton', 'wheat', 'maize', 'potato', 'chilli'];
  const normalized = String(currentCrop || '').trim().toLowerCase();
  return [...new Set([normalized, ...defaults].filter(Boolean))];
}
