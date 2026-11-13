/**
 * Rover Telemetry Marker Trace Generator (§3.5).
 *
 * Rules:
 * - Validates coordinate bounds against DEM before placing.
 * - Marker: scatter3d, mode: 'markers+text', color: #06B6D4 (cyan), size: 9, symbol: 'diamond'.
 * - Callout text: '(row: R, col: C) · Z m' in JetBrains Mono.
 * - z = DEM value at (row, col) + roverOffset (display only).
 */

import { elevationAt, isInsideBounds } from '../../utils/coordinateMapping';

export function buildRoverMarkerTrace(roverPos, elevation, options = {}) {
  const {
    roverOffset = 3.0,
    displayScale = 1.0,
    onOutOfBounds = null,
  } = options;

  if (!roverPos || !Array.isArray(roverPos) || roverPos.length < 2 || !elevation) {
    return null;
  }

  const [row, col] = roverPos;
  const rows = elevation.length;
  const cols = elevation[0]?.length || 0;

  if (!isInsideBounds(row, col, rows, cols)) {
    if (onOutOfBounds) {
      onOutOfBounds({ row, col, rows, cols });
    }
    return null;
  }

  const baseZ = elevationAt(elevation, row, col);
  if (baseZ === null) return null;

  const displayZ = (baseZ + roverOffset) * displayScale;

  return {
    type: 'scatter3d',
    mode: 'markers+text',
    name: 'MARS-09 Rover',
    x: [col],
    y: [row],
    z: [displayZ],
    marker: {
      symbol: 'diamond',
      size: 9,
      color: '#06B6D4',
      line: {
        color: '#FFFFFF',
        width: 2,
      },
    },
    text: [`(${row}, ${col}) · ${baseZ.toFixed(1)} m`],
    textposition: 'top center',
    textfont: {
      family: 'JetBrains Mono, monospace',
      size: 11,
      color: '#06B6D4',
    },
    hoverinfo: 'text',
    hovertext: `MARS-09 ROVER POSITION<br>Row: ${row}, Col: ${col}<br>Terrain Elevation: ${baseZ.toFixed(1)} m`,
  };
}
