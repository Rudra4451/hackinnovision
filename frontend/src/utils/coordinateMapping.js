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
