import React, { useState, useCallback, useMemo } from 'react';
import {
  Compass,
  Map,
  Navigation,
  Play,
  Pause,
  RotateCcw,
  Shield,
  Zap,
  Radio,
  Wind,
  Flame,
  Activity,
  Layers,
  Database,
  CheckCircle2,
  XCircle,
  Camera,
} from 'lucide-react';

import TerrainThreeMap from './components/three/TerrainThreeMap';
import InteractiveRoverHUD from './components/navigation/InteractiveRoverHUD';
import ElevationProfileChart from './components/navigation/ElevationProfileChart';
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
  // 1. Interactive Marker Endpoints (Cyan Start & Amber Destination)
  const [startPoint, setStartPoint] = useState([5, 5]);
  const [destinationPoint, setDestinationPoint] = useState([40, 40]);
  const [selectionMode, setSelectionMode] = useState('auto'); // 'auto' | 'start' | 'destination'

  // 2. Trajectory Selection & Kinematics State
  const [activeRoute, setActiveRoute] = useState('safest'); // 'safest' (Green) | 'shortest' (Red)
  const [isPlaying, setIsPlaying] = useState(false);
  const [roverProgress, setRoverProgress] = useState(0);
  const [simSpeed, setSimSpeed] = useState(1.0); // 0.5, 1.0, 2.0, 4.0

  // 3. Tactical Camera Mode
  const [cameraMode, setCameraMode] = useState('ORBIT'); // 'ORBIT' | 'ROVER_CHASE' | 'MASTCAM_POV'

  // 4. Viewport Mode (3D Tactical Sim vs Plotly Topographic vs VisionScore)
  const [activeView, setActiveView] = useState('tactical'); // 'tactical' | 'topographic' | 'visionscore'

  // 5. Environmental Danger Telemetry (Wind, Thermal Magma, Seismic)
  const [environmentalData, setEnvironmentalData] = useState({
    windSpeedMs: '28.4',
    windHeading: 'WNW (285°)',
    thermalFluxKw: '4.8',
    seismicAlert: 'NOMINAL',
    opticalDepth: '0.82',
    roverPitch: '1.8',
    roverRoll: '-0.9',
  });

  // 6. Mission Data Bridge (FastAPI REST Endpoint)
  const { dem, costMap, navigation, loading, error, reload, integrity } = useMissionData(
    startPoint || [2, 2],
    destinationPoint || [45, 45]
  );

  // 7. Interactive Hover Cell Readout
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

  // Active path array
  const activePath = useMemo(() => {
    return navigation?.[activeRoute]?.route?.path || [];
  }, [navigation, activeRoute]);

  // Live continuous rover position
  const roverCoord = useMemo(() => {
    if (!activePath || activePath.length === 0) return startPoint || [5, 5];
    const maxIdx = Math.max(1, activePath.length - 1);
    const clampedProgress = Math.max(0, Math.min(maxIdx, roverProgress));
    const k = Math.floor(clampedProgress);
    const t = clampedProgress - k;
    const p0 = activePath[k] || activePath[0];
    const p1 = activePath[Math.min(k + 1, maxIdx)];
    return [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t];
  }, [activePath, roverProgress, startPoint]);

  // Live continuous elevation
  const currentElevation = useMemo(() => {
    if (!dem?.elevation || !roverCoord) return 0;
    return bilinearElevation(roverCoord[0], roverCoord[1], dem.elevation, dem.rows, dem.cols);
  }, [dem, roverCoord]);

  // Distance metrics
  const totalDistance = navigation?.[activeRoute]?.metrics?.total_distance ?? 0;
  const pathLength = activePath.length;
  const maxIdx = Math.max(1, pathLength - 1);
  const progressPct = Math.min(100, Math.round((roverProgress / maxIdx) * 100));
  const distanceTravelled = (totalDistance * (progressPct / 100)).toFixed(1);

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
      {/* 1. TOP COMMAND TELEMETRY BAR (38px height)                    */}
      {/* ───────────────────────────────────────────────────────────── */}
      <header className="mc-top-bar">
        {/* Left: Branding & System State */}
        <div className="mc-brand-area">
          <Radio size={15} color="var(--rover)" />
          <div className="mc-title">MARS-09 // ODYSSEY RECON</div>
          <span
            style={{
              fontSize: '9px',
              fontFamily: 'var(--font-mono)',
              padding: '1px 6px',
              background: environmentalData.seismicAlert !== 'NOMINAL' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.2)',
              color: environmentalData.seismicAlert !== 'NOMINAL' ? 'var(--hazard)' : 'var(--safe)',
              fontWeight: 700,
              letterSpacing: '0.05em',
            }}
          >
            SYS: {environmentalData.seismicAlert}
          </span>
        </div>

        {/* Center: Live Environmental Readout */}
        <div className="mc-env-readout">
          <div className="mc-env-item">
            <Wind size={12} color="#67e8f9" />
            <span>WIND: {environmentalData.windSpeedMs} m/s {environmentalData.windHeading}</span>
          </div>
          <div className="mc-env-item">
            <Flame size={12} color="#f97316" />
            <span>THERMAL: {environmentalData.thermalFluxKw} kW/m²</span>
          </div>
          <div className="mc-env-item" style={{ color: 'var(--text-muted)' }}>
            <span>OPTICAL DEPTH: {environmentalData.opticalDepth} τ</span>
          </div>
          <div className="mc-env-item">
            <span>PITCH: {environmentalData.roverPitch}° | ROLL: {environmentalData.roverRoll}°</span>
          </div>
        </div>

        {/* Right: Viewport Mode Switcher & Telemetry Health */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="mc-view-switcher">
            <button
              className={`mc-view-btn ${activeView === 'tactical' ? 'active' : ''}`}
              onClick={() => setActiveView('tactical')}
            >
              3D TACTICAL SIM
            </button>
            <button
              className={`mc-view-btn ${activeView === 'topographic' ? 'active' : ''}`}
              onClick={() => setActiveView('topographic')}
            >
              PLOTLY TOPO
            </button>
            <button
              className={`mc-view-btn ${activeView === 'visionscore' ? 'active' : ''}`}
              onClick={() => setActiveView('visionscore')}
            >
              <Camera size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              VISIONSCORE 2.0
            </button>
          </div>

          <StatusChip status={loading ? 'INITIALIZING' : error ? 'OFFLINE' : navStatus} />
        </div>
      </header>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. FULL-BLEED 100VW × 100VH 3D VIEWPORT / VISIONSCORE         */}
      {/* ───────────────────────────────────────────────────────────── */}
      {activeView === 'visionscore' ? (
        <main className="mc-viewport-area" style={{ top: '38px', height: 'calc(100vh - 38px)', overflow: 'hidden' }}>
          <ErrorBoundary fallbackTitle="VisionScore 2.0 Subsystem Failure">
            <VisionScoreDashboard />
          </ErrorBoundary>
        </main>
      ) : (
        <>
          <main className="mc-viewport-area">
            {loading && !dem ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px' }}>
                <div className="mono" style={{ color: 'var(--rover)', fontSize: '12px', letterSpacing: '0.12em' }}>
                  INGESTING MARTIAN VOLCANIC DEM TOPOGRAPHY...
                </div>
                <div style={{ width: '180px', height: '2px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                  <div style={{ width: '50%', height: '100%', background: 'var(--rover)', animation: 'status-blink 1s infinite alternate' }} />
                </div>
              </div>
            ) : error ? (
              <div style={{ position: 'absolute', top: '60px', left: '20px', zIndex: 100, maxWidth: '450px' }}>
                <ErrorBanner error={error} onRetry={reload} />
              </div>
            ) : !dem ? (
              <EmptyState
                title="Elevation data not supplied"
                message="Upload or connect a DEM source to visualize Martian geological features."
                icon={Database}
              />
            ) : activeView === 'tactical' ? (
              /* HIGH-DETAIL THREE.JS TACTICAL SIM (Volcanic Vents, Wind Streaks, 3D Rover & Camera) */
              <ErrorBoundary fallbackTitle="Three.js Tactical Viewport Error">
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
                  cameraMode={cameraMode}
                  onEnvironmentalUpdate={setEnvironmentalData}
                />
              </ErrorBoundary>
            ) : (
              /* PLOTLY TOPOGRAPHIC CONTOUR & ELEVATION RELIEF VIEW */
              <>
                <TerrainControls
                  overlays={overlays}
                  onChangeOverlay={(k, v) => setOverlays((prev) => ({ ...prev, [k]: v }))}
                  displayScale={displayScale}
                  onChangeDisplayScale={setDisplayScale}
                />
                <ErrorBoundary fallbackTitle="Topographic 3D Surface Rendering Error">
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
          </main>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 3. FLOATING LEFT TACTICAL STACK (325px wide)                  */}
          {/* ───────────────────────────────────────────────────────────── */}
          <aside className="mc-left-stack">
            <InteractiveRoverHUD
              startPoint={startPoint}
              destinationPoint={destinationPoint}
              onResetPoints={handleResetPoints}
              onSetSelectionMode={setSelectionMode}
              selectionMode={selectionMode}
              navigation={navigation}
              activeRoute={activeRoute}
              onSelectRoute={handleSelectRoute}
              navStatus={navStatus}
              cameraMode={cameraMode}
              onSetCameraMode={setCameraMode}
              environmentalData={environmentalData}
            />
          </aside>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 4. FLOATING RIGHT STATUS & LEGEND CORNER                      */}
          {/* ───────────────────────────────────────────────────────────── */}
          <div className="mc-floating-status tactical-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '4px' }}>
              <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                MAP LEGEND & INTEGRITY
              </span>
              <div style={{ display: 'flex', gap: '6px', fontSize: '9px', fontFamily: 'var(--font-mono)' }}>
                <span style={{ color: integrity.demLoaded ? 'var(--safe)' : 'var(--hazard)' }}>DEM ✓</span>
                <span style={{ color: integrity.costMapLoaded ? 'var(--safe)' : 'var(--hazard)' }}>COST ✓</span>
                <span style={{ color: integrity.routeLoaded ? 'var(--safe)' : 'var(--hazard)' }}>NAV ✓</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', background: 'var(--rover)', display: 'inline-block' }} />
                <span>START [CYAN]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', background: 'var(--caution)', display: 'inline-block' }} />
                <span>GOAL [AMBER]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', background: 'var(--safe)', display: 'inline-block' }} />
                <span>SAFEST ROUTE</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', background: 'var(--hazard)', display: 'inline-block' }} />
                <span>SHORTEST ROUTE</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', gridColumn: 'span 2' }}>
                <span style={{ width: '8px', height: '8px', background: '#ff3700', display: 'inline-block' }} />
                <span>VOLCANIC MAGMA VEIN (INF)</span>
              </div>
            </div>

            {/* Hover Coordinate Readout */}
            <div style={{ marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '4px', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
              {hoveredCell ? (
                <span style={{ color: 'var(--text-secondary)' }}>
                  CURSOR: ({hoveredCell.row}, {hoveredCell.col}) ·{' '}
                  <span style={{ color: 'var(--text-primary)' }}>{hoveredCell.elevation?.toFixed(1)} m</span> ·{' '}
                  <span style={{ color: hoveredCell.cost >= 9999 ? 'var(--hazard)' : hoveredCell.cost > 2.0 ? 'var(--caution)' : 'var(--safe)' }}>
                    {hoveredCell.cost >= 9999 ? 'VOLCANIC HAZARD' : hoveredCell.cost > 2.0 ? `CAUTION (${hoveredCell.cost.toFixed(1)})` : 'SAFE'}
                  </span>
                </span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>Hover over terrain mesh to inspect geology</span>
              )}
            </div>
          </div>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 5. FLOATING BOTTOM MISSION TIMELINE & ELEVATION TRANSECT DOCK  */}
          {/* ───────────────────────────────────────────────────────────── */}
          <footer className="mc-bottom-dock tactical-panel">
            {/* Left: Transport Cluster & Speed Controls */}
            <div className="mc-transport-cluster">
              <div className="mc-btn-group">
                {!isPlaying ? (
                  <button
                    className="mc-tactical-btn active"
                    disabled={!navigation?.[activeRoute]?.route?.success || pathLength === 0}
                    onClick={roverProgress > 0 && roverProgress < maxIdx ? handleResume : handlePlay}
                  >
                    <Play size={12} fill="#06080d" />
                    <span>{roverProgress > 0 && roverProgress < maxIdx ? 'RESUME' : 'PLAY'}</span>
                  </button>
                ) : (
                  <button className="mc-tactical-btn" onClick={handlePause} style={{ color: 'var(--caution)', borderColor: 'var(--caution)' }}>
                    <Pause size={12} />
                    <span>PAUSE</span>
                  </button>
                )}

                <button
                  className="mc-tactical-btn"
                  disabled={roverProgress === 0 && !isPlaying}
                  onClick={handleResetRover}
                >
                  <RotateCcw size={11} />
                  <span>RESET</span>
                </button>

                {/* Speed Selector */}
                <div className="mc-speed-selector">
                  {[0.5, 1.0, 2.0, 4.0].map((spd) => (
                    <button
                      key={spd}
                      className={`mc-speed-btn ${simSpeed === spd ? 'active' : ''}`}
                      onClick={() => setSimSpeed(spd)}
                    >
                      {spd}×
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                <span>PROGRESS:</span>
                <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.1)', position: 'relative' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${progressPct}%`,
                      background: activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)',
                      transition: 'width 100ms linear',
                    }}
                  />
                </div>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{progressPct}%</span>
              </div>
            </div>

            {/* Center: Live SVG Elevation Profile Transect */}
            <div className="mc-transect-box">
              <ElevationProfileChart
                path={activePath}
                elevation={dem?.elevation}
                costMap={costMap}
                roverProgress={roverProgress}
                totalDistance={totalDistance}
                activeRoute={activeRoute}
              />
            </div>

            {/* Right: Live Rover Waypoint & Altimeter Telemetry */}
            <div className="mc-bottom-dock-right" style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>COORDINATES:</span>
                <span style={{ color: 'var(--rover)', fontWeight: 600 }}>
                  ({roverCoord[0].toFixed(1)}, {roverCoord[1].toFixed(1)})
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>SURFACE ALT:</span>
                <span style={{ fontWeight: 600 }}>{currentElevation.toFixed(1)} m</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>TRAVERSE:</span>
                <span>{distanceTravelled} / {totalDistance.toFixed(1)} m</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>WAYPOINT:</span>
                <span>{Math.min(pathLength, Math.floor(roverProgress) + 1)} / {pathLength || 0}</span>
              </div>
            </div>
          </footer>
        </>
      )}
    </div>
  );
}
