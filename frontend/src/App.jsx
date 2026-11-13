import React, { useState, useCallback, useMemo } from 'react';
import {
  Compass,
  Map,
  Navigation,
  Layers,
  AlertTriangle,
  MapPin,
  CheckCircle2,
  XCircle,
  Activity,
  Database,
  Radio,
} from 'lucide-react';

import Terrain3DMap from './components/terrain/Terrain3DMap';
import TerrainControls from './components/terrain/TerrainControls';
import RoverSimulation from './components/rover/RoverSimulation';
import RouteMetrics from './components/navigation/RouteMetrics';
import RouteComparison from './components/navigation/RouteComparison';

import StatusChip from './components/shared/StatusChip';
import ErrorBanner from './components/shared/ErrorBanner';
import EmptyState from './components/shared/EmptyState';
import ErrorBoundary from './components/shared/ErrorBoundary';

import { useMissionData } from './hooks/useMissionData';
import { useSimulation } from './hooks/useSimulation';
import { getCostClassification } from './utils/terrainHelpers';
import { isInsideBounds } from './utils/coordinateMapping';

export default function App() {
  // 1. Mission Coordinates State (§1.1, §7.1)
  const [startPos, setStartPos] = useState([2, 2]);
  const [goalPos, setGoalPos] = useState([45, 45]);

  // 2. Mission Data Integration Hook (§7.3)
  const { dem, costMap, navigation, loading, error, reload, integrity } = useMissionData(startPos, goalPos);

  // 3. View Switcher Mode (§2.4)
  const [activeView, setActiveView] = useState('terrain'); // 'terrain' | 'simulation'

  // 4. Terrain Overlay Controls State (§2.5, §3.3)
  const [overlays, setOverlays] = useState({
    route: true,
    hazards: true,
    caution: true,
    rover: true,
    contours: true,
  });
  const [displayScale, setDisplayScale] = useState(1.0);

  // 5. Interactive Inspection State (§2.5, §9)
  const [hoveredCell, setHoveredCell] = useState(null);
  const [pinnedCell, setPinnedCell] = useState(null);
  const [outOfBoundsWarning, setOutOfBoundsWarning] = useState(null);

  // 6. Rover Simulation Lifecycle Engine (§4.2)
  const routePath = useMemo(() => {
    return navigation?.safest?.route?.success ? navigation.safest.route.path || [] : [];
  }, [navigation]);

  const simState = useSimulation(routePath, { initialSpeed: 1.0 });

  // Current active rover position
  const activeRoverPos = useMemo(() => {
    if (routePath.length > 0) {
      return simState.currentCoordinate || routePath[0];
    }
    return startPos;
  }, [routePath, simState.currentCoordinate, startPos]);

  // Handle overlay checkbox toggle
  const handleToggleOverlay = useCallback((key, checked) => {
    setOverlays((prev) => ({ ...prev, [key]: checked }));
  }, []);

  // Handle cell click on 3D terrain (§2.5)
  const handleCellClick = useCallback((cellData) => {
    setPinnedCell(cellData);
  }, []);

  // Handle custom destination goal
  const handleSetGoal = useCallback(([r, c]) => {
    setGoalPos([r, c]);
    setPinnedCell(null);
    simState.reset();
  }, [simState]);

  // Validate rover position against DEM bounds (§8.1)
  const isRoverValid = useMemo(() => {
    if (!dem || !activeRoverPos) return true;
    return isInsideBounds(activeRoverPos[0], activeRoverPos[1], dem.rows, dem.cols);
  }, [dem, activeRoverPos]);

  return (
    <div className="mc-container">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* TOP BAR (§2.4)                                                */}
      {/* ───────────────────────────────────────────────────────────── */}
      <header className="mc-top-bar">
        <div className="mc-brand-area">
          <Radio size={18} color="var(--rover)" />
          <div>
            <div className="mc-title">MARS-09 ODYSSEY</div>
            <div className="mc-subtitle">TRACK A // PLANETARY RECONNAISSANCE & AUTONOMOUS NAVIGATION</div>
          </div>
        </div>

        {/* View Switcher (§2.4) */}
        <div className="mc-view-switcher">
          <button
            className={`mc-view-btn ${activeView === 'terrain' ? 'active' : ''}`}
            onClick={() => setActiveView('terrain')}
          >
            <Map size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Terrain Exploration
          </button>
          <button
            className={`mc-view-btn ${activeView === 'simulation' ? 'active' : ''}`}
            onClick={() => setActiveView('simulation')}
          >
            <Navigation size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Rover Simulation
          </button>
        </div>

        {/* Global Mission Status Chip (§2.4, §4.3) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            MISSION STATUS
          </span>
          <StatusChip status={loading ? 'INITIALIZING' : error ? 'OFFLINE' : simState.status} />
        </div>
      </header>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* MAIN SPLIT VIEWPORT (§2.4: 70% 3D Viewport / 30% Telemetry)   */}
      {/* ───────────────────────────────────────────────────────────── */}
      <main className="mc-main-body">
        {/* Left Column (70%): 3D Terrain Viewport */}
        <section className="mc-viewport-area">
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px' }}>
              <div className="mono" style={{ color: 'var(--rover)', fontSize: '13px', letterSpacing: '0.08em' }}>
                INGESTING MARS DEM ELEVATION MATRIX...
              </div>
              <div style={{ width: '180px', height: '2px', background: 'var(--border-subtle)', overflow: 'hidden' }}>
                <div style={{ width: '50%', height: '100%', background: 'var(--safe)', animation: 'status-blink 1s infinite alternate' }} />
              </div>
            </div>
          ) : error ? (
            <ErrorBanner error={error} onRetry={reload} />
          ) : !dem ? (
            <EmptyState
              title="Elevation data not supplied"
              message="Upload or connect a DEM source to visualize Martian geological features."
              icon={Database}
            />
          ) : (
            <>
              {/* Overlay Toolbar (§2.5) */}
              <TerrainControls
                overlays={overlays}
                onChangeOverlay={handleToggleOverlay}
                displayScale={displayScale}
                onChangeDisplayScale={setDisplayScale}
              />

              {/* 3D Map wrapped in ErrorBoundary (§8.2) */}
              <ErrorBoundary fallbackTitle="Terrain 3D Surface Rendering Exception">
                <Terrain3DMap
                  dem={dem}
                  costMap={costMap}
                  navigation={navigation}
                  roverPos={activeRoverPos}
                  simulationIndex={simState.currentIndex}
                  overlays={overlays}
                  displayScale={displayScale}
                  onHoverCell={setHoveredCell}
                  onClickCell={handleCellClick}
                  onOutOfBounds={(badPts) => setOutOfBoundsWarning(badPts[0])}
                />
              </ErrorBoundary>

              {/* Pinned Cell Interactive Chip (§2.5) */}
              {pinnedCell && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '16px',
                    left: '16px',
                    zIndex: 10,
                    background: 'rgba(14, 21, 34, 0.95)',
                    border: '1px solid var(--border-active)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                    backdropFilter: 'blur(4px)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
                    <MapPin size={14} color="var(--rover)" />
                    <span>PINNED: ({pinnedCell.row}, {pinnedCell.col})</span>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      · {pinnedCell.elevation !== null ? `${pinnedCell.elevation.toFixed(1)} m` : '—'}
                    </span>
                    <span
                      style={{
                        color:
                          pinnedCell.cost === Infinity || pinnedCell.cost >= 9999
                            ? 'var(--hazard)'
                            : pinnedCell.cost > 2.0
                            ? 'var(--caution)'
                            : 'var(--safe)',
                      }}
                    >
                      · {pinnedCell.cost === Infinity || pinnedCell.cost >= 9999
                        ? 'HAZARD (IMPASSABLE)'
                        : pinnedCell.cost > 2.0
                        ? `CAUTION (${pinnedCell.cost.toFixed(1)})`
                        : 'SAFE (1.0)'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    {pinnedCell.cost !== Infinity && pinnedCell.cost < 9999 && (
                      <button
                        className="mc-btn"
                        style={{ padding: '2px 8px', fontSize: '11px', color: 'var(--safe)', borderColor: 'var(--safe)' }}
                        onClick={() => handleSetGoal([pinnedCell.row, pinnedCell.col])}
                      >
                        SET AS GOAL
                      </button>
                    )}
                    <button
                      className="mc-btn"
                      style={{ padding: '2px 6px', fontSize: '11px' }}
                      onClick={() => setPinnedCell(null)}
                    >
                      DISMISS
                    </button>
                  </div>
                </div>
              )}

              {/* Invalid Rover Position Warning Card (§8.1) */}
              {(!isRoverValid || outOfBoundsWarning) && (
                <div
                  style={{
                    position: 'absolute',
                    top: '64px',
                    right: '16px',
                    zIndex: 10,
                    background: 'rgba(6, 182, 212, 0.15)',
                    border: '1px solid var(--rover)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: 'var(--rover)',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
                  }}
                >
                  <AlertTriangle size={14} />
                  <span>
                    Rover position out of bounds: (
                    {outOfBoundsWarning ? `${outOfBoundsWarning[0]}, ${outOfBoundsWarning[1]}` : `${activeRoverPos[0]}, ${activeRoverPos[1]}`}
                    )
                  </span>
                  <button
                    onClick={() => setOutOfBoundsWarning(null)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--rover)', cursor: 'pointer' }}
                  >
                    ✕
                  </button>
                </div>
              )}
            </>
          )}
        </section>

        {/* Right Column (30%, min 360px): Telemetry Stack */}
        <aside className="mc-telemetry-column">
          {/* 1. Navigation Telemetry Panel (§5.2) */}
          <RouteMetrics navigation={navigation} />

          {/* 2. Collapsible Route Comparison Drawer (§5.3) */}
          <RouteComparison navigation={navigation} />

          {/* 3. Rover Simulation Controls & Live Telemetry (§4.2, §4.3) */}
          <ErrorBoundary fallbackTitle="Rover Simulation Module Failure">
            <RoverSimulation
              simState={simState}
              routePath={routePath}
              elevation={dem?.elevation}
              costMap={costMap}
              safestMetrics={navigation?.safest?.metrics}
              routeSuccess={navigation?.safest?.route?.success ?? false}
            />
          </ErrorBoundary>
        </aside>
      </main>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* BOTTOM BAR (§2.4: Legend, Coordinate Readout, Integrity)      */}
      {/* ───────────────────────────────────────────────────────────── */}
      <footer className="mc-bottom-bar">
        {/* Left: Legend Swatches */}
        <div className="mc-legend">
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: 'var(--safe)' }} />
            <span>SAFE</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: 'var(--caution)' }} />
            <span>CAUTION (&gt;2.0)</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: 'var(--hazard)' }} />
            <span>HAZARD (IMPASSABLE)</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: 'var(--rover)' }} />
            <span>ROVER</span>
          </div>
        </div>

        {/* Center: Live Debounced Coordinate Readout (§2.5, §9) */}
        <div className="mc-coord-readout">
          {hoveredCell ? (
            <span>
              ROW: {hoveredCell.row} · COL: {hoveredCell.col} · ELEVATION:{' '}
              {hoveredCell.elevation !== null ? `${hoveredCell.elevation.toFixed(1)} m` : '—'} ·{' '}
              <span
                style={{
                  color:
                    hoveredCell.cost === Infinity || hoveredCell.cost >= 9999
                      ? 'var(--hazard)'
                      : hoveredCell.cost > 2.0
                      ? 'var(--caution)'
                      : 'var(--safe)',
                }}
              >
                {hoveredCell.cost === Infinity || hoveredCell.cost >= 9999
                  ? 'HAZARD (IMPASSABLE)'
                  : hoveredCell.cost > 2.0
                  ? `CAUTION (${hoveredCell.cost.toFixed(2)})`
                  : 'SAFE (1.00)'}
              </span>
            </span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>
              Hover over terrain surface to inspect coordinates and elevation
            </span>
          )}
        </div>

        {/* Right: Data Integrity Indicators (§2.4) */}
        <div className="mc-integrity-indicator">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            {integrity.demLoaded ? <CheckCircle2 size={13} color="var(--safe)" /> : <XCircle size={13} color="var(--hazard)" />}
            <span>DEM</span>
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            {integrity.costMapLoaded ? <CheckCircle2 size={13} color="var(--safe)" /> : <XCircle size={13} color="var(--hazard)" />}
            <span>Cost Map</span>
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            {integrity.routeLoaded ? <CheckCircle2 size={13} color="var(--safe)" /> : <XCircle size={13} color="var(--caution)" />}
            <span>Route</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
