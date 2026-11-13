import React from 'react';
import { Mountain, Compass, MapPin } from 'lucide-react';

export default function TerrainExplorer({
  inspectedCell,
  terrain,
  onSetAsGoal,
}) {
  if (!inspectedCell) {
    return (
      <div className="hud-panel">
        <div className="hud-panel-title">
          <Mountain size={18} />
          Terrain Morphology & Topography Inspector
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.8rem' }}>
          Click any cell on the Tactical Navigation Canvas to inspect elevation, surface slope, and traversability cost.
        </div>
      </div>
    );
  }

  const { row, col } = inspectedCell;
  const isHazard = terrain?.hazard_mask?.[row]?.[col] ?? false;
  const cost = terrain?.cost_map_display?.[row]?.[col] ?? (isHazard ? null : 1.0);
  const elevation = terrain?.elevation_map?.[row]?.[col]?.toFixed(1) ?? '30.0';

  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Mountain size={18} />
          Cell Inspection [{row}, {col}]
        </div>
        <div>
          {isHazard ? (
            <span className="badge badge-gated">IMPASSABLE HAZARD</span>
          ) : cost > 2.0 ? (
            <span className="badge badge-caution">CAUTION TERRAIN</span>
          ) : (
            <span className="badge badge-optimal">NOMINAL FLAT REGOLITH</span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
        <div className="tradeoff-stat-box">
          <div className="stat-val mono" style={{ color: '#00f0ff' }}>
            {elevation} m
          </div>
          <div className="stat-label">Elevation</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val mono" style={{ color: isHazard ? '#ff1744' : cost > 2.0 ? '#ffb300' : '#00e676' }}>
            {isHazard ? '∞ (HAZARD)' : `${cost?.toFixed(1)}x`}
          </div>
          <div className="stat-label">Terrain Cost</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val mono" style={{ color: '#f0f4f8' }}>
            1.0 m²
          </div>
          <div className="stat-label">Cell Res</div>
        </div>
      </div>

      <button
        className="btn-tactical btn-cyan"
        style={{ width: '100%' }}
        onClick={() => onSetAsGoal([row, col])}
        disabled={isHazard}
      >
        <MapPin size={16} />
        {isHazard ? 'CANNOT NAVIGATE TO HAZARD' : `PLAN AUTONOMOUS TRAJECTORY TO [${row}, ${col}]`}
      </button>
    </div>
  );
}
