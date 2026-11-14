import React, { useRef, useEffect, useCallback } from 'react';

/**
 * A.R.E.S. 2D Tactical Radar Minimap Component
 * Utilitarian Aerospace Brutalist Radar:
 * 200x200 Martian DEM elevation relief with #0284C7 nominal route and #DC2626 direct route,
 * square geometric beacons, crosshair grid, and zero curves.
 */
export default function RadarMinimap({
  dem,
  costMap,
  navigation,
  roverCoord,
  roverHeading = 0,
  startPoint,
  destinationPoint,
  cameraPos,
  cameraTarget,
  onFocusLocation,
  width = 180,
  height = 180,
}) {
  const canvasRef = useRef(null);
  const baseCanvasRef = useRef(null);
  const demSignatureRef = useRef('');

  const rows = dem?.rows || 200;
  const cols = dem?.cols || 200;

  // 1. Generate static background texture when DEM or costMap changes
  useEffect(() => {
    if (!dem?.elevation || !dem.elevation.length) return;

    const signature = `${rows}x${cols}_${dem.elevation[0]?.[0]}_${costMap?.cost?.[0]?.[0]}`;
    if (demSignatureRef.current === signature && baseCanvasRef.current) return;
    demSignatureRef.current = signature;

    const offscreen = document.createElement('canvas');
    offscreen.width = cols;
    offscreen.height = rows;
    const ctx = offscreen.getContext('2d');
    const imgData = ctx.createImageData(cols, rows);
    const data = imgData.data;

    let minElev = Infinity;
    let maxElev = -Infinity;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const e = dem.elevation[r]?.[c] ?? 0;
        if (e < minElev) minElev = e;
        if (e > maxElev) maxElev = e;
      }
    }
    const elevRange = Math.max(1, maxElev - minElev);

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = (r * cols + c) * 4;
        const e = dem.elevation[r]?.[c] ?? minElev;
        const normE = (e - minElev) / elevRange;

        const cellCost = costMap?.cost?.[r]?.[c];
        const isHazard = cellCost === Infinity || cellCost === 'Infinity' || cellCost >= 9999;
        const isCaution = typeof cellCost === 'number' && cellCost > 2.0 && !isHazard;

        if (isHazard) {
          // Flat Crimson (#DC2626) Hazard
          data[idx + 0] = 220;
          data[idx + 1] = 38;
          data[idx + 2] = 38;
          data[idx + 3] = 255;
        } else if (isCaution) {
          // Flat Amber (#D97706) Caution Zone
          data[idx + 0] = 217;
          data[idx + 1] = 119;
          data[idx + 2] = 6;
          data[idx + 3] = 200;
        } else {
          // Monochrome Matte Topography (#181818 to #383838)
          const shade = Math.floor(20 + normE * 40);
          data[idx + 0] = shade;
          data[idx + 1] = shade;
          data[idx + 2] = shade;
          data[idx + 3] = 255;
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);
    baseCanvasRef.current = offscreen;
  }, [dem, costMap, rows, cols]);

  // 2. Render dynamic radar overlays (Routes, Rover, Beacons, Frustum)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    // Draw base terrain image
    if (baseCanvasRef.current) {
      ctx.drawImage(baseCanvasRef.current, 0, 0, cols, rows, 0, 0, width, height);
    } else {
      ctx.fillStyle = '#121212';
      ctx.fillRect(0, 0, width, height);
    }

    // Grid Scale Helper
    const scaleX = width / cols;
    const scaleY = height / rows;

    // Helper to draw route line
    const drawRoute = (path, color, lineWidth = 2, dashed = false) => {
      if (!Array.isArray(path) || path.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      if (dashed) ctx.setLineDash([3, 3]);
      else ctx.setLineDash([]);

      for (let i = 0; i < path.length; i++) {
        const [r, c] = path[i];
        const px = c * scaleX;
        const py = r * scaleY;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    };

    // Draw Shortest Route (Crimson #DC2626)
    const shortestPath = navigation?.shortest?.route?.path;
    if (shortestPath) {
      drawRoute(shortestPath, '#DC2626', 1.5, true);
    }

    // Draw Safest Route (Sky Blue #0284C7)
    const safestPath = navigation?.safest?.route?.path;
    if (safestPath) {
      drawRoute(safestPath, '#0284C7', 2.0);
    }

    // Draw Start Beacon (Sky Blue Square)
    if (startPoint) {
      const sx = startPoint[1] * scaleX;
      const sy = startPoint[0] * scaleY;
      ctx.fillStyle = '#0284C7';
      ctx.fillRect(sx - 3, sy - 3, 6, 6);
      ctx.strokeStyle = '#D4D4D4';
      ctx.lineWidth = 1;
      ctx.strokeRect(sx - 3, sy - 3, 6, 6);
    }

    // Draw Destination Beacon (Flat Amber Square)
    if (destinationPoint) {
      const dx = destinationPoint[1] * scaleX;
      const dy = destinationPoint[0] * scaleY;
      ctx.fillStyle = '#D97706';
      ctx.fillRect(dx - 3, dy - 3, 6, 6);
      ctx.strokeStyle = '#D4D4D4';
      ctx.lineWidth = 1;
      ctx.strokeRect(dx - 3, dy - 3, 6, 6);
    }

    // Draw Rover Position & Heading Arrow
    if (roverCoord) {
      const rx = roverCoord[1] * scaleX;
      const ry = roverCoord[0] * scaleY;

      // Rover square reticle
      ctx.fillStyle = '#D4D4D4';
      ctx.fillRect(rx - 3, ry - 3, 6, 6);
      ctx.strokeStyle = '#0284C7';
      ctx.lineWidth = 1;
      ctx.strokeRect(rx - 4, ry - 4, 8, 8);

      // Heading indicator needle
      const headingLen = 10;
      const nx = rx + Math.sin(roverHeading) * headingLen;
      const ny = ry + Math.cos(roverHeading) * headingLen;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(nx, ny);
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw Tactical Camera Target Crosshair
    if (cameraTarget) {
      const targetCol = cameraTarget.x + (cols - 1) / 2;
      const targetRow = cameraTarget.z + (rows - 1) / 2;
      const tx = targetCol * scaleX;
      const ty = targetRow * scaleY;

      ctx.strokeStyle = '#D4D4D4';
      ctx.lineWidth = 1;
      ctx.strokeRect(tx - 3, ty - 3, 6, 6);
    }

    // Radar Hairline Crosshair
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
  }, [
    dem,
    costMap,
    navigation,
    roverCoord,
    roverHeading,
    startPoint,
    destinationPoint,
    cameraPos,
    cameraTarget,
    cols,
    rows,
    width,
    height,
  ]);

  const handleCanvasClick = useCallback(
    (e) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const clickCol = Math.max(0, Math.min(cols - 1, Math.round((clickX / width) * cols)));
      const clickRow = Math.max(0, Math.min(rows - 1, Math.round((clickY / height) * rows)));

      onFocusLocation(clickRow, clickCol);
    },
    [cols, rows, width, height, onFocusLocation]
  );

  return (
    <div
      style={{
        position: 'relative',
        width: `${width}px`,
        height: `${height}px`,
        background: '#121212',
        border: '1px solid #333333',
        cursor: 'crosshair',
      }}
      title="A.R.E.S. Radar 2D — Click to Pan Camera"
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onClick={handleCanvasClick}
        style={{ display: 'block' }}
      />
      {/* Brutalist Monospace Labels */}
      <div
        style={{
          position: 'absolute',
          top: '2px',
          left: '4px',
          fontSize: '8px',
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 700,
          color: '#858585',
          letterSpacing: '0.08em',
          pointerEvents: 'none',
        }}
      >
        RADAR // {cols}×{rows}
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: '2px',
          right: '4px',
          fontSize: '7px',
          fontFamily: "'JetBrains Mono', monospace",
          color: '#858585',
          pointerEvents: 'none',
        }}
      >
        [ TARGET LOCK ]
      </div>
    </div>
  );
}
