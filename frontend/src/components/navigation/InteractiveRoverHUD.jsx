import React from 'react';
import {
  Compass,
  Shield,
  Zap,
  Crosshair,
  Mountain,
  Wind,
  Flame,
  AlertTriangle,
} from 'lucide-react';
import ArtificialHorizon from './ArtificialHorizon';
import RadarMinimap from './RadarMinimap';

/**
 * A.R.E.S. Interactive Rover Tactical HUD
 * Strict Utilitarian Aerospace / Brutalist Aesthetics:
 * 1. Strict 1px grid lines separating Radar, Artificial Horizon, and Metrics panels.
 * 2. Telemetry UI: Render the "Shortest vs. Safest" metrics as a literal HTML <table> with visible borders.
 * 3. Zero curves, zero gradients, zero shadows.
 */
export default function InteractiveRoverHUD({
  startPoint,
  destinationPoint,
  onResetPoints,
  onSetSelectionMode,
  selectionMode,
  navigation,
  activeRoute,
  onSelectRoute,
  navStatus,
  cameraMode,
  onSetCameraMode,
  environmentalData,
  toolMode = 'nav',
  onSetToolMode,
  rerouteAlert,
  dem,
  costMap,
  roverCoord,
  roverHeading,
  cameraState,
  onFocusLocation,
}) {
  const currentRouteData = navigation?.[activeRoute];
  const routeSuccess = currentRouteData?.route?.success ?? false;
  const failureReason = currentRouteData?.route?.reason || null;
  const summary = navigation?.summary;

  const safestMetrics = navigation?.safest?.metrics;
  const shortestMetrics = navigation?.shortest?.metrics;

  return (
    <div
      style={{
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        background: '#121212',
        color: '#D4D4D4',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      {/* 1. Tactical Directives Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #333333',
          paddingBottom: '5px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#D4D4D4',
          }}
        >
          <Compass size={13} color="#0284C7" />
          <span>A.R.E.S. DIRECTIVE</span>
        </div>
        <span
          style={{
            fontSize: '9px',
            border: `1px solid ${navStatus === 'NAVIGATING' ? '#0284C7' : '#333333'}`,
            padding: '1px 5px',
            background: navStatus === 'NAVIGATING' ? '#0284C7' : '#181818',
            color: navStatus === 'NAVIGATING' ? '#121212' : '#858585',
            fontWeight: 700,
            letterSpacing: '0.06em',
          }}
        >
          {navStatus}
        </span>
      </div>

      {/* Dynamic Mid-Course Reroute Alert Banner */}
      {rerouteAlert && (
        <div
          style={{
            background: '#1c1505',
            border: '1px solid #D97706',
            padding: '5px 8px',
            fontSize: '10px',
            color: '#D97706',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <AlertTriangle size={13} color="#D97706" />
          <span style={{ fontWeight: 600 }}>{rerouteAlert.message}</span>
        </div>
      )}

      {/* Status Directive Text */}
      <div
        style={{
          fontSize: '10px',
          color: '#858585',
          lineHeight: 1.35,
          borderLeft: '2px solid #555555',
          paddingLeft: '6px',
        }}
      >
        {toolMode !== 'nav' ? (
          <span style={{ color: '#D97706' }}>
            [HAZARD INJECT]: CLICK 3D TERRAIN TO INJECT {toolMode.toUpperCase()} & FORCE REROUTE.
          </span>
        ) : !startPoint ? (
          <span style={{ color: '#0284C7' }}>
            [STEP 1/3] CLICK TERRAIN TO DROP START WAYPOINT [SKY BLUE]
          </span>
        ) : !destinationPoint ? (
          <span style={{ color: '#D97706' }}>
            [STEP 2/3] CLICK TERRAIN TO DROP GOAL WAYPOINT [AMBER]
          </span>
        ) : !routeSuccess ? (
          <span style={{ color: '#DC2626' }}>
            [BLOCKED] {failureReason || 'Target unreachable due to impassable hazard barrier.'}
          </span>
        ) : (
          <span style={{ color: '#0284C7' }}>
            [STEP 3/3] TRAJECTORY VERIFIED. SELECT MODE & INITIATE TRAVERSAL.
          </span>
        )}
      </div>

      {/* 2. Terrain Interaction & Hazard Injection Modes */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        <div style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em' }}>
          TERRAIN INGESTION & INTERACTION
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0', border: '1px solid #333333' }}>
          <button
            className={`mc-camera-btn ${toolMode === 'nav' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('nav')}
            style={{ borderRight: '1px solid #333333', borderBottom: '1px solid #333333' }}
          >
            <Crosshair size={10} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            NAV SELECT
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'landslide' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('landslide')}
            style={{ borderBottom: '1px solid #333333' }}
          >
            <Mountain size={10} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            LANDSLIDE
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'vortex' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('vortex')}
            style={{ borderRight: '1px solid #333333' }}
          >
            <Wind size={10} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            DUST VORTEX
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'fissure' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('fissure')}
          >
            <Flame size={10} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            ERUPT FISSURE
          </button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. STRICT BRUTALIST 1PX GRID INSTRUMENTS CLUSTER             */}
      {/* Separates Radar, Artificial Horizon, and Metrics with strict  */}
      {/* 1px grid lines                                               */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div
        style={{
          border: '1px solid #333333',
          background: '#121212',
          display: 'flex',
          flexDirection: 'column',
          marginTop: '2px',
        }}
      >
        {/* PANEL 1: RADAR MINIMAP (Bordered with 1px grid line) */}
        <div style={{ borderBottom: '1px solid #333333', padding: '6px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em', fontWeight: 600 }}>
              PANEL 1 // RADAR MINIMAP
            </span>
            <span style={{ fontSize: '8px', color: '#858585' }}>
              {dem ? `${dem.cols}×${dem.rows}` : 'INGESTING'}
            </span>
          </div>
          <RadarMinimap
            dem={dem}
            costMap={costMap}
            navigation={navigation}
            roverCoord={roverCoord}
            roverHeading={roverHeading}
            startPoint={startPoint}
            destinationPoint={destinationPoint}
            cameraPos={cameraState?.pos}
            cameraTarget={cameraState?.target}
            onFocusLocation={onFocusLocation || (() => {})}
            width={306}
            height={130}
          />
        </div>

        {/* PANEL 2: ARTIFICIAL HORIZON (Bordered with 1px grid line) */}
        <div style={{ borderBottom: '1px solid #333333', padding: '6px' }}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em', fontWeight: 600 }}>
              PANEL 2 // ARTIFICIAL HORIZON
            </span>
            <span style={{ fontSize: '8px', color: '#858585' }}>
              STABILITY SENSOR
            </span>
          </div>
          <ArtificialHorizon
            pitchDeg={environmentalData?.roverPitch ?? 0}
            rollDeg={environmentalData?.roverRoll ?? 0}
          />
        </div>

        {/* PANEL 3: METRICS TABLE (Shortest vs. Safest literal HTML <table> with visible borders) */}
        <div style={{ padding: '6px' }}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em', fontWeight: 600 }}>
              PANEL 3 // TRAJECTORY COMPARISON MATRIX
            </span>
            <div style={{ display: 'flex', gap: '3px' }}>
              <button
                onClick={() => onSelectRoute('safest')}
                disabled={!navigation?.safest?.route?.success}
                style={{
                  fontSize: '8px',
                  padding: '1px 5px',
                  border: `1px solid ${activeRoute === 'safest' ? '#0284C7' : '#333333'}`,
                  background: activeRoute === 'safest' ? '#0284C7' : '#161616',
                  color: activeRoute === 'safest' ? '#121212' : '#858585',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                SAFEST
              </button>
              <button
                onClick={() => onSelectRoute('shortest')}
                disabled={!navigation?.shortest?.route?.success}
                style={{
                  fontSize: '8px',
                  padding: '1px 5px',
                  border: `1px solid ${activeRoute === 'shortest' ? '#DC2626' : '#333333'}`,
                  background: activeRoute === 'shortest' ? '#DC2626' : '#161616',
                  color: activeRoute === 'shortest' ? '#FFFFFF' : '#858585',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                SHORTEST
              </button>
            </div>
          </div>

          {/* Literal HTML <table> with visible 1px borders */}
          <table
            className="mc-matrix-table"
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '1px solid #333333',
              fontSize: '10px',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <thead>
              <tr style={{ background: '#181818' }}>
                <th style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'left', color: '#858585' }}>
                  PARAMETER
                </th>
                <th style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#0284C7' }}>
                  SAFEST
                </th>
                <th style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#DC2626' }}>
                  SHORTEST
                </th>
                <th style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D4D4D4' }}>
                  DELTA
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', color: '#858585' }}>Distance</td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D4D4D4' }}>
                  {safestMetrics?.total_distance ? `${safestMetrics.total_distance.toFixed(1)}m` : '—'}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D4D4D4' }}>
                  {shortestMetrics?.total_distance ? `${shortestMetrics.total_distance.toFixed(1)}m` : '—'}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D97706' }}>
                  +{summary?.distance_penalty_pct ? summary.distance_penalty_pct.toFixed(1) : '0.0'}%
                </td>
              </tr>
              <tr>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', color: '#858585' }}>Risk Cost</td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#0284C7', fontWeight: 600 }}>
                  {safestMetrics?.total_cost ? safestMetrics.total_cost.toFixed(1) : '—'}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#DC2626', fontWeight: 600 }}>
                  {shortestMetrics?.total_cost ? shortestMetrics.total_cost.toFixed(1) : '—'}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#0284C7' }}>
                  -{summary?.cost_reduction_pct ? summary.cost_reduction_pct.toFixed(1) : '0.0'}%
                </td>
              </tr>
              <tr>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', color: '#858585' }}>Caution Cells</td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#0284C7' }}>
                  {safestMetrics?.caution_steps ?? 0}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D97706' }}>
                  {shortestMetrics?.caution_steps ?? 0}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#0284C7' }}>
                  -{summary?.caution_steps_avoided ?? 0}
                </td>
              </tr>
              <tr>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', color: '#858585' }}>Waypoints</td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D4D4D4' }}>
                  {safestMetrics?.step_count ?? 0}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#D4D4D4' }}>
                  {shortestMetrics?.step_count ?? 0}
                </td>
                <td style={{ border: '1px solid #333333', padding: '4px 6px', textAlign: 'right', color: '#858585' }}>
                  {safestMetrics?.step_count && shortestMetrics?.step_count
                    ? safestMetrics.step_count - shortestMetrics.step_count
                    : 0}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Tactical Camera Mode Selector */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        <div style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em' }}>
          CAMERA CONTROL
        </div>
        <div className="mc-camera-modes">
          <button
            className={`mc-camera-btn ${cameraMode === 'ORBIT' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('ORBIT')}
          >
            ORBIT
          </button>
          <button
            className={`mc-camera-btn ${cameraMode === 'ROVER_CHASE' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('ROVER_CHASE')}
          >
            CHASE CAM
          </button>
          <button
            className={`mc-camera-btn ${cameraMode === 'MASTCAM_POV' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('MASTCAM_POV')}
          >
            MASTCAM POV
          </button>
        </div>
      </div>

      {/* 5. Start & Goal Coordinates */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
        <div
          style={{
            background: '#161616',
            border: `1px solid ${selectionMode === 'start' ? '#0284C7' : '#333333'}`,
            padding: '5px 6px',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '9px', color: '#0284C7', fontWeight: 700 }}>
              START [SKY BLUE]
            </span>
            <button
              onClick={() => onSetSelectionMode(selectionMode === 'start' ? 'auto' : 'start')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#858585',
                fontSize: '8px',
                cursor: 'pointer',
              }}
            >
              {selectionMode === 'start' ? '[PICKING]' : '[RE-PICK]'}
            </button>
          </div>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#D4D4D4' }}>
            {startPoint ? `(${startPoint[0]}, ${startPoint[1]})` : 'NOT SET'}
          </span>
        </div>

        <div
          style={{
            background: '#161616',
            border: `1px solid ${selectionMode === 'destination' ? '#D97706' : '#333333'}`,
            padding: '5px 6px',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '9px', color: '#D97706', fontWeight: 700 }}>
              GOAL [AMBER]
            </span>
            <button
              onClick={() => onSetSelectionMode(selectionMode === 'destination' ? 'auto' : 'destination')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#858585',
                fontSize: '8px',
                cursor: 'pointer',
              }}
            >
              {selectionMode === 'destination' ? '[PICKING]' : '[RE-PICK]'}
            </button>
          </div>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#D4D4D4' }}>
            {destinationPoint ? `(${destinationPoint[0]}, ${destinationPoint[1]})` : 'NOT SET'}
          </span>
        </div>
      </div>

      {/* Clear Waypoints */}
      {(startPoint || destinationPoint) && (
        <button
          onClick={onResetPoints}
          className="mc-btn"
          style={{ width: '100%', padding: '4px', fontSize: '9px', color: '#858585' }}
        >
          [ RESET WAYPOINT PINS ]
        </button>
      )}
    </div>
  );
}
