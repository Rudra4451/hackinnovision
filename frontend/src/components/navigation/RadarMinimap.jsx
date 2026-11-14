import React, { useRef, useEffect, useCallback } from 'react';

/**
 * 2D Tactical Radar Minimap Component
 * Renders 200x200 Martian DEM elevation relief, color-coded hazard zones,
 * green/red route overlays, live rover position with heading reticle,
 * and camera frustum cone.
 * Clicking anywhere on the minimap pans camera target to that 3D location.
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
}) {
  const canvasRef = useRef(null);

  // Pre-render elevation & hazard base layer to an offscreen canvas for 60+ FPS efficiency
  const baseCanvasRef = useRef(null);
  const demSignatureRef = useRef('');

  const rows = dem?.rows || 200;
  const cols = dem?.cols || 200;
  const width = 190;
  const height = 190;

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
          // Bright Red/Magma Hazard
          data[idx + 0] = 239;
          data[idx + 1] = 68;
          data[idx + 2] = 68;
          data[idx + 3] = 240;
        } else if (isCaution) {
          // Amber Caution Zone (Sand trap / high slip)
          data[idx + 0] = 217;
          data[idx + 1] = 119;
          data[idx + 2] = 6;
          data[idx + 3] = 180;
        } else {
          // Martian Basalt to Rust elevation gradient
          const red = Math.floor(25 + normE * 125);
          const green = Math.floor(15 + normE * 60);
          const blue = Math.floor(18 + normE * 45);
          data[idx + 0] = red;
          data[idx + 1] = green;
          data[idx + 2] = blue;
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
      ctx.fillStyle = '#0a0e17';
      ctx.fillRect(0, 0, width, height);
    }

    // Grid Scale Helper
    const scaleX = width / cols;
    const scaleY = height / rows;

    // Helper to draw route line
    const drawRoute = (path, color, lineWidth = 1.5, dashed = false) => {
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

    // Draw Shortest Route (Red)
    const shortestPath = navigation?.shortest?.route?.path;
    if (shortestPath) {
      drawRoute(shortestPath, 'rgba(239, 68, 68, 0.75)', 1.5, true);
    }

    // Draw Safest Route (Green)
    const safestPath = navigation?.safest?.route?.path;
    if (safestPath) {
      drawRoute(safestPath, 'rgba(16, 185, 129, 0.95)', 2.0);
    }

    // Draw Start Beacon (Cyan dot)
    if (startPoint) {
      const sx = startPoint[1] * scaleX;
      const sy = startPoint[0] * scaleY;
      ctx.beginPath();
      ctx.arc(sx, sy, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#06b6d4';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw Destination Beacon (Amber dot)
    if (destinationPoint) {
      const dx = destinationPoint[1] * scaleX;
      const dy = destinationPoint[0] * scaleY;
      ctx.beginPath();
      ctx.arc(dx, dy, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#f59e0b';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw Rover Position & Heading Arrow
    if (roverCoord) {
      const rx = roverCoord[1] * scaleX;
      const ry = roverCoord[0] * scaleY;

      // Outer radar pulse circle
      ctx.beginPath();
      ctx.arc(rx, ry, 5.5, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(6, 182, 212, 0.35)';
      ctx.fill();
      ctx.strokeStyle = '#22d3ee';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Heading indicator needle
      const headingLen = 9;
      const nx = rx + Math.sin(roverHeading) * headingLen;
      const ny = ry + Math.cos(roverHeading) * headingLen;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(nx, ny);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw Tactical Camera Frustum / Center Target
    if (cameraTarget) {
      // Convert world target (x, z) to grid (row, col)
      const targetCol = cameraTarget.x + (cols - 1) / 2;
      const targetRow = cameraTarget.z + (rows - 1) / 2;
      const tx = targetCol * scaleX;
      const ty = targetRow * scaleY;

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.55)';
      ctx.lineWidth = 1;
      ctx.strokeRect(tx - 3, ty - 3, 6, 6);

      if (cameraPos) {
        const camCol = cameraPos.x + (cols - 1) / 2;
        const camRow = cameraPos.z + (rows - 1) / 2;
        const cx = camCol * scaleX;
        const cy = camRow * scaleY;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(tx - 5, ty);
        ctx.lineTo(tx + 5, ty);
        ctx.closePath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.stroke();
      }
    }

    // Draw Radar Sweep Reticle & Grid Crosshair
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width / 2, height);
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    // Radar distance concentric rings
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, width * 0.25, 0, Math.PI * 2);
    ctx.arc(width / 2, height / 2, width * 0.45, 0, Math.PI * 2);
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
    rows,
    cols,
    width,
    height,
  ]);

  // Click on minimap to focus 3D camera
  const handleCanvasClick = useCallback(
    (e) => {
      const canvas = canvasRef.current;
      if (!canvas || !onFocusLocation) return;
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
      className="tactical-panel"
      style={{
        position: 'relative',
        width: `${width}px`,
        height: `${height}px`,
        overflow: 'hidden',
        border: '1px solid rgba(255, 255, 255, 0.16)',
        boxShadow: '0 4px 18px rgba(0, 0, 0, 0.75)',
        cursor: 'crosshair',
      }}
      title="Tactical 2D Radar Minimap — Click to Focus Camera"
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onClick={handleCanvasClick}
        style={{ display: 'block' }}
      />
      {/* Corner Overlay Labels */}
      <div
        style={{
          position: 'absolute',
          top: '3px',
          left: '5px',
          fontSize: '8px',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          color: 'var(--rover)',
          letterSpacing: '0.08em',
          pointerEvents: 'none',
          textShadow: '0 1px 3px rgba(0,0,0,0.9)',
        }}
      >
        RADAR 2D // {cols}×{rows}
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: '3px',
          right: '5px',
          fontSize: '7px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          pointerEvents: 'none',
          textShadow: '0 1px 3px rgba(0,0,0,0.9)',
        }}
      >
        CLICK TO TARGET
      </div>
    </div>
  );
}
