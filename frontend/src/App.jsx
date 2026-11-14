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
  AlertTriangle,
} from 'lucide-react';

import TerrainThreeMap from './components/three/TerrainThreeMap';
import InteractiveRoverHUD from './components/navigation/InteractiveRoverHUD';
import RadarMinimap from './components/navigation/RadarMinimap';
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
import { compareRoutes } from './api/client';

export default function App() {
  // 1. Interactive Marker Endpoints (Cyan Start & Amber Destination)
  const [startPoint, setStartPoint] = useState([15, 15]);
  const [destinationPoint, setDestinationPoint] = useState([185, 185]);
  const [selectionMode, setSelectionMode] = useState('auto'); // 'auto' | 'start' | 'destination'

  // 2. Trajectory Selection & Kinematics State
  const [activeRoute, setActiveRoute] = useState('safest'); // 'safest' (Green) | 'shortest' (Red)
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

  // 6. Environmental Danger Telemetry (Wind, Thermal Magma, Seismic, Inclinometer)
  const [environmentalData, setEnvironmentalData] = useState({
    windSpeedMs: '28.4',
    windHeading: 'WNW (285°)',
    thermalFluxKw: '4.8',
    seismicAlert: 'NOMINAL',
    opticalDepth: '0.82',
    roverPitch: '1.8',
    roverRoll: '-0.9',
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
    if (!destinationPoint) return 'SELECT_DESTINATION';
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

  // ─────────────────────────────────────────────────────────────
  // Dynamic Hazard Injection & Real-Time Mid-Course Rerouting
  // ─────────────────────────────────────────────────────────────
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

      // Rover's current continuous grid coordinate
      const curR = Math.max(0, Math.min(rows - 1, Math.round(roverCoord[0])));
      const curC = Math.max(0, Math.min(cols - 1, Math.round(roverCoord[1])));
      const goal = destinationPoint || [rows - 15, cols - 15];

      try {
        const rerouteRes = await compareRoutes([curR, curC], goal, clonedCost);
        if (rerouteRes) {
          // Splice path: retain traveled steps up to curR, curC and append new path forward
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
              },
            },
            shortest: {
              ...rerouteRes.shortest,
              route: {
                ...rerouteRes.shortest.route,
                path: splicedShortest,
              },
            },
          };

          setCustomNavigation(splicedNavigation);
          setRerouteAlert({
            message: `DYNAMIC REROUTE: Avoided ${type.toUpperCase()} at (${r}, ${c}). Safe trajectory engaged!`,
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
              background:
                environmentalData.seismicAlert !== 'NOMINAL'
                  ? 'rgba(239, 68, 68, 0.25)'
                  : 'rgba(16, 185, 129, 0.2)',
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
            <span>
              WIND: {environmentalData.windSpeedMs} m/s {environmentalData.windHeading}
            </span>
          </div>
          <div className="mc-env-item">
            <Flame size={12} color="#f97316" />
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
        <main
          className="mc-viewport-area"
          style={{ top: '38px', height: 'calc(100vh - 38px)', overflow: 'hidden' }}
        >
          <ErrorBoundary fallbackTitle="VisionScore 2.0 Subsystem Failure">
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
                  style={{ color: 'var(--rover)', fontSize: '12px', letterSpacing: '0.12em' }}
                >
                  INGESTING 200×200 MARTIAN TOPOGRAPHY & MULTI-HAZARD MESH...
                </div>
                <div
                  style={{
                    width: '180px',
                    height: '2px',
                    background: 'rgba(255,255,255,0.1)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: '50%',
                      height: '100%',
                      background: 'var(--rover)',
                      animation: 'status-blink 1s infinite alternate',
                    }}
                  />
                </div>
              </div>
            ) : error ? (
              <div
                style={{
                  position: 'absolute',
                  top: '60px',
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
              /* BUTTER-SMOOTH THREE.JS TACTICAL SIM WITH MULTI-HAZARD 3D SYSTEM */
              <ErrorBoundary fallbackTitle="Three.js Tactical Viewport Error">
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
          {/* 3. FLOATING LEFT TACTICAL STACK (325px wide)                  */}
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
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                paddingBottom: '4px',
              }}
            >
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  letterSpacing: '0.08em',
                }}
              >
                MAP LEGEND & INTEGRITY
              </span>
              <div
                style={{
                  display: 'flex',
                  gap: '6px',
                  fontSize: '9px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span style={{ color: integrity.demLoaded ? 'var(--safe)' : 'var(--hazard)' }}>
                  DEM ✓
                </span>
                <span style={{ color: integrity.costMapLoaded ? 'var(--safe)' : 'var(--hazard)' }}>
                  COST ✓
                </span>
                <span style={{ color: integrity.routeLoaded ? 'var(--safe)' : 'var(--hazard)' }}>
                  NAV ✓
                </span>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '4px',
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    background: 'var(--rover)',
                    display: 'inline-block',
                  }}
                />
                <span>START [CYAN]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    background: 'var(--caution)',
                    display: 'inline-block',
                  }}
                />
                <span>GOAL [AMBER]</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    background: 'var(--safe)',
                    display: 'inline-block',
                  }}
                />
                <span>SAFEST ROUTE</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    background: 'var(--hazard)',
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
                    width: '8px',
                    height: '8px',
                    background: '#ff3700',
                    display: 'inline-block',
                  }}
                />
                <span>VOLCANIC MAGMA VEIN (INF)</span>
              </div>
            </div>

            {/* Hover Coordinate Readout */}
            <div
              style={{
                marginTop: '4px',
                borderTop: '1px solid rgba(255,255,255,0.06)',
                paddingTop: '4px',
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {hoveredCell ? (
                <span style={{ color: 'var(--text-secondary)' }}>
                  CURSOR: ({hoveredCell.row}, {hoveredCell.col}) ·{' '}
                  <span style={{ color: 'var(--text-primary)' }}>
                    {hoveredCell.elevation?.toFixed(1)} m
                  </span>{' '}
                  ·{' '}
                  <span
                    style={{
                      color:
                        hoveredCell.cost >= 9999
                          ? 'var(--hazard)'
                          : hoveredCell.cost > 2.0
                          ? 'var(--caution)'
                          : 'var(--safe)',
                    }}
                  >
                    {hoveredCell.cost >= 9999
                      ? 'VOLCANIC HAZARD'
                      : hoveredCell.cost > 2.0
                      ? `CAUTION (${hoveredCell.cost.toFixed(1)})`
                      : 'SAFE'}
                  </span>
                </span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>
                  Hover over terrain mesh to inspect geology
                </span>
              )}
            </div>
          </div>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 5. 2D TACTICAL RADAR MINIMAP (Anchored in bottom-right)       */}
          {/* ───────────────────────────────────────────────────────────── */}
          <div
            style={{
              position: 'absolute',
              right: '14px',
              bottom: '124px',
              zIndex: 30,
              pointerEvents: 'auto',
            }}
          >
            <RadarMinimap
              dem={dem}
              costMap={effectiveCostMap}
              navigation={effectiveNavigation}
              roverCoord={roverCoord}
              roverHeading={roverHeading}
              startPoint={startPoint}
              destinationPoint={destinationPoint}
              cameraPos={cameraState.pos}
              cameraTarget={cameraState.target}
              onFocusLocation={(r, c) => setFocusTarget({ row: r, col: c })}
            />
          </div>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* 6. FLOATING BOTTOM MISSION TIMELINE & ELEVATION TRANSECT DOCK  */}
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
                    <Play size={12} fill="#06080d" />
                    <span>{roverProgress > 0 && roverProgress < maxIdx ? 'RESUME' : 'PLAY'}</span>
                  </button>
                ) : (
                  <button
                    className="mc-tactical-btn"
                    onClick={handlePause}
                    style={{ color: 'var(--caution)', borderColor: 'var(--caution)' }}
                  >
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

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                }}
              >
                <span>PROGRESS:</span>
                <div
                  style={{
                    flex: 1,
                    height: '4px',
                    background: 'rgba(255,255,255,0.1)',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${progressPct}%`,
                      background: activeRoute === 'safest' ? 'var(--safe)' : 'var(--hazard)',
                      transition: 'width 100ms linear',
                    }}
                  />
                </div>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
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

            {/* Right: Live Rover Waypoint & Altimeter Telemetry */}
            <div
              className="mc-bottom-dock-right"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '3px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
              }}
            >
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
                <span>
                  {distanceTravelled} / {totalDistance.toFixed(1)} m
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>WAYPOINT:</span>
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
