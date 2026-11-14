import React, { useState, useCallback, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Radio,
  Wind,
  Flame,
  Camera,
  Database,
} from 'lucide-react';

import TerrainThreeMap from './components/three/TerrainThreeMap';
import InteractiveRoverHUD from './components/navigation/InteractiveRoverHUD';
import ElevationProfileChart from './components/navigation/ElevationProfileChart';
import Terrain3DMap from './components/terrain/Terrain3DMap';
import TerrainControls from './components/terrain/TerrainControls';
import VisionScoreDashboard from './components/visionscore/VisionScoreDashboard';
import AresTerminalLanding from './components/terminal/AresTerminalLanding';
import AresLogo from './components/terminal/AresLogo';

import StatusChip from './components/shared/StatusChip';
import ErrorBanner from './components/shared/ErrorBanner';
import EmptyState from './components/shared/EmptyState';
import ErrorBoundary from './components/shared/ErrorBoundary';

import { useMissionData } from './hooks/useMissionData';
import { bilinearElevation } from './utils/coordinateMapping';
import { compareRoutes } from './api/client';

export default function App() {
  // 0. Classified Terminal Landing Entry State
  const [showTerminal, setShowTerminal] = useState(true);

  // 1. Interactive Marker Endpoints (Sky Blue Start & Amber Destination)
  const [startPoint, setStartPoint] = useState([15, 15]);
  const [destinationPoint, setDestinationPoint] = useState([185, 185]);
  const [selectionMode, setSelectionMode] = useState('auto'); // 'auto' | 'start' | 'destination'

  // 2. Trajectory Selection & Kinematics State
  const [activeRoute, setActiveRoute] = useState('safest'); // 'safest' (Sky Blue) | 'shortest' (Crimson)
  const [isPlaying, setIsPlaying] = useState(false);
  const [roverProgress, setRoverProgress] = useState(0);
  const [simSpeed, setSimSpeed] = useState(1.0); // 0.5, 1.0, 2.0, 4.0

  // 3. Tactical Camera Mode & State
  const [cameraMode, setCameraMode] = useState('ORBIT'); // 'ORBIT' | 'ROVER_CHASE' | 'MASTCAM_POV'
  const [cameraState, setCameraState] = useState({ pos: null, target: null });
  const [focusTarget, setFocusTarget] = useState(null);

  // 4. Interactive Hazard Injection & Dynamic Mid-Course Rerouting
  const [toolMode, setToolMode] = useState('nav'); // 'nav' | 'landslide' | 'vortex' | 'fissure'
  const [customCostMap, setCustomCostMap] = useState(null);
  const [customNavigation, setCustomNavigation] = useState(null);
  const [rerouteAlert, setRerouteAlert] = useState(null);

  // 5. Viewport Mode (3D Tactical Sim vs Plotly Topographic vs VisionScore)
  const [activeView, setActiveView] = useState('tactical'); // 'tactical' | 'topographic' | 'visionscore'

  // 6. Environmental Telemetry (Wind, Thermal, Seismic, Inclinometer)
  const [environmentalData, setEnvironmentalData] = useState({
    windSpeedMs: '28.4',
    windHeading: 'WNW (285°)',
    thermalFluxKw: '4.8',
    seismicAlert: 'NOMINAL',
    opticalDepth: '0.82',
    roverPitch: '0.0',
    roverRoll: '0.0',
  });

  // 7. Mission Data Bridge (FastAPI REST Endpoint)
  const { dem, costMap, navigation, loading, error, reload, integrity } = useMissionData(
    startPoint || [15, 15],
    destinationPoint || [185, 185]
  );

  // Effective cost map and navigation (allowing local dynamic hazard overrides)
  const effectiveCostMap = customCostMap || costMap;
  const effectiveNavigation = customNavigation || navigation;

  // 8. Interactive Hover Cell Readout
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
    return effectiveNavigation?.[activeRoute]?.route?.path || [];
  }, [effectiveNavigation, activeRoute]);

  // Live continuous rover position
  const roverCoord = useMemo(() => {
    if (!activePath || activePath.length === 0) return startPoint || [15, 15];
    const maxIdx = Math.max(1, activePath.length - 1);
    const clampedProgress = Math.max(0, Math.min(maxIdx, roverProgress));
    const k = Math.floor(clampedProgress);
    const t = clampedProgress - k;
    const p0 = activePath[k] || activePath[0];
    const p1 = activePath[Math.min(k + 1, maxIdx)];
    return [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t];
  }, [activePath, roverProgress, startPoint]);

  // Rover Heading Angle calculation from path tangent
  const roverHeading = useMemo(() => {
    if (!activePath || activePath.length < 2) return 0;
    const maxIdx = activePath.length - 1;
    const clampedProgress = Math.max(0, Math.min(maxIdx, roverProgress));
    const k = Math.min(maxIdx - 1, Math.floor(clampedProgress));
    const p0 = activePath[k];
    const p1 = activePath[k + 1];
    return Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
  }, [activePath, roverProgress]);

  // Live continuous elevation
  const currentElevation = useMemo(() => {
    if (!dem?.elevation || !roverCoord) return 0;
    return bilinearElevation(roverCoord[0], roverCoord[1], dem.elevation, dem.rows, dem.cols);
  }, [dem, roverCoord]);

  // Distance metrics
  const totalDistance = effectiveNavigation?.[activeRoute]?.metrics?.total_distance ?? 0;
  const pathLength = activePath.length;
  const maxIdx = Math.max(1, pathLength - 1);
  const progressPct = Math.min(100, Math.round((roverProgress / maxIdx) * 100));
  const distanceTravelled = (totalDistance * (progressPct / 100)).toFixed(1);

  // High-level Navigation Status
  const navStatus = useMemo(() => {
    if (!startPoint) return 'SELECT_START';
    if (!destinationPoint) return 'SELECT_GOAL';
    if (loading) return 'CALCULATING';
    if (!effectiveNavigation?.[activeRoute]?.route?.success) return 'BLOCKED';
    if (isPlaying) return 'NAVIGATING';
    if (roverProgress > 0 && roverProgress < activePath.length - 1) return 'PAUSED';
    if (roverProgress >= activePath.length - 1 && activePath.length > 1) return 'ARRIVED';
    return 'READY';
  }, [
    startPoint,
    destinationPoint,
    loading,
    effectiveNavigation,
    activeRoute,
    isPlaying,
    roverProgress,
    activePath,
  ]);

  // Handlers for Terrain Interaction
  const handleSelectStart = useCallback((row, col) => {
    setStartPoint([row, col]);
    setIsPlaying(false);
    setRoverProgress(0);
    setCustomCostMap(null);
    setCustomNavigation(null);
    setRerouteAlert(null);
    setSelectionMode('auto');
  }, []);

  const handleSelectDestination = useCallback((row, col) => {
    setDestinationPoint([row, col]);
    setIsPlaying(false);
    setRoverProgress(0);
    setCustomCostMap(null);
    setCustomNavigation(null);
    setRerouteAlert(null);
    setSelectionMode('auto');
  }, []);

  const handleResetPoints = useCallback(() => {
    setStartPoint(null);
    setDestinationPoint(null);
    setIsPlaying(false);
    setRoverProgress(0);
    setCustomCostMap(null);
    setCustomNavigation(null);
    setRerouteAlert(null);
    setSelectionMode('start');
  }, []);

  // Handlers for Rover Traversal Controls
  const handlePlay = useCallback(() => {
    if (!effectiveNavigation?.[activeRoute]?.route?.success) return;
    setIsPlaying(true);
  }, [effectiveNavigation, activeRoute]);

  const handlePause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const handleResume = useCallback(() => {
    if (!effectiveNavigation?.[activeRoute]?.route?.success) return;
    setIsPlaying(true);
  }, [effectiveNavigation, activeRoute]);

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

  // Dynamic Hazard Injection & Real-Time Mid-Course Rerouting
  const handleInjectHazard = useCallback(
    async (type, r, c) => {
      if (!effectiveCostMap?.cost) return;

      const rows = effectiveCostMap.rows;
      const cols = effectiveCostMap.cols;
      const clonedCost = effectiveCostMap.cost.map((rowArr) => [...rowArr]);

      const radius = 6;
      const costValue = type === 'vortex' ? 4.5 : Infinity;

      for (let dr = -radius; dr <= radius; dr++) {
        for (let dc = -radius; dc <= radius; dc++) {
          if (dr * dr + dc * dc <= radius * radius) {
            const nr = r + dr;
            const nc = c + dc;
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
              clonedCost[nr][nc] = costValue;
            }
          }
        }
      }

      const updatedCostMap = {
        ...effectiveCostMap,
        cost: clonedCost,
      };
      setCustomCostMap(updatedCostMap);

      const curR = Math.max(0, Math.min(rows - 1, Math.round(roverCoord[0])));
      const curC = Math.max(0, Math.min(cols - 1, Math.round(roverCoord[1])));
      const goal = destinationPoint || [rows - 15, cols - 15];

      try {
        const rerouteRes = await compareRoutes([curR, curC], goal, clonedCost);
        if (rerouteRes) {
          const currentPath = effectiveNavigation?.[activeRoute]?.route?.path || [];
          const curIdx = Math.floor(roverProgress);
          const traveledPrefix = currentPath.slice(0, Math.max(0, curIdx));

          const newSafest = rerouteRes.safest?.route?.path || [];
          const newShortest = rerouteRes.shortest?.route?.path || [];

          const splicedSafest = [...traveledPrefix, ...newSafest];
          const splicedShortest = [...traveledPrefix, ...newShortest];

          const splicedNavigation = {
            ...rerouteRes,
            safest: {
              ...rerouteRes.safest,
              route: {
                ...rerouteRes.safest.route,
                path: splicedSafest,
                smoothed_x: rerouteRes.safest.route?.smoothed_x,
                smoothed_y: rerouteRes.safest.route?.smoothed_y,
              },
            },
            shortest: {
              ...rerouteRes.shortest,
              route: {
                ...rerouteRes.shortest.route,
                path: splicedShortest,
                smoothed_x: rerouteRes.shortest.route?.smoothed_x,
                smoothed_y: rerouteRes.shortest.route?.smoothed_y,
              },
            },
          };

          setCustomNavigation(splicedNavigation);
          setRerouteAlert({
            message: `DYNAMIC REROUTE: Avoided ${type.toUpperCase()} at (${r}, ${c}). New trajectory armed!`,
            timestamp: Date.now(),
          });
          setTimeout(() => setRerouteAlert(null), 6500);
        }
      } catch (err) {
        console.error('Dynamic mid-course reroute error:', err);
      }
    },
    [effectiveCostMap, roverCoord, destinationPoint, effectiveNavigation, activeRoute, roverProgress]
  );

  return (
    <div className="mc-container">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 0. CLASSIFIED ENTRY TERMINAL LANDING PAGE                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      {showTerminal && (
        <AresTerminalLanding onInitiate={() => setShowTerminal(false)} />
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. TOP COMMAND TELEMETRY BAR (36px height)                    */}
      {/* ───────────────────────────────────────────────────────────── */}
      <header className="mc-top-bar">
        {/* Left: Branding & System State */}
        <div className="mc-brand-area">
          <AresLogo size={22} showText={false} />
          <div className="mc-title">A.R.E.S. MARS-09 // KERNEL</div>
          <button
            onClick={() => setShowTerminal(true)}
            className="mc-btn"
            style={{ padding: '1px 6px', fontSize: '9px', color: '#858585', border: '1px solid #333333' }}
            title="Open Classified Entry Terminal Dossier"
          >
            [ DOSSIER ]
          </button>
          <span
            style={{
              fontSize: '9px',
              fontFamily: 'var(--font-mono)',
              padding: '1px 6px',
              border: `1px solid ${environmentalData.seismicAlert !== 'NOMINAL' ? '#DC2626' : '#0284C7'}`,
              background: '#161616',
              color: environmentalData.seismicAlert !== 'NOMINAL' ? '#DC2626' : '#0284C7',
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
            <Wind size={11} color="#0284C7" />
            <span>
              WIND: {environmentalData.windSpeedMs} m/s {environmentalData.windHeading}
            </span>
          </div>
          <div className="mc-env-item">
            <Flame size={11} color="#D97706" />
            <span>THERMAL: {environmentalData.thermalFluxKw} kW/m²</span>
          </div>
          <div className="mc-env-item" style={{ color: 'var(--text-muted)' }}>
            <span>OPTICAL DEPTH: {environmentalData.opticalDepth} τ</span>
          </div>
          <div className="mc-env-item">
            <span>
              PITCH: {environmentalData.roverPitch}° | ROLL: {environmentalData.roverRoll}°
            </span>
          </div>
        </div>

        {/* Right: Viewport Mode Switcher & Telemetry Health */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="mc-view-switcher">
            <button
              className={`mc-view-btn ${activeView === 'tactical' ? 'active' : ''}`}
              onClick={() => setActiveView('tactical')}
            >
              3D WIREFRAME SIM
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
              <Camera size={10} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              VISIONSCORE
            </button>
          </div>

          <StatusChip status={loading ? 'INITIALIZING' : error ? 'OFFLINE' : navStatus} />
        </div>
      </header>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. FULL-BLEED 100VW × 100VH VIEWPORT                          */}
      {/* ───────────────────────────────────────────────────────────── */}
      {activeView === 'visionscore' ? (
        <main
          className="mc-viewport-area"
          style={{ top: '36px', height: 'calc(100vh - 36px)', overflow: 'hidden' }}
        >
          <ErrorBoundary fallbackTitle="VisionScore Subsystem Failure">
            <VisionScoreDashboard />
          </ErrorBoundary>
        </main>
      ) : (
        <>
          <main className="mc-viewport-area">
            {loading && !dem ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  gap: '12px',
                }}
              >
                <div
                  className="mono"
                  style={{ color: '#D4D4D4', fontSize: '11px', letterSpacing: '0.14em' }}
                >
                  INGESTING 200×200 MARTIAN TOPOGRAPHY & WIREFRAME MATRIX...
                </div>
                <div
                  style={{
                    width: '180px',
                    height: '2px',
                    background: '#333333',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: '50%',
                      height: '100%',
                      background: '#0284C7',
                    }}
                  />
                </div>
              </div>
            ) : error ? (
              <div
                style={{
                  position: 'absolute',
                  top: '50px',
                  left: '20px',
                  zIndex: 100,
                  maxWidth: '450px',
                }}
              >
                <ErrorBanner error={error} onRetry={reload} />
              </div>
            ) : !dem ? (
              <EmptyState
                title="Elevation data not supplied"
                message="Upload or connect a DEM source to visualize Martian geological features."
                icon={Database}
              />
            ) : activeView === 'tactical' ? (
              /* A.R.E.S. BRUTALIST THREE.JS TACTICAL SIM WITH WIREFRAME TERRAIN & GEOMETRIC PRIMITIVES */
              <ErrorBoundary fallbackTitle="A.R.E.S. Tactical Viewport Error">
                <TerrainThreeMap
                  dem={dem}
                  costMap={effectiveCostMap}
                  navigation={effectiveNavigation}
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
                  toolMode={toolMode}
                  onInjectHazard={handleInjectHazard}
                  onCameraUpdate={setCameraState}
                  focusTarget={focusTarget}
                  simSpeed={simSpeed}
                />
              </ErrorBoundary>
            ) : (
              /* PLOTLY TOPOGRAPHIC CONTOUR VIEW */
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
                    costMap={effectiveCostMap}
                    navigation={effectiveNavigation}
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
          {/* 3. FLOATING LEFT TACTICAL STACK                               */}
          {/* Houses Radar, Artificial Horizon, and Metrics in strict 1px   */}
          {/* grid lines                                                    */}
          {/* ───────────────────────────────────────────────────────────── */}
          <aside className="mc-left-stack">
            <InteractiveRoverHUD
              startPoint={startPoint}
              destinationPoint={destinationPoint}
              onResetPoints={handleResetPoints}
              onSetSelectionMode={setSelectionMode}
              selectionMode={selectionMode}
              navigation={effectiveNavigation}
              activeRoute={activeRoute}
              onSelectRoute={handleSelectRoute}
              navStatus={navStatus}
              cameraMode={cameraMode}
              onSetCameraMode={setCameraMode}
              environmentalData={environmentalData}
              toolMode={toolMode}
              onSetToolMode={setToolMode}
              rerouteAlert={rerouteAlert}
              dem={dem}
              costMap={effectiveCostMap}
              roverCoord={roverCoord}
              roverHeading={roverHeading}
              cameraState={cameraState}
              onFocusLocation={(r, c) => setFocusTarget({ row: r, col: c })}
            />
          </aside>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 4. FLOATING RIGHT STATUS & LEGEND CORNER                      */}
          {/* ───────────────────────────────────────────────────────────── */}
          <div className="mc-floating-status tactical-panel">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '1px solid #333333',
                paddingBottom: '4px',
              }}
            >
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  color: '#858585',
                  letterSpacing: '0.08em',
                }}
              >
                A.R.E.S. MAP LEGEND
              </span>
              <div
                style={{
                  display: 'flex',
                  gap: '6px',
                  fontSize: '9px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span style={{ color: integrity.demLoaded ? '#0284C7' : '#DC2626' }}>
                  DEM ✓
                </span>
                <span style={{ color: integrity.costMapLoaded ? '#0284C7' : '#DC2626' }}>
                  COST ✓
                </span>
                <span style={{ color: integrity.routeLoaded ? '#0284C7' : '#DC2626' }}>
                  NAV ✓
                </span>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '4px',
                fontSize: '9px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    background: '#0284C7',
                    display: 'inline-block',
                    border: '1px solid #D4D4D4',
                  }}
                />
                <span>START [SKY BLUE]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    background: '#D97706',
                    display: 'inline-block',
                    border: '1px solid #D4D4D4',
                  }}
                />
                <span>GOAL [AMBER]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    background: '#0284C7',
                    display: 'inline-block',
                  }}
                />
                <span>SAFEST ROUTE</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    background: '#DC2626',
                    display: 'inline-block',
                  }}
                />
                <span>SHORTEST ROUTE</span>
              </div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  gridColumn: 'span 2',
                }}
              >
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    background: '#DC2626',
                    display: 'inline-block',
                  }}
                />
                <span>IMPASSABLE HAZARD (INF)</span>
              </div>
            </div>

            {/* Hover Coordinate Readout */}
            <div
              style={{
                marginTop: '4px',
                borderTop: '1px solid #333333',
                paddingTop: '4px',
                fontSize: '9px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {hoveredCell ? (
                <span style={{ color: '#858585' }}>
                  CURSOR: ({hoveredCell.row}, {hoveredCell.col}) ·{' '}
                  <span style={{ color: '#D4D4D4' }}>
                    {hoveredCell.elevation?.toFixed(1)} m
                  </span>{' '}
                  ·{' '}
                  <span
                    style={{
                      color:
                        hoveredCell.cost >= 9999
                          ? '#DC2626'
                          : hoveredCell.cost > 2.0
                          ? '#D97706'
                          : '#0284C7',
                      fontWeight: 600,
                    }}
                  >
                    {hoveredCell.cost >= 9999
                      ? 'HAZARD (BLOCKED)'
                      : hoveredCell.cost > 2.0
                      ? `CAUTION (${hoveredCell.cost.toFixed(1)})`
                      : 'SAFE'}
                  </span>
                </span>
              ) : (
                <span style={{ color: '#555555' }}>
                  Hover over wireframe mesh to inspect terrain
                </span>
              )}
            </div>
          </div>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 5. FLOATING BOTTOM MISSION TIMELINE & ELEVATION TRANSECT DOCK */}
          {/* ───────────────────────────────────────────────────────────── */}
          <footer className="mc-bottom-dock tactical-panel">
            {/* Left: Transport Cluster & Speed Controls */}
            <div className="mc-transport-cluster">
              <div className="mc-btn-group">
                {!isPlaying ? (
                  <button
                    className="mc-tactical-btn active"
                    disabled={!effectiveNavigation?.[activeRoute]?.route?.success || pathLength === 0}
                    onClick={roverProgress > 0 && roverProgress < maxIdx ? handleResume : handlePlay}
                  >
                    <Play size={11} fill="#121212" />
                    <span>{roverProgress > 0 && roverProgress < maxIdx ? 'RESUME' : 'PLAY'}</span>
                  </button>
                ) : (
                  <button
                    className="mc-tactical-btn"
                    onClick={handlePause}
                    style={{ color: '#D97706', borderColor: '#D97706' }}
                  >
                    <Pause size={11} />
                    <span>PAUSE</span>
                  </button>
                )}

                <button
                  className="mc-tactical-btn"
                  disabled={roverProgress === 0 && !isPlaying}
                  onClick={handleResetRover}
                >
                  <RotateCcw size={10} />
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

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '9px',
                  fontFamily: 'var(--font-mono)',
                  color: '#858585',
                }}
              >
                <span>PROGRESS:</span>
                <div
                  style={{
                    flex: 1,
                    height: '3px',
                    background: '#222222',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${progressPct}%`,
                      background: activeRoute === 'safest' ? '#0284C7' : '#DC2626',
                    }}
                  />
                </div>
                <span style={{ fontWeight: 700, color: '#D4D4D4' }}>
                  {progressPct}%
                </span>
              </div>
            </div>

            {/* Center: Live SVG Elevation Profile Transect */}
            <div className="mc-transect-box">
              <ElevationProfileChart
                path={activePath}
                elevation={dem?.elevation}
                costMap={effectiveCostMap}
                roverProgress={roverProgress}
                totalDistance={totalDistance}
                activeRoute={activeRoute}
              />
            </div>

            {/* Right: Live Rover Telemetry Coordinates */}
            <div className="mc-bottom-dock-right">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#858585' }}>COORDINATES:</span>
                <span style={{ color: '#0284C7', fontWeight: 600 }}>
                  ({roverCoord[0].toFixed(1)}, {roverCoord[1].toFixed(1)})
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#858585' }}>SURFACE ALT:</span>
                <span style={{ fontWeight: 600, color: '#D4D4D4' }}>{currentElevation.toFixed(1)} m</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#858585' }}>TRAVERSE:</span>
                <span>
                  {distanceTravelled} / {totalDistance.toFixed(1)} m
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#858585' }}>WAYPOINT:</span>
                <span>
                  {Math.min(pathLength, Math.floor(roverProgress) + 1)} / {pathLength || 0}
                </span>
              </div>
            </div>
          </footer>
        </>
      )}
    </div>
  );
}
