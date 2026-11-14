import React, { useMemo } from 'react';
import { elevationAt } from '../../utils/coordinateMapping';

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
      <div style={{ height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
        AWAITING ROUTE WAYPOINTS FOR ELEVATION TRANSECT
      </div>
    );
  }

  const { samples, minZ, maxZ, rangeZ } = chartData;
  const width = 480;
  const height = 50;
  const padY = 8;
  const padX = 12;
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

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;

  // Live Rover Position on the chart
  const curIdx = Math.max(0, Math.min(samples.length - 1, roverProgress));
  const k = Math.floor(curIdx);
  const t = curIdx - k;
  const p0 = points[k] || points[0];
  const p1 = points[Math.min(k + 1, points.length - 1)];

  const roverX = p0.x + (p1.x - p0.x) * t;
  const roverY = p0.y + (p1.y - p0.y) * t;
  const currentZ = p0.z + (p1.z - p0.z) * t;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
        <span>TRANSECT: 0 m ({minZ.toFixed(1)} m)</span>
        <span style={{ color: activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)', fontWeight: 600 }}>
          LIVE ALTITUDE: {currentZ.toFixed(1)} m
        </span>
        <span>{totalDistance > 0 ? `${totalDistance.toFixed(1)} m` : '—'} ({maxZ.toFixed(1)} m)</span>
      </div>

      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={activeRoute === 'safest' ? '#10B981' : '#EF4444'} stopOpacity="0.35" />
            <stop offset="100%" stopColor={activeRoute === 'safest' ? '#10B981' : '#EF4444'} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Hazard & Caution background columns */}
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
              fill={p.isHazard ? 'rgba(239, 68, 68, 0.28)' : 'rgba(245, 158, 11, 0.22)'}
            />
          );
        })}

        {/* Shaded Area under Profile */}
        <path d={areaD} fill="url(#areaGradient)" />

        {/* Elevation Transect Line */}
        <path
          d={pathD}
          fill="none"
          stroke={activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)'}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Live Rover Playhead Pin */}
        <line
          x1={roverX}
          y1={padY - 2}
          x2={roverX}
          y2={height}
          stroke="var(--rover)"
          strokeWidth="1.2"
          strokeDasharray="2,2"
        />
        <circle cx={roverX} cy={roverY} r="3.5" fill="var(--rover)" stroke="#fff" strokeWidth="1" />
      </svg>
    </div>
  );
}
