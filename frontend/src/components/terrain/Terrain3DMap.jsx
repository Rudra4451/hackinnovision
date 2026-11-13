import React, { useMemo, useRef, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';

import { routeToTrace, elevationAt } from '../../utils/coordinateMapping';
import { buildHazardTraces } from './HazardOverlay';
import { buildRoverMarkerTrace } from './RoverMarker';

const Plot = createPlotlyComponent(Plotly);

/**
 * Martian Geological Colorscale (§3.2).
 * Non-rainbow, scientifically restrained representation of surface minerals.
 */
const MARS_COLORSCALE = [
  [0.00, '#2D140D'],  // dark basalt
  [0.35, '#8C3B2B'],  // Martian rust
  [0.70, '#D97757'],  // dusty orange
  [1.00, '#E7B18A'],  // pale mineral surface
];

export default function Terrain3DMap({
  dem,
  costMap,
  navigation,
  roverPos,
  simulationIndex = 0,
  overlays = { route: true, hazards: true, caution: true, rover: true, contours: true },
  displayScale = 1.0,
  onHoverCell = null,
  onClickCell = null,
  onOutOfBounds = null,
}) {
  const hoverTimeoutRef = useRef(null);

  // 1. Memoized 3D Terrain Surface Trace (§3.2, §9)
  // Keyed strictly on dem and displayScale — will not recalculate on rover ticks!
  const surfaceTrace = useMemo(() => {
    if (!dem || !dem.elevation || !Array.isArray(dem.elevation)) return null;

    const rows = dem.rows;
    const cols = dem.cols;
    const elevation = dem.elevation;

    // Apply display scale factor to Z coordinates for visual relief exaggeration
    const scaledZ = elevation.map((row) => row.map((z) => (z !== null ? z * displayScale : null)));

    return {
      type: 'surface',
      z: scaledZ,
      x: Array.from({ length: cols }, (_, c) => c),
      y: Array.from({ length: rows }, (_, r) => r),
      colorscale: MARS_COLORSCALE,
      showscale: true,
      colorbar: {
        title: {
          text: `Elevation (${dem.elevationUnit || 'm'})`,
          font: { color: '#E2E8F0', size: 11, family: 'JetBrains Mono' },
          side: 'bottom',
        },
        orientation: 'h',
        x: 0.5,
        y: -0.08,
        xanchor: 'center',
        len: 0.55,
        thickness: 12,
        tickfont: { color: '#94A3B8', size: 10, family: 'JetBrains Mono' },
      },
      contours: {
        z: {
          show: overlays.contours,
          usecolormap: false,
          color: 'rgba(226, 177, 138, 0.18)',
          width: 1,
        },
      },
      lighting: {
        ambient: 0.65,
        diffuse: 0.8,
        specular: 0.05,
        roughness: 0.85,
        fresnel: 0.1,
      },
      hoverinfo: 'none', // Handled custom by onHover to preserve high performance
    };
  }, [dem, displayScale, overlays.contours]);

  // 2. Trajectory Traces (Safest Path Split: Completed vs Remaining) (§3.3, §4.4)
  const routeTraces = useMemo(() => {
    if (!overlays.route || !navigation?.safest?.route?.success) return [];
    const fullPath = navigation.safest.route.path || [];
    if (fullPath.length === 0 || !dem?.elevation) return [];

    const traces = [];
    const splitIndex = Math.min(simulationIndex, fullPath.length - 1);

    // Completed Path (Solid #10B981, width 5)
    if (splitIndex > 0) {
      const completedPath = fullPath.slice(0, splitIndex + 1);
      const { x, y, z, outOfBounds } = routeToTrace(completedPath, dem.elevation, 2.0, displayScale);
      if (outOfBounds.length > 0 && onOutOfBounds) onOutOfBounds(outOfBounds);

      traces.push({
        type: 'scatter3d',
        mode: 'lines',
        name: 'Completed Traverse',
        x,
        y,
        z,
        line: {
          color: '#10B981',
          width: 5,
          shape: 'linear',
        },
        hoverinfo: 'name',
      });
    }

    // Remaining Path (Dotted #10B981, width 3, opacity 0.35)
    if (splitIndex < fullPath.length - 1) {
      const remainingPath = fullPath.slice(splitIndex);
      const { x, y, z } = routeToTrace(remainingPath, dem.elevation, 2.0, displayScale);

      traces.push({
        type: 'scatter3d',
        mode: 'lines',
        name: 'Planned Trajectory',
        x,
        y,
        z,
        line: {
          color: '#10B981',
          width: 3,
          dash: 'dot',
        },
        opacity: 0.45,
        hoverinfo: 'name',
      });
    }

    return traces;
  }, [overlays.route, navigation, dem, simulationIndex, displayScale, onOutOfBounds]);

  // 3. Hazard & Caution Traces (§3.4)
  const hazardTraces = useMemo(() => {
    if (!costMap?.cost || !dem?.elevation) return [];
    return buildHazardTraces(costMap.cost, dem.elevation, {
      showHazards: overlays.hazards,
      showCaution: overlays.caution,
      verticalOffset: 1.2,
      displayScale,
    });
  }, [costMap, dem, overlays.hazards, overlays.caution, displayScale]);

  // 4. Rover Marker Trace (§3.5)
  const roverTrace = useMemo(() => {
    if (!overlays.rover || !roverPos || !dem?.elevation) return null;
    return buildRoverMarkerTrace(roverPos, dem.elevation, {
      roverOffset: 3.0,
      displayScale,
      onOutOfBounds,
    });
  }, [overlays.rover, roverPos, dem, displayScale, onOutOfBounds]);

  // Combine active traces for rendering
  const allTraces = useMemo(() => {
    const combined = [];
    if (surfaceTrace) combined.push(surfaceTrace);
    if (hazardTraces.length > 0) combined.push(...hazardTraces);
    if (routeTraces.length > 0) combined.push(...routeTraces);
    if (roverTrace) combined.push(roverTrace);
    return combined;
  }, [surfaceTrace, hazardTraces, routeTraces, roverTrace]);

  // 3D Layout & Camera Config (§3.2)
  const layout = useMemo(() => {
    const rows = dem?.rows || 50;
    const cols = dem?.cols || 50;

    return {
      autosize: true,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      margin: { l: 0, r: 0, t: 0, b: 0 },
      scene: {
        xaxis: {
          title: { text: 'Column', font: { color: '#94A3B8', size: 11, family: 'Inter' } },
          tickfont: { color: '#64748B', size: 9, family: 'JetBrains Mono' },
          gridcolor: '#1E293B',
          zeroline: false,
          range: [0, cols - 1],
        },
        yaxis: {
          title: { text: 'Row', font: { color: '#94A3B8', size: 11, family: 'Inter' } },
          tickfont: { color: '#64748B', size: 9, family: 'JetBrains Mono' },
          gridcolor: '#1E293B',
          zeroline: false,
          range: [0, rows - 1],
        },
        zaxis: {
          title: { text: 'Elevation (m)', font: { color: '#94A3B8', size: 11, family: 'Inter' } },
          tickfont: { color: '#64748B', size: 9, family: 'JetBrains Mono' },
          gridcolor: '#1E293B',
          zeroline: false,
        },
        aspectmode: 'data', // Preserves realistic proportions without stretching (§3.2)
        camera: {
          eye: { x: 1.6, y: -1.6, z: 1.1 }, // Standard NASA/JPL 45° perspective
        },
      },
      legend: {
        orientation: 'h',
        x: 0.02,
        y: 0.96,
        font: { color: '#E2E8F0', size: 10, family: 'JetBrains Mono' },
        bgcolor: 'rgba(14, 21, 34, 0.85)',
        bordercolor: '#1E293B',
        borderwidth: 1,
      },
    };
  }, [dem]);

  // Debounced hover handler at 60ms (§9)
  const handlePlotHover = useCallback(
    (eventData) => {
      if (!onHoverCell || !eventData.points || eventData.points.length === 0) return;
      const pt = eventData.points[0];
      const col = Math.round(pt.x);
      const row = Math.round(pt.y);

      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = setTimeout(() => {
        const rawZ = dem?.elevation ? elevationAt(dem.elevation, row, col) : null;
        const cellCost = costMap?.cost?.[row]?.[col] ?? 1.0;
        onHoverCell({ row, col, elevation: rawZ, cost: cellCost });
      }, 60);
    },
    [onHoverCell, dem, costMap]
  );

  const handlePlotClick = useCallback(
    (eventData) => {
      if (!onClickCell || !eventData.points || eventData.points.length === 0) return;
      const pt = eventData.points[0];
      const col = Math.round(pt.x);
      const row = Math.round(pt.y);
      const rawZ = dem?.elevation ? elevationAt(dem.elevation, row, col) : null;
      const cellCost = costMap?.cost?.[row]?.[col] ?? 1.0;
      onClickCell({ row, col, elevation: rawZ, cost: cellCost });
    },
    [onClickCell, dem, costMap]
  );

  return (
    <div className="mc-plotly-wrapper">
      <Plot
        data={allTraces}
        layout={layout}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: [
            'lasso2d',
            'select2d',
            'hoverClosest3d',
            'hoverClosestCartesian',
            'hoverCompareCartesian',
          ],
        }}
        onHover={handlePlotHover}
        onClick={handlePlotClick}
      />
    </div>
  );
}
