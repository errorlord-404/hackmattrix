import { describe, expect, it } from 'vitest';
import { boundaryAreaAcres, boundaryError, editableBoundaryPoints, farmerDrawnBoundary } from './fieldBoundary.js';

describe('farmer-drawn boundaries', () => {
  const rectangle = [[18.5, 73.8], [18.5, 73.801], [18.501, 73.801], [18.501, 73.8]];

  it('saves a closed GeoJSON polygon with an unverified quality label', () => {
    const feature = farmerDrawnBoundary(rectangle);
    expect(feature.properties.quality).toBe('farmer_drawn_unverified');
    expect(feature.geometry.coordinates[0]).toHaveLength(5);
    expect(feature.geometry.coordinates[0][0]).toEqual([73.8, 18.5]);
    expect(feature.geometry.coordinates[0].at(-1)).toEqual([73.8, 18.5]);
    expect(boundaryAreaAcres(rectangle)).toBeGreaterThan(2);
    expect(editableBoundaryPoints(feature)).toEqual(rectangle);
  });

  it('rejects incomplete, overlapping, and crossing shapes', () => {
    expect(boundaryError(rectangle.slice(0, 2))).toMatch(/three corners/);
    expect(boundaryError([...rectangle.slice(0, 3), rectangle[0]])).toMatch(/overlap/);
    expect(boundaryError([rectangle[0], rectangle[2], rectangle[1], rectangle[3]])).toMatch(/cross/);
  });
});
