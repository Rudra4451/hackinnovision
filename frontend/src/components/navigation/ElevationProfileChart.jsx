import React, { useMemo } from 'react';
import { elevationAt } from '../../utils/coordinateMapping';

/**
 * A.R.E.S. Elevation Profile Transect Chart
 * Brutalist Aerospace Telemetry: Zero gradients, zero neon glow, hairline grid lines #333333,
 * solid monochrome/accent profile line, tabular monospace numbers.
 */
export default function ElevationProfileChart({
  path = [],
  elevation,
  costMap,
  roverProgress = 0,
  totalDistance = 0,
  activeRoute = 'safest',
}) {
  const chartData = useMemo(() => {
    if (!path || path.length < 2 || !elevation) return null;

    const samples = [];
    let minZ = Infinity;
    let maxZ = -Infinity;

    for (let i = 0; i < path.length; i++) {
      const [r, c] = path[i];
      const z = elevationAt(elevation, r, c) ?? 0;
      const cost = costMap?.cost?.[r]?.[c] ?? 1.0;
      const isHazard = cost === 'Infinity' || cost === Infinity || cost >= 9999;
      const isCaution = typeof cost === 'number' && cost > 2.0 && !isHazard;

      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;

      samples.push({ index: i, r, c, z, isCaution, isHazard });
    }

    if (minZ === Infinity) minZ = 0;
    if (maxZ === -Infinity) maxZ = 60;
    const rangeZ = Math.max(1, maxZ - minZ);

    return { samples, minZ, maxZ, rangeZ };
  }, [path, elevation, costMap]);

  if (!chartData || chartData.samples.length < 2) {
    return (
      <div
        style={{
          height: '46px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#858585',
          fontSize: '10px',
          fontFamily: "'JetBrains Mono', monospace",
          border: '1px dashed #333333',
        }}
      >
        AWAITING TRAJECTORY TELEMETRY FOR ELEVATION TRANSECT
      </div>
    );
  }

  const { samples, minZ, maxZ, rangeZ } = chartData;
  const width = 480;
  const height = 48;
  const padY = 6;
  const padX = 10;
  const plotW = width - padX * 2;
  const plotH = height - padY * 2;

  // Build SVG path points
  const points = samples.map((s, idx) => {
    const x = padX + (idx / (samples.length - 1)) * plotW;
    const y = height - padY - ((s.z - minZ) / rangeZ) * plotH;
    return { x, y, ...s };
  });

  const pathD = points.reduce((acc, p, idx) => {
    return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  // Live Rover Position on the chart
  const curIdx = Math.max(0, Math.min(samples.length - 1, roverProgress));
  const k = Math.floor(curIdx);
  const t = curIdx - k;
  const p0 = points[k] || points[0];
  const p1 = points[Math.min(k + 1, points.length - 1)];

  const roverX = p0.x + (p1.x - p0.x) * t;
  const roverY = p0.y + (p1.y - p0.y) * t;
  const currentZ = p0.z + (p1.z - p0.z) * t;

  const lineColor = activeRoute === 'safest' ? '#0284C7' : '#DC2626';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', position: 'relative' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '9px',
          fontFamily: "'JetBrains Mono', monospace",
          color: '#858585',
        }}
      >
        <span>TRANSECT: 0.0m ({minZ.toFixed(1)}m)</span>
        <span style={{ color: lineColor, fontWeight: 700 }}>
          ALTITUDE: {currentZ.toFixed(1)} m
        </span>
        <span>{totalDistance > 0 ? `${totalDistance.toFixed(1)}m` : '—'} ({maxZ.toFixed(1)}m)</span>
      </div>

      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ overflow: 'visible', background: '#161616', border: '1px solid #333333' }}
      >
        {/* Hairline Grid Horizon Lines (Zero gradients) */}
        <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="#222222" strokeWidth="1" strokeDasharray="4 2" />
        <line x1="0" y1={height - padY} x2={width} y2={height - padY} stroke="#333333" strokeWidth="1" />

        {/* Hazard & Caution Columns (Solid Flat Colors, No Gradient) */}
        {points.map((p, idx) => {
          if (!p.isCaution && !p.isHazard) return null;
          const colW = Math.max(2, plotW / samples.length);
          return (
            <rect
              key={idx}
              x={p.x - colW / 2}
              y={padY}
              width={colW}
              height={plotH}
              fill={p.isHazard ? '#DC2626' : '#D97706'}
              opacity="0.3"
            />
          );
        })}

        {/* Solid Transect Profile Line (Zero glow, pure 1.5px stroke) */}
        <path d={pathD} fill="none" stroke={lineColor} strokeWidth="1.5" />

        {/* Current Rover Marker on Transect: Solid Square Reticle */}
        <line x1={roverX} y1={0} x2={roverX} y2={height} stroke="#D4D4D4" strokeWidth="1" strokeDasharray="2 2" />
        <rect x={roverX - 3} y={roverY - 3} width="6" height="6" fill="#D4D4D4" stroke="#121212" strokeWidth="1" />
      </svg>
    </div>
  );
}
