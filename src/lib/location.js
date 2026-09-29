export function normalizeLocationPart(value) {
  return String(value || '').replace(/\([^)]*\)/g, '').replace(/\s+/g, ' ').trim();
}

export function parseDisplayLocation(location) {
  const parts = normalizeLocationPart(location).split(',').map((part) => part.trim()).filter(Boolean);
  return {
    district: parts.length > 1 ? parts.at(-2) : undefined,
    state: parts.length ? parts.at(-1) : undefined,
  };
}

export function selectedLocation(profile, field) {
  return {
    latitude: field?.centroid_lat ?? profile?.latitude ?? null,
    longitude: field?.centroid_lon ?? profile?.longitude ?? null,
    district: field?.district || parseDisplayLocation(profile?.location).district,
    state: field?.state || parseDisplayLocation(profile?.location).state,
    label: field?.name || normalizeLocationPart(profile?.location) || 'Selected farm',
  };
}

export function hasCoordinates(location) {
  return location?.latitude != null && location?.longitude != null
    && location.latitude !== '' && location.longitude !== ''
    && Number.isFinite(Number(location.latitude)) && Number.isFinite(Number(location.longitude));
}
