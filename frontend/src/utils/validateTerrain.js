/**
 * Validation module for Martian Digital Elevation Model (DEM) data (§3.1).
 *
 * Rules:
 * 1. Matrix must be a 2D array, numeric, and non-ragged.
 * 2. Reject NaN, null, undefined, Infinity cells — never silently coerce.
 * 3. Preserve original values. Never derive elevation from cost map.
 * 4. Return diagnostic error details if invalid.
 */

export function validateTerrain(demData) {
  if (!demData || typeof demData !== 'object') {
    return {
      isValid: false,
      reason: 'MISSING_PAYLOAD',
      message: 'DEM data payload was not supplied or is not an object.',
      errors: ['Payload is null or undefined'],
      badSamples: [],
    };
  }

  const elevation = demData.elevation;
  if (!Array.isArray(elevation) || elevation.length === 0) {
    return {
      isValid: false,
      reason: 'EMPTY_ELEVATION',
      message: 'Elevation matrix is missing or empty array.',
      errors: ['elevation array is empty or not an array'],
      badSamples: [],
    };
  }

  const rows = elevation.length;
  const cols = Array.isArray(elevation[0]) ? elevation[0].length : 0;

  if (cols === 0) {
    return {
      isValid: false,
      reason: 'INVALID_DIMENSIONS',
      message: `Elevation row 0 has length 0.`,
      errors: ['Row length is 0'],
      badSamples: [],
    };
  }

  const errors = [];
  const badSamples = [];
  let minElevation = Infinity;
  let maxElevation = -Infinity;

  for (let r = 0; r < rows; r++) {
    const row = elevation[r];
    if (!Array.isArray(row)) {
      errors.push(`Row ${r} is not an array`);
      break;
    }
    if (row.length !== cols) {
      errors.push(`Ragged matrix detected: row ${r} length ${row.length} != expected ${cols}`);
      if (errors.length >= 10) break;
    }

    for (let c = 0; c < row.length; c++) {
      const val = row[c];
      if (typeof val !== 'number' || Number.isNaN(val) || !Number.isFinite(val)) {
        badSamples.push({ row: r, col: c, value: String(val) });
        if (badSamples.length >= 15) break;
      } else {
        if (val < minElevation) minElevation = val;
        if (val > maxElevation) maxElevation = val;
      }
    }
    if (badSamples.length >= 15) break;
  }

  if (errors.length > 0 || badSamples.length > 0) {
    return {
      isValid: false,
      reason: 'INVALID_DATA',
      message: 'Elevation matrix contains non-finite, NaN, or ragged values.',
      errors,
      badSamples,
      rows,
      cols,
    };
  }

  return {
    isValid: true,
    rows,
    cols,
    minElevation,
    maxElevation,
    elevationUnit: demData.elevationUnit || 'meters',
    source: demData.source || 'HiRISE/MOLA Benchmark',
  };
}
