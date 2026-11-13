/**
 * Terrain and Hazard Analysis Utilities (§3.4).
 *
 * Coordinate derivation protocol:
 * - Cost matrix is indexed as cost[row][col].
 * - Classification is derived SOLELY from numerical traversal costs — NEVER from visual topography.
 *   - SAFE: cost === 1.0 (nominal rolling resistance regolith)
 *   - CAUTION: cost > 2.0 and cost !== Infinity (loose sand ripples, slopes >= 12°)
 *   - IMPASSABLE: cost === Infinity or cost === "Infinity" (rollover slopes >= 20°, scarps, boulders)
 * - Plotly 3D scatter coordinate alignment: x = col, y = row, z = elevationAt(elevation, row, col).
 */

import { elevationAt } from './coordinateMapping';

export function extractHazardCoordinates(costMatrix, elevation, verticalOffset = 1.0, displayScale = 1.0) {
  const cautionCells = [];
  const impassableCells = [];

  if (!costMatrix || !Array.isArray(costMatrix) || !elevation) {
    return { cautionCells, impassableCells };
  }

  const rows = costMatrix.length;
  const cols = costMatrix[0]?.length || 0;

  for (let r = 0; r < rows; r++) {
    const row = costMatrix[r];
    for (let c = 0; c < cols; c++) {
      const rawCost = row[c];
      const isImpassable = rawCost === Infinity || rawCost === 'Infinity' || rawCost >= 1e9;
      const numericCost = typeof rawCost === 'number' ? rawCost : parseFloat(rawCost);
      const isCaution = !isImpassable && numericCost > 2.0;

      if (isImpassable || isCaution) {
        const zBase = elevationAt(elevation, r, c);
        if (zBase !== null) {
          const pt = {
            x: c,
            y: r,
            z: (zBase + verticalOffset) * displayScale,
            cost: isImpassable ? '∞' : numericCost.toFixed(2),
          };
          if (isImpassable) {
            impassableCells.push(pt);
          } else {
            cautionCells.push(pt);
          }
        }
      }
    }
  }

  return { cautionCells, impassableCells };
}

/**
 * Returns cost classification and human-readable label from numerical cost value.
 */
export function getCostClassification(cost) {
  if (cost === Infinity || cost === 'Infinity' || cost >= 1e9) {
    return { classKey: 'HAZARD', label: 'IMPASSABLE HAZARD', color: 'var(--hazard)' };
  }
  const num = typeof cost === 'number' ? cost : parseFloat(cost);
  if (num > 2.0) {
    return { classKey: 'CAUTION', label: `CAUTION (${num.toFixed(1)}x)`, color: 'var(--caution)' };
  }
  return { classKey: 'SAFE', label: 'SAFE REGOLITH (1.0x)', color: 'var(--safe)' };
}

/**
 * Downsampling utility for large grids (> 300x300 per §9).
 * Preserves the original matrix in state; creates a stride-reduced display copy.
 */
export function downsampleMatrix(matrix, stride = 2) {
  if (!matrix || !Array.isArray(matrix)) return matrix;
  const rows = matrix.length;
  const cols = matrix[0]?.length || 0;
  if (rows <= 300 && cols <= 300) return matrix;

  const sampled = [];
  for (let r = 0; r < rows; r += stride) {
    const row = matrix[r];
    const newRow = [];
    for (let c = 0; c < cols; c += stride) {
      newRow.push(row[c]);
    }
    sampled.push(newRow);
  }
  return sampled;
}
