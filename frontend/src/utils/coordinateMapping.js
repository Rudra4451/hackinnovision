/**
 * Coordinate Mapping and Spatial Transformations (§3.6).
 *
 * Single source of truth:
 * - DEM matrix indexing: [row][col]
 * - Plotly 3D Scatter/Surface: x = col, y = row, z = elevation
 * - Rover simulation state: [row, col]
 * - Route path tuples: [row, col]
 *
 * Rule: No component may index elevation[row][col] directly.
 */

/**
 * Maps a grid coordinate (row, col) to Plotly Cartesian axes (x=col, y=row).
 */
export function demToPlotly(row, col) {
  return { x: col, y: row };
}

/**
 * Bounds checking helper for any (row, col) against grid dimensions.
 */
export function isInsideBounds(row, col, rows, cols) {
  return (
    typeof row === 'number' &&
    typeof col === 'number' &&
    Number.isInteger(row) &&
    Number.isInteger(col) &&
    row >= 0 &&
    row < rows &&
    col >= 0 &&
    col < cols
  );
}

/**
 * Safely accesses elevation at (row, col) with strict bounds checking.
 * Returns the exact elevation number in meters, or null if out of bounds or invalid.
 */
export function elevationAt(elevation, row, col) {
  if (!elevation || !Array.isArray(elevation)) return null;
  const rows = elevation.length;
  if (rows === 0) return null;
  const cols = elevation[0]?.length || 0;

  if (!isInsideBounds(row, col, rows, cols)) {
    return null;
  }

  const val = elevation[row][col];
  if (typeof val !== 'number' || Number.isNaN(val) || !Number.isFinite(val)) {
    return null;
  }
  return val;
}

/**
 * Transforms an ordered list of [row, col] path waypoints into Plotly 3D scatter arrays.
 * Applies display vertical offset and optional display scaling.
 */
export function routeToTrace(path, elevation, verticalOffset = 2.0, displayScale = 1.0) {
  const x = [];
  const y = [];
  const z = [];
  const outOfBounds = [];

  if (!Array.isArray(path) || !elevation) {
    return { x, y, z, outOfBounds };
  }

  const rows = elevation.length;
  const cols = elevation[0]?.length || 0;

  for (let i = 0; i < path.length; i++) {
    const pt = path[i];
    if (!pt || pt.length < 2) continue;
    const [row, col] = pt;

    if (!isInsideBounds(row, col, rows, cols)) {
      outOfBounds.push({ index: i, row, col });
      continue;
    }

    const baseZ = elevationAt(elevation, row, col);
    if (baseZ !== null) {
      x.push(col);
      y.push(row);
      z.push((baseZ + verticalOffset) * displayScale);
    }
  }

  return { x, y, z, outOfBounds };
}

/**
 * Three.js 3D Coordinate Transformations
 */

export function gridToThree(row, col, elevation, rows, cols, minElev = 0, elevScale = 0.25, verticalOffset = 0) {
  const offsetX = (cols - 1) / 2;
  const offsetZ = (rows - 1) / 2;
  const x = col - offsetX;
  const z = row - offsetZ;
  const rawElev = elevationAt(elevation, row, col) ?? minElev;
  const y = (rawElev - minElev) * elevScale + verticalOffset;
  return { x, y, z, rawElev };
}

export function threeToGrid(x, z, rows, cols) {
  const offsetX = (cols - 1) / 2;
  const offsetZ = (rows - 1) / 2;
  const col = Math.max(0, Math.min(cols - 1, Math.round(x + offsetX)));
  const row = Math.max(0, Math.min(rows - 1, Math.round(z + offsetZ)));
  return { row, col };
}

/**
 * Continuous bilinear interpolation of DEM elevation for smooth rover kinematics.
 */
export function bilinearElevation(rowFloat, colFloat, elevation, rows, cols) {
  if (!elevation || rows === 0 || cols === 0) return 0;
  const r0 = Math.max(0, Math.min(rows - 1, Math.floor(rowFloat)));
  const r1 = Math.max(0, Math.min(rows - 1, r0 + 1));
  const c0 = Math.max(0, Math.min(cols - 1, Math.floor(colFloat)));
  const c1 = Math.max(0, Math.min(cols - 1, c0 + 1));

  const fr = rowFloat - r0;
  const fc = colFloat - c0;

  const e00 = elevationAt(elevation, r0, c0) ?? 0;
  const e10 = elevationAt(elevation, r1, c0) ?? 0;
  const e01 = elevationAt(elevation, r0, c1) ?? 0;
  const e11 = elevationAt(elevation, r1, c1) ?? 0;

  return (1 - fr) * (1 - fc) * e00 + fr * (1 - fc) * e10 + (1 - fr) * fc * e01 + fr * fc * e11;
}

