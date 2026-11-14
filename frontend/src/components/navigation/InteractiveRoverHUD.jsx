import React from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Shield,
  Zap,
  MapPin,
  Compass,
  AlertTriangle,
  CheckCircle2,
  Navigation2,
  Layers,
  ChevronRight,
} from 'lucide-react';

export default function InteractiveRoverHUD({
  startPoint,
  destinationPoint,
  onResetPoints,
  onSetSelectionMode,
  selectionMode,
  navigation,
  activeRoute,
  onSelectRoute,
  isPlaying,
  onPlay,
  onPause,
  onResume,
  onResetRover,
  roverProgress,
  roverCoord,
  currentElevation,
  navStatus,
  error,
}) {
  const currentRouteData = navigation?.[activeRoute];
  const routeSuccess = currentRouteData?.route?.success ?? false;
  const failureReason = currentRouteData?.route?.reason || null;
  const path = currentRouteData?.route?.path || [];
  const metrics = currentRouteData?.metrics || {};

  const totalDistance = metrics.total_distance ?? 0;
  const pathLength = path.length;
  const maxIdx = Math.max(1, pathLength - 1);
  const progressPct = Math.min(100, Math.round((roverProgress / maxIdx) * 100));
  const distanceTravelled = (totalDistance * (progressPct / 100)).toFixed(1);

  const safestMetrics = navigation?.safest?.metrics;
  const shortestMetrics = navigation?.shortest?.metrics;

  return (
    <div className="telemetry-card" style={{ gap: '14px' }}>
      {/* 1. Interactive Step-by-Step Guidance Banner */}
      <div
        style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, color: 'var(--rover)', letterSpacing: '0.06em' }}>
            <Compass size={13} />
            <span>OPERATOR DIRECTIVE</span>
          </div>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              padding: '2px 6px',
              borderRadius: '4px',
              background: navStatus === 'NAVIGATING' ? 'rgba(6, 182, 212, 0.2)' : 'var(--bg-elevated)',
              color: navStatus === 'NAVIGATING' ? 'var(--rover)' : 'var(--text-secondary)',
              fontWeight: 600,
            }}
          >
            {navStatus}
          </span>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.4 }}>
          {!startPoint ? (
            <span style={{ color: '#60a5fa' }}>
              • <strong>Step 1:</strong> Click anywhere on the 3D terrain to place the <strong>BLUE START</strong> marker.
            </span>
          ) : !destinationPoint ? (
            <span style={{ color: '#fbbf24' }}>
              • <strong>Step 2:</strong> Click on the terrain to place the <strong>YELLOW DESTINATION</strong> marker.
            </span>
          ) : !routeSuccess ? (
            <span style={{ color: 'var(--hazard)' }}>
              • <strong>Route Blocked:</strong> {failureReason || 'Target cell is inaccessible. Click to choose an alternate destination.'}
            </span>
          ) : (
            <span style={{ color: 'var(--safe)' }}>
              • <strong>Step 3:</strong> Select <strong>GREEN (Safest)</strong> or <strong>RED (Shortest)</strong> route and press <strong>PLAY</strong>.
            </span>
          )}
        </div>
      </div>

      {/* 2. Marker Endpoints & Repositioning Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {/* Blue Start Marker Chip */}
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.08)',
            border: selectionMode === 'start' ? '1px solid #3b82f6' : '1px solid rgba(59, 130, 246, 0.25)',
            borderRadius: '6px',
            padding: '8px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '10px', color: '#60a5fa', fontWeight: 600, letterSpacing: '0.05em' }}>
              START (BLUE)
            </span>
            <button
              className="mc-btn"
              style={{
                padding: '1px 6px',
                fontSize: '10px',
                borderColor: selectionMode === 'start' ? '#3b82f6' : 'var(--border-subtle)',
                color: selectionMode === 'start' ? '#60a5fa' : 'var(--text-secondary)',
              }}
              onClick={() => onSetSelectionMode(selectionMode === 'start' ? 'auto' : 'start')}
            >
              {selectionMode === 'start' ? 'CLICKING...' : 'REPOSITION'}
            </button>
          </div>
          <span className="mono" style={{ fontSize: '12px', fontWeight: 600, color: '#93c5fd' }}>
            {startPoint ? `(${startPoint[0]}, ${startPoint[1]})` : 'NOT SET'}
          </span>
        </div>

        {/* Yellow Destination Marker Chip */}
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: selectionMode === 'destination' ? '1px solid #f59e0b' : '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '6px',
            padding: '8px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '10px', color: '#fbbf24', fontWeight: 600, letterSpacing: '0.05em' }}>
              DESTINATION (YELLOW)
            </span>
            <button
              className="mc-btn"
              style={{
                padding: '1px 6px',
                fontSize: '10px',
                borderColor: selectionMode === 'destination' ? '#f59e0b' : 'var(--border-subtle)',
                color: selectionMode === 'destination' ? '#fbbf24' : 'var(--text-secondary)',
              }}
              onClick={() => onSetSelectionMode(selectionMode === 'destination' ? 'auto' : 'destination')}
            >
              {selectionMode === 'destination' ? 'CLICKING...' : 'REPOSITION'}
            </button>
          </div>
          <span className="mono" style={{ fontSize: '12px', fontWeight: 600, color: '#fde68a' }}>
            {destinationPoint ? `(${destinationPoint[0]}, ${destinationPoint[1]})` : 'NOT SET'}
          </span>
        </div>
      </div>

      {/* Reset Marker Points Button */}
      {(startPoint || destinationPoint) && (
        <button
          className="mc-btn"
          style={{ padding: '4px 10px', fontSize: '11px', alignSelf: 'flex-start' }}
          onClick={onResetPoints}
        >
          <RotateCcw size={12} />
          CLEAR / RESET ENDPOINT PINS
        </button>
      )}

      {/* 3. Authoritative Route Selection: GREEN SAFEST vs RED SHORTEST */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <span className="unit-label">AUTHORITATIVE PYTHON NAVIGATION ROUTES</span>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {/* Green Safest Route Button */}
          <button
            onClick={() => onSelectRoute('safest')}
            disabled={!navigation?.safest?.route?.success}
            style={{
              padding: '8px 10px',
              borderRadius: '6px',
              border: activeRoute === 'safest' ? '2px solid var(--safe)' : '1px solid var(--border-subtle)',
              background: activeRoute === 'safest' ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-base)',
              color: 'var(--text-primary)',
              cursor: navigation?.safest?.route?.success ? 'pointer' : 'not-allowed',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              opacity: navigation?.safest?.route?.success ? 1 : 0.4,
              transition: 'all 150ms ease-out',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--safe)', fontWeight: 600, fontSize: '11px' }}>
              <Shield size={13} />
              <span>GREEN ROUTE (SAFEST)</span>
            </div>
            <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {safestMetrics?.total_distance ? `${safestMetrics.total_distance.toFixed(1)} m` : '—'} · {safestMetrics?.caution_steps ?? 0} caution
            </div>
          </button>

          {/* Red Shortest Route Button */}
          <button
            onClick={() => onSelectRoute('shortest')}
            disabled={!navigation?.shortest?.route?.success}
            style={{
              padding: '8px 10px',
              borderRadius: '6px',
              border: activeRoute === 'shortest' ? '2px solid var(--hazard)' : '1px solid var(--border-subtle)',
              background: activeRoute === 'shortest' ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-base)',
              color: 'var(--text-primary)',
              cursor: navigation?.shortest?.route?.success ? 'pointer' : 'not-allowed',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              opacity: navigation?.shortest?.route?.success ? 1 : 0.4,
              transition: 'all 150ms ease-out',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--hazard)', fontWeight: 600, fontSize: '11px' }}>
              <Zap size={13} />
              <span>RED ROUTE (SHORTEST)</span>
            </div>
            <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {shortestMetrics?.total_distance ? `${shortestMetrics.total_distance.toFixed(1)} m` : '—'} · {shortestMetrics?.caution_steps ?? 0} caution
            </div>
          </button>
        </div>
      </div>

      {/* 4. Live Navigation Telemetry Dashboard Readout */}
      <div
        style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px' }}>
          <span className="section-header" style={{ marginBottom: 0 }}>
            Live Navigation Telemetry
          </span>
          <span
            className="mono"
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)',
            }}
          >
            ACTIVE: {activeRoute.toUpperCase()}
          </span>
        </div>

        {/* Primary KPI Grid */}
        <div className="kpi-grid">
          <div className="kpi-cell">
            <span className="unit-label">CURRENT POSITION</span>
            <span className="mono" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--rover)' }}>
              {roverCoord ? `(${roverCoord[0].toFixed(1)}, ${roverCoord[1].toFixed(1)})` : '—'}
            </span>
            <span className="unit-label">GRID (ROW, COL)</span>
          </div>

          <div className="kpi-cell">
            <span className="unit-label">ELEVATION</span>
            <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
              {currentElevation !== null && currentElevation !== undefined
                ? `${currentElevation.toFixed(1)} m`
                : '—'}
            </span>
            <span className="unit-label">SURFACE Z</span>
          </div>

          <div className="kpi-cell">
            <span className="unit-label">TRAVERSE DISTANCE</span>
            <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
              {distanceTravelled} / {totalDistance > 0 ? `${totalDistance.toFixed(1)} m` : '—'}
            </span>
            <span className="unit-label">METERS</span>
          </div>
        </div>

        {/* Progress Bar & Percentage */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>JOURNEY COMPLETION</span>
            <span style={{ fontWeight: 600, color: progressPct === 100 ? 'var(--safe)' : 'var(--text-primary)' }}>
              {progressPct}%
            </span>
          </div>
          <div className="mc-sim-progress-track">
            <div
              className="mc-sim-progress-fill"
              style={{
                width: `${progressPct}%`,
                background: activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)',
              }}
            />
          </div>
        </div>
      </div>

      {/* 5. Integrated Rover Controls: PLAY, PAUSE, RESUME, RESET */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!isPlaying ? (
            <button
              className="mc-btn mc-btn-primary"
              disabled={!routeSuccess || pathLength === 0}
              onClick={roverProgress > 0 && roverProgress < maxIdx ? onResume : onPlay}
              style={{
                background: routeSuccess ? (activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)') : 'var(--border-subtle)',
                color: '#fff',
                borderColor: 'transparent',
              }}
            >
              <Play size={13} fill="#fff" />
              {roverProgress > 0 && roverProgress < maxIdx ? 'RESUME' : 'PLAY'}
            </button>
          ) : (
            <button className="mc-btn" onClick={onPause} style={{ color: 'var(--caution)', borderColor: 'var(--caution)' }}>
              <Pause size={13} />
              PAUSE
            </button>
          )}

          <button
            className="mc-btn"
            disabled={roverProgress === 0 && !isPlaying}
            onClick={onResetRover}
          >
            <RotateCcw size={12} />
            RESET ROVER
          </button>
        </div>

        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          WAYPOINT: {Math.min(pathLength, Math.floor(roverProgress) + 1)} / {pathLength || 0}
        </div>
      </div>

      {/* Failure Callout if Route is Blocked */}
      {!routeSuccess && failureReason && (
        <div
          style={{
            padding: '8px 12px',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid var(--hazard)',
            borderRadius: '6px',
            color: 'var(--hazard)',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertTriangle size={16} />
          <span>Navigation Planning: {failureReason}</span>
        </div>
      )}
    </div>
  );
}
