import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { Compass, Crosshair, AlertTriangle } from 'lucide-react';

const Plot = createPlotlyComponent(Plotly);

export default function NavigationMap({
  terrain,
  routeComparison,
  roverPos,
  activeTarget,
  allTargets = [],
  onCellClick,
  simulationStep = null,
}) {
  const plotData = useMemo(() => {
    if (!terrain || !terrain.cost_map_display) return [];

    const traces = [];
    const rows = terrain.dimensions[0];
    const cols = terrain.dimensions[1];

    // 1. Terrain Cost Heatmap
    // Plotly Heatmap: z[row][col], x=cols, y=rows
    // Convert null hazards to a visually distinct value for the colorscale
    const zData = terrain.cost_map_display.map((row, r) =>
      row.map((val, c) => {
        if (terrain.hazard_mask && terrain.hazard_mask[r][c]) {
          return 35.0; // Render hazards with distinct hazard cap
        }
        return val !== null ? val : 35.0;
      })
    );

    traces.push({
      z: zData,
      type: 'heatmap',
      colorscale: [
        [0.0, '#090e17'],       // 1.0 Nominal flat regolith (Dark space navy)
        [0.08, '#14273e'],      // 1.5 Mild grade
        [0.2, '#9c5a1a'],       // 5.0 Caution slope (Mars amber/rust)
        [0.5, '#e65100'],       // 15.0 High slope caution
        [0.85, '#bf360c'],      // 25.0 Severe rock field
        [1.0, '#ff1744'],       // 35.0 Impassable Hazard (Crimson/Red)
      ],
      zmin: 1.0,
      zmax: 35.0,
      colorbar: {
        title: { text: 'Cost Scale', font: { color: '#94a3b8', size: 10 } },
        tickvals: [1.0, 5.0, 15.0, 35.0],
        ticktext: ['1.0 Safe', '5.0 Caution', '15.0 Risk', 'Hazard (inf)'],
        tickfont: { color: '#94a3b8', size: 9 },
        len: 0.85,
        thickness: 12,
      },
      hoverinfo: 'x+y+z',
      hovertemplate: 'Col: %{x}<br>Row: %{y}<br>Terrain Cost: %{z:.1f}<extra></extra>',
      name: 'Terrain Cost',
    });

    // 2. Shortest Route Trace (Red / dashed)
    if (
      routeComparison?.shortest?.route?.success &&
      routeComparison.shortest.route.x?.length > 0
    ) {
      traces.push({
        x: routeComparison.shortest.route.x,
        y: routeComparison.shortest.route.y,
        mode: 'lines',
        line: {
          color: '#ff1744',
          width: 3,
          dash: 'dashdot',
        },
        name: 'Shortest Route (Min Distance)',
        hoverinfo: 'name',
      });
    }

    // 3. Safest Route Trace (Cyan / solid)
    if (
      routeComparison?.safest?.route?.success &&
      routeComparison.safest.route.x?.length > 0
    ) {
      traces.push({
        x: routeComparison.safest.route.x,
        y: routeComparison.safest.route.y,
        mode: 'lines+markers',
        line: {
          color: '#00f0ff',
          width: 3.5,
        },
        marker: {
          size: 4,
          color: '#00f0ff',
        },
        name: 'Safest Route (Risk-Weighted)',
        hoverinfo: 'name',
      });
    }

    // 4. Science Targets Markers
    if (allTargets.length > 0) {
      const tgtX = allTargets.map((t) => t.location[1]);
      const tgtY = allTargets.map((t) => t.location[0]);
      const tgtColors = allTargets.map((t) =>
        t.operational_priority > 0 ? '#ffb300' : '#ff1744'
      );
      const tgtHover = allTargets.map(
        (t) =>
          `<b>${t.name}</b> (${t.id})<br>` +
          `Priority: ${t.operational_priority}/100<br>` +
          `Sci Value: ${t.scientific_value}/100<br>` +
          `Status: ${t.accessibility_status}`
      );

      traces.push({
        x: tgtX,
        y: tgtY,
        mode: 'markers+text',
        text: allTargets.map((t) => t.id),
        textposition: 'top center',
        textfont: { family: 'JetBrains Mono', size: 10, color: '#f0f4f8' },
        marker: {
          symbol: 'diamond',
          size: 11,
          color: tgtColors,
          line: { color: '#ffffff', width: 1.5 },
        },
        name: 'Science Targets',
        hoverinfo: 'text',
        hovertext: tgtHover,
      });
    }

    // 5. Rover Current Position or Simulation Playback Step
    const activeRoverPos =
      simulationStep !== null && routeComparison?.safest?.route?.path?.[simulationStep]
        ? routeComparison.safest.route.path[simulationStep]
        : roverPos || [2, 2];

    traces.push({
      x: [activeRoverPos[1]],
      y: [activeRoverPos[0]],
      mode: 'markers',
      marker: {
        symbol: 'cross-dot',
        size: 16,
        color: '#00e676',
        line: { color: '#ffffff', width: 2 },
      },
      name: 'MARS-09 Rover',
      hoverinfo: 'text',
      hovertext: `Rover Chassis at [${activeRoverPos[0]}, ${activeRoverPos[1]}]`,
    });

    return traces;
  }, [terrain, routeComparison, roverPos, activeTarget, allTargets, simulationStep]);

  const layout = useMemo(() => {
    return {
      autosize: true,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { l: 40, r: 20, t: 20, b: 40 },
      xaxis: {
        title: { text: 'Column / Easting (meters)', font: { color: '#64748b', size: 11 } },
        tickfont: { color: '#94a3b8', size: 10, family: 'JetBrains Mono' },
        gridcolor: 'rgba(255, 255, 255, 0.05)',
        zeroline: false,
        range: [-0.5, terrain?.dimensions?.[1] ? terrain.dimensions[1] - 0.5 : 49.5],
      },
      yaxis: {
        title: { text: 'Row / Northing (meters)', font: { color: '#64748b', size: 11 } },
        tickfont: { color: '#94a3b8', size: 10, family: 'JetBrains Mono' },
        gridcolor: 'rgba(255, 255, 255, 0.05)',
        zeroline: false,
        autorange: 'reversed', // Row 0 at top, matching matrix layout
        range: [-0.5, terrain?.dimensions?.[0] ? terrain.dimensions[0] - 0.5 : 49.5],
      },
      legend: {
        orientation: 'h',
        x: 0,
        y: 1.12,
        font: { color: '#cbd5e1', size: 10, family: 'JetBrains Mono' },
      },
      hovermode: 'closest',
    };
  }, [terrain]);

  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Crosshair size={18} />
          Tactical Navigation Canvas (8-Way A* Dual Planner)
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem' }}>
          <span style={{ color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            ● Safest Route
          </span>
          <span style={{ color: '#ff1744', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            ╌╌ Shortest Route
          </span>
        </div>
      </div>

      <div className="nav-canvas-container">
        <Plot
          data={plotData}
          layout={layout}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
          }}
          onClick={(data) => {
            if (data.points && data.points.length > 0 && onCellClick) {
              const pt = data.points[0];
              const r = Math.round(pt.y);
              const c = Math.round(pt.x);
              onCellClick(r, c);
            }
          }}
        />
      </div>
    </div>
  );
}
