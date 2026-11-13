/**
 * Hazard & Caution Terrain Overlay Generator (§3.4).
 *
 * Coordinate Derivation Documentation:
 * Coordinates are extracted directly from the verified 2D numerical cost_map array:
 * - Each cell at matrix indices (r, c) is inspected:
 *   - IMPASSABLE: cost_map[r][c] === Infinity || cost_map[r][c] === "Infinity" || cost_map[r][c] >= 1e9
 *   - CAUTION: cost_map[r][c] > 2.0 and not impassable
 * - Spatial coordinate mapping:
 *   - x = c (column index, matching Plotly Cartesian horizontal)
 *   - y = r (row index, matching Plotly Cartesian depth)
 *   - z = (elevationAt(elevation, r, c) + verticalOffset) * displayScale
 * - Classification is derived SOLELY from numerical cost constraints — never visual appearance.
 */

import { extractHazardCoordinates } from '../../utils/terrainHelpers';

export function buildHazardTraces(costMatrix, elevation, options = {}) {
  const {
    showHazards = true,
    showCaution = true,
    verticalOffset = 1.2,
    displayScale = 1.0,
  } = options;

  if (!showHazards && !showCaution) return [];
  if (!costMatrix || !elevation) return [];

  const { cautionCells, impassableCells } = extractHazardCoordinates(
    costMatrix,
    elevation,
    verticalOffset,
    displayScale
  );

  const traces = [];

  // 1. Impassable Hazards Overlay (Crimson #EF4444)
  if (showHazards && impassableCells.length > 0) {
    traces.push({
      type: 'scatter3d',
      mode: 'markers',
      name: `Impassable Hazard (${impassableCells.length} cells)`,
      legendgroup: 'hazards',
      x: impassableCells.map((pt) => pt.x),
      y: impassableCells.map((pt) => pt.y),
      z: impassableCells.map((pt) => pt.z),
      marker: {
        size: 3.5,
        color: '#EF4444',
        opacity: 0.75,
        symbol: 'circle',
      },
      hoverinfo: 'text',
      hovertext: impassableCells.map(
        (pt) => `IMPASSABLE HAZARD<br>Row: ${pt.y}, Col: ${pt.x}<br>Elevation: ${(pt.z / displayScale).toFixed(1)} m`
      ),
    });
  }

  // 2. Caution Terrain Overlay (Amber #F59E0B)
  if (showCaution && cautionCells.length > 0) {
    traces.push({
      type: 'scatter3d',
      mode: 'markers',
      name: `Caution Terrain (${cautionCells.length} cells)`,
      legendgroup: 'hazards',
      x: cautionCells.map((pt) => pt.x),
      y: cautionCells.map((pt) => pt.y),
      z: cautionCells.map((pt) => pt.z),
      marker: {
        size: 3,
        color: '#F59E0B',
        opacity: 0.6,
        symbol: 'circle',
      },
      hoverinfo: 'text',
      hovertext: cautionCells.map(
        (pt) => `CAUTION ZONE (Cost: ${pt.cost})<br>Row: ${pt.y}, Col: ${pt.x}<br>Elevation: ${(pt.z / displayScale).toFixed(1)} m`
      ),
    });
  }

  return traces;
}
