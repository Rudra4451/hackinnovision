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
  Eye,
  Sliders,
  Camera,
} from 'lucide-react';

import TerrainThreeMap from './components/three/TerrainThreeMap';
import InteractiveRoverHUD from './components/navigation/InteractiveRoverHUD';
import RouteMetrics from './components/navigation/RouteMetrics';
import RouteComparison from './components/navigation/RouteComparison';
import Terrain3DMap from './components/terrain/Terrain3DMap';
import TerrainControls from './components/terrain/TerrainControls';
import VisionScoreDashboard from './components/visionscore/VisionScoreDashboard';

import StatusChip from './components/shared/StatusChip';
import ErrorBanner from './components/shared/ErrorBanner';
import EmptyState from './components/shared/EmptyState';
import ErrorBoundary from './components/shared/ErrorBoundary';

import { useMissionData } from './hooks/useMissionData';
import { bilinearElevation } from './utils/coordinateMapping';

export default function App() {
  // 1. Interactive Marker Endpoints (Blue Start & Yellow Destination)
  const [startPoint, setStartPoint] = useState([5, 5]);
  const [destinationPoint, setDestinationPoint] = useState([40, 40]);
  const [selectionMode, setSelectionMode] = useState('auto'); // 'auto' | 'start' | 'destination'

  // 2. Authoritative Route Selection & Rover Kinematics
  const [activeRoute, setActiveRoute] = useState('safest'); // 'safest' (Green) | 'shortest' (Red)
  const [isPlaying, setIsPlaying] = useState(false);
  const [roverProgress, setRoverProgress] = useState(0);

  // 3. View Mode: Interactive Three.js (Unified) vs Topographic Plotly
  const [activeView, setActiveView] = useState('interactive'); // 'interactive' | 'topographic'

  // 4. Mission Data Bridge (FastAPI Integration)
  const { dem, costMap, navigation, loading, error, reload, integrity } = useMissionData(
    startPoint || [2, 2],
    destinationPoint || [45, 45]
  );

  // 5. Interactive Inspection State
  const [hoveredCell, setHoveredCell] = useState(null);

  // Topographic Overlay Controls (for Plotly mode)
  const [overlays, setOverlays] = useState({
    route: true,
    hazards: true,
    caution: true,
    rover: true,
    contours: true,
  });
  const [displayScale, setDisplayScale] = useState(1.0);

  // Current active path waypoints
  const activePath = useMemo(() => {
    return navigation?.[activeRoute]?.route?.path || [];
  }, [navigation, activeRoute]);

  // Live continuous rover position
  const roverCoord = useMemo(() => {
    if (!activePath || activePath.length === 0) return startPoint || [0, 0];
    const maxIdx = Math.max(1, activePath.length - 1);
    const clampedProgress = Math.max(0, Math.min(maxIdx, roverProgress));
    const k = Math.floor(clampedProgress);
    const t = clampedProgress - k;
    const p0 = activePath[k] || activePath[0];
    const p1 = activePath[Math.min(k + 1, maxIdx)];
    return [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t];
  }, [activePath, roverProgress, startPoint]);

  // Current continuous elevation
  const currentElevation = useMemo(() => {
    if (!dem?.elevation || !roverCoord) return null;
    return bilinearElevation(roverCoord[0], roverCoord[1], dem.elevation, dem.rows, dem.cols);
  }, [dem, roverCoord]);

  // High-level Navigation Status
  const navStatus = useMemo(() => {
    if (!startPoint) return 'SELECT_START';
    if (!destinationPoint) return 'SELECT_DESTINATION';
    if (loading) return 'CALCULATING';
    if (!navigation?.[activeRoute]?.route?.success) return 'BLOCKED';
    if (isPlaying) return 'NAVIGATING';
    if (roverProgress > 0 && roverProgress < activePath.length - 1) return 'PAUSED';
    if (roverProgress >= activePath.length - 1 && activePath.length > 1) return 'ARRIVED';
    return 'READY';
  }, [startPoint, destinationPoint, loading, navigation, activeRoute, isPlaying, roverProgress, activePath]);

  // Handlers for Terrain Interaction
  const handleSelectStart = useCallback((row, col) => {
    setStartPoint([row, col]);
    setIsPlaying(false);
    setRoverProgress(0);
    setSelectionMode('auto');
  }, []);

  const handleSelectDestination = useCallback((row, col) => {
    setDestinationPoint([row, col]);
    setIsPlaying(false);
    setRoverProgress(0);
    setSelectionMode('auto');
  }, []);

  const handleResetPoints = useCallback(() => {
    setStartPoint(null);
    setDestinationPoint(null);
    setIsPlaying(false);
    setRoverProgress(0);
    setSelectionMode('start');
  }, []);

  // Handlers for Rover Traversal Controls
  const handlePlay = useCallback(() => {
    if (!navigation?.[activeRoute]?.route?.success) return;
    setIsPlaying(true);
  }, [navigation, activeRoute]);

  const handlePause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const handleResume = useCallback(() => {
    if (!navigation?.[activeRoute]?.route?.success) return;
    setIsPlaying(true);
  }, [navigation, activeRoute]);

  const handleResetRover = useCallback(() => {
    setIsPlaying(false);
    setRoverProgress(0);
  }, []);

  const handleSelectRoute = useCallback((routeKey) => {
    setActiveRoute(routeKey);
    setIsPlaying(false);
    setRoverProgress(0);
  }, []);

  const handleRoverProgressUpdate = useCallback((nextProgress, isDone) => {
    setRoverProgress(nextProgress);
    if (isDone) {
      setIsPlaying(false);
    }
  }, []);

  return (
    <div className="mc-container">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* TOP BAR: BRANDING, VIEW SWITCHER & STATUS                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <header className="mc-top-bar">
        <div className="mc-brand-area">
          <Radio size={18} color="var(--rover)" />
          <div>
            <div className="mc-title">MARS-09 ODYSSEY</div>
            <div className="mc-subtitle">INTERACTIVE TERRAIN RECONNAISSANCE & AUTONOMOUS ROVER NAVIGATION</div>
          </div>
        </div>

        {/* View Switcher: Interactive Three.js vs Topographic Surface */}
        <div className="mc-view-switcher">
          <button
            className={`mc-view-btn ${activeView === 'interactive' ? 'active' : ''}`}
            onClick={() => setActiveView('interactive')}
            title="Three.js interactive 3D terrain with raycasting & animated rover"
          >
            <Navigation size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Interactive Rover 3D
          </button>
          <button
            className={`mc-view-btn ${activeView === 'topographic' ? 'active' : ''}`}
            onClick={() => setActiveView('topographic')}
            title="Plotly topographic elevation contours & analytical strata"
          >
            <Map size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Topographic Analysis
          </button>
          <button
            className={`mc-view-btn ${activeView === 'visionscore' ? 'active' : ''}`}
            onClick={() => setActiveView('visionscore')}
          >
            <Camera size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            VisionScore 2.0
          </button>
        </div>

        {/* Global Mission Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            STATUS:
          </span>
          <StatusChip status={loading ? 'INITIALIZING' : error ? 'OFFLINE' : navStatus} />
        </div>
      </header>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* ───────────────────────────────────────────────────────────── */}
      {/* MAIN VIEWPORT: VisionScore 2.0 OR Split 3D Terrain / Telemetry */}
      {/* ───────────────────────────────────────────────────────────── */}
      {activeView === 'visionscore' ? (
        <main className="mc-main-body" style={{ display: 'block', overflow: 'hidden' }}>
          <ErrorBoundary fallbackTitle="VisionScore 2.0 Subsystem Failure">
            <VisionScoreDashboard />
          </ErrorBoundary>
        </main>
      ) : (
        <main className="mc-main-body">
          {/* Left Column (70%): 3D Terrain Viewport */}
          <section className="mc-viewport-area">
          {loading && !dem ? (
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
          ) : activeView === 'interactive' ? (
            /* UNIFIED THREE.JS INTERACTIVE MODULE (Raycasting + Rover) */
            <ErrorBoundary fallbackTitle="Three.js 3D Interactive Viewport Failure">
              <TerrainThreeMap
                dem={dem}
                costMap={costMap}
                navigation={navigation}
                startPoint={startPoint}
                destinationPoint={destinationPoint}
                onSelectStart={handleSelectStart}
                onSelectDestination={handleSelectDestination}
                selectionMode={selectionMode}
                activeRoute={activeRoute}
                isPlaying={isPlaying}
                roverProgress={roverProgress}
                onRoverProgressUpdate={handleRoverProgressUpdate}
                onHoverCell={setHoveredCell}
              />
            </ErrorBoundary>
          ) : (
            /* TOPOGRAPHIC SURFACE EXPLORATION (Plotly) */
            <>
              <TerrainControls
                overlays={overlays}
                onChangeOverlay={(k, v) => setOverlays((prev) => ({ ...prev, [k]: v }))}
                displayScale={displayScale}
                onChangeDisplayScale={setDisplayScale}
              />
              <ErrorBoundary fallbackTitle="Terrain 3D Surface Rendering Exception">
                <Terrain3DMap
                  dem={dem}
                  costMap={costMap}
                  navigation={navigation}
                  roverPos={roverCoord ? [Math.round(roverCoord[0]), Math.round(roverCoord[1])] : startPoint}
                  simulationIndex={Math.floor(roverProgress)}
                  overlays={overlays}
                  displayScale={displayScale}
                  onHoverCell={setHoveredCell}
                />
              </ErrorBoundary>
            </>
          )}
        </section>

        {/* Right Column (30%, min 360px): Telemetry Stack */}
        <aside className="mc-telemetry-column">
          {/* 1. Integrated Interactive Rover HUD & Kinematic Controls */}
          <InteractiveRoverHUD
            startPoint={startPoint}
            destinationPoint={destinationPoint}
            onResetPoints={handleResetPoints}
            onSetSelectionMode={setSelectionMode}
            selectionMode={selectionMode}
            navigation={navigation}
            activeRoute={activeRoute}
            onSelectRoute={handleSelectRoute}
            isPlaying={isPlaying}
            onPlay={handlePlay}
            onPause={handlePause}
            onResume={handleResume}
            onResetRover={handleResetRover}
            roverProgress={roverProgress}
            roverCoord={roverCoord}
            currentElevation={currentElevation}
            navStatus={navStatus}
            error={error}
          />

          {/* 2. Route Metrics Panel (Safest vs Shortest metrics) */}
          <RouteMetrics navigation={navigation} />

          {/* 3. Collapsible Route Comparison Drawer */}
          <RouteComparison navigation={navigation} />
        </aside>
      </main>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* BOTTOM BAR: LEGEND, COORDINATE READOUT & DATA INTEGRITY       */}
      {/* ───────────────────────────────────────────────────────────── */}
      <footer className="mc-bottom-bar">
        {/* Left: Map Legend Swatches */}
        <div className="mc-legend">
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: '#3b82f6' }} />
            <span>START (BLUE)</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: '#f59e0b' }} />
            <span>DESTINATION (YELLOW)</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: '#10b981' }} />
            <span>SAFEST (GREEN)</span>
          </div>
          <div className="mc-legend-item">
            <span className="mc-swatch" style={{ background: '#ef4444' }} />
            <span>SHORTEST (RED)</span>
          </div>
        </div>

        {/* Center: Live Debounced Coordinate Readout */}
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
              Click on terrain to place Start (Blue) & Destination (Yellow) markers
            </span>
          )}
        </div>

        {/* Right: Data Source Integrity Indicators */}
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
            <span>Navigation</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
