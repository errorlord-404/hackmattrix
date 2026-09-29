const EARTH_RADIUS_METRES = 6371008.8;
const SQUARE_METRES_PER_ACRE = 4046.8564224;

export function boundaryAreaAcres(points) {
  if (points.length < 3) return 0;
  const meanLatitude = points.reduce((sum, point) => sum + point[0], 0) / points.length;
  const latitudeScale = Math.PI * EARTH_RADIUS_METRES / 180;
  const longitudeScale = latitudeScale * Math.cos(meanLatitude * Math.PI / 180);
  let twiceArea = 0;
  for (let index = 0; index < points.length; index += 1) {
    const [latitude, longitude] = points[index];
    const [nextLatitude, nextLongitude] = points[(index + 1) % points.length];
    twiceArea += (longitude * longitudeScale) * (nextLatitude * latitudeScale)
      - (nextLongitude * longitudeScale) * (latitude * latitudeScale);
  }
  return Math.abs(twiceArea) / 2 / SQUARE_METRES_PER_ACRE;
}

function intersects(a, b, c, d) {
  const cross = (p, q, r) => (q[1] - p[1]) * (r[0] - p[0]) - (q[0] - p[0]) * (r[1] - p[1]);
  const abC = cross(a, b, c); const abD = cross(a, b, d);
  const cdA = cross(c, d, a); const cdB = cross(c, d, b);
  return abC * abD < 0 && cdA * cdB < 0;
}

export function boundaryError(points) {
  if (points.length < 3) return 'Tap at least three corners to draw your field.';
  if (points.length > 100) return 'This boundary has too many corners. Use at most 100.';
  if (points.some(([latitude, longitude]) => !Number.isFinite(latitude) || !Number.isFinite(longitude)
    || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)) return 'A boundary corner is outside valid map coordinates.';
  if (new Set(points.map(([latitude, longitude]) => `${latitude.toFixed(8)},${longitude.toFixed(8)}`)).size !== points.length) return 'Two boundary corners overlap. Move or remove one.';
  for (let first = 0; first < points.length; first += 1) {
    for (let second = first + 2; second < points.length; second += 1) {
      if (first === 0 && second === points.length - 1) continue;
      if (intersects(points[first], points[(first + 1) % points.length], points[second], points[(second + 1) % points.length])) return 'Boundary lines cross. Drag a corner to fix the shape.';
    }
  }
  if (boundaryAreaAcres(points) < 0.001) return 'The drawn area is too small. Spread the corners over the field.';
  return null;
}

export function farmerDrawnBoundary(points) {
  const error = boundaryError(points);
  if (error) throw new Error(error);
  const coordinates = points.map(([latitude, longitude]) => [longitude, latitude]);
  return {
    type: 'Feature',
    properties: { quality: 'farmer_drawn_unverified', source: 'farmer_map_editor' },
    geometry: { type: 'Polygon', coordinates: [[...coordinates, coordinates[0]]] },
  };
}

export function editableBoundaryPoints(feature) {
  const geometry = feature?.geometry || feature;
  if (geometry?.type !== 'Polygon') return [];
  const ring = geometry.coordinates?.[0];
  if (!Array.isArray(ring) || ring.length < 4) return [];
  return ring.slice(0, -1).map((position) => [position[1], position[0]]);
}
