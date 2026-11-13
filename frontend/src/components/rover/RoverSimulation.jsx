import React from 'react';
import { AlertTriangle } from 'lucide-react';
import SimulationControls from './SimulationControls';
import RoverTelemetry from './RoverTelemetry';
import { elevationAt } from '../../utils/coordinateMapping';

export default function RoverSimulation({
  simState,
  routePath = [],
  elevation = null,
  costMap = null,
  safestMetrics = null,
  routeSuccess = true,
}) {
  const {
    currentIndex,
    currentCoordinate,
    status,
    speed,
    progressPct,
    maxIndex,
    start,
    pause,
    stepForward,
    stepBackward,
    reset,
    seekTo,
    setSpeed,
  } = simState;

  if (!routeSuccess || routePath.length === 0) {
    return (
      <div className="telemetry-card" style={{ borderColor: 'var(--hazard)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--hazard)', fontWeight: 600 }}>
          <AlertTriangle size={16} />
          <span>Simulation Unavailable</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
          No verified safe trajectory exists. Simulation controls remain locked to safeguard the vehicle.
        </p>
      </div>
    );
  }

  const [row, col] = currentCoordinate || routePath[0] || [0, 0];
  const currentZ = elevation ? elevationAt(elevation, row, col) : null;
  const currentCost = costMap?.cost?.[row]?.[col] ?? null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <RoverTelemetry
        currentPos={[row, col]}
        currentElevation={currentZ}
        currentIndex={currentIndex}
        pathLength={routePath.length}
        totalDistance={safestMetrics?.total_distance ?? null}
        cellCost={currentCost}
        status={status}
      />

      <SimulationControls
        status={status}
        currentIndex={currentIndex}
        maxIndex={maxIndex}
        speed={speed}
        progressPct={progressPct}
        onStart={start}
        onPause={pause}
        onStepForward={stepForward}
        onStepBackward={stepBackward}
        onReset={reset}
        onSeek={seekTo}
        onChangeSpeed={setSpeed}
      />
    </div>
  );
}
