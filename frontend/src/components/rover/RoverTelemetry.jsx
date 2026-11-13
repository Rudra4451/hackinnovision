import React from 'react';
import StatusChip from '../shared/StatusChip';
import { getCostClassification } from '../../utils/terrainHelpers';

export default function RoverTelemetry({
  currentPos,
  currentElevation,
  currentIndex,
  pathLength,
  totalDistance,
  cellCost,
  status,
}) {
  const formattedPos = currentPos ? `(${currentPos[0]}, ${currentPos[1]})` : '—';
  const formattedElevation =
    currentElevation !== null && currentElevation !== undefined
      ? `${currentElevation.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} m`
      : '—';

  const formattedDistance =
    typeof totalDistance === 'number'
      ? `${totalDistance.toFixed(1)} m`
      : '—';

  const progressStr = pathLength > 0 ? `${currentIndex + 1} / ${pathLength}` : '—';
  const progressPercent = pathLength > 0 ? Math.round(((currentIndex + 1) / pathLength) * 100) : 0;

  const costInfo = cellCost !== null && cellCost !== undefined ? getCostClassification(cellCost) : null;

  return (
    <div className="telemetry-card">
      <div className="section-header">
        <span>Rover Telemetry</span>
        <StatusChip status={status} />
      </div>

      <div className="kpi-grid">
        <div className="kpi-cell">
          <span className="unit-label">COORDINATES</span>
          <span className="mono" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--rover)' }}>
            {formattedPos}
          </span>
        </div>

        <div className="kpi-cell">
          <span className="unit-label">ELEVATION</span>
          <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
            {formattedElevation}
          </span>
        </div>

        <div className="kpi-cell">
          <span className="unit-label">TRAVERSE DISTANCE</span>
          <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
            {formattedDistance}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
        <div className="kpi-cell">
          <span className="unit-label">WAYPOINT PROGRESS</span>
          <span className="mono" style={{ fontSize: '12px' }}>
            {progressStr} · {progressPercent}%
          </span>
        </div>

        <div className="kpi-cell">
          <span className="unit-label">LOCAL CELL COST</span>
          <span className="mono" style={{ fontSize: '12px', color: costInfo?.color || 'var(--text-primary)' }}>
            {costInfo ? costInfo.label : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
