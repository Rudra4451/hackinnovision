import React from 'react';
import {
  Compass,
  Shield,
  Zap,
  RotateCcw,
  Camera,
  Eye,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Wind,
  Mountain,
  Crosshair,
} from 'lucide-react';
import ArtificialHorizon from './ArtificialHorizon';

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
}) {
  const currentRouteData = navigation?.[activeRoute];
  const routeSuccess = currentRouteData?.route?.success ?? false;
  const failureReason = currentRouteData?.route?.reason || null;
  const summary = navigation?.summary;

  const safestMetrics = navigation?.safest?.metrics;
  const shortestMetrics = navigation?.shortest?.metrics;

  return (
    <div
      className="tactical-panel"
      style={{
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      {/* 1. Tactical Directives & Mission State */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          paddingBottom: '6px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: 'var(--rover)',
          }}
        >
          <Compass size={12} />
          <span>TACTICAL DIRECTIVE</span>
        </div>
        <span
          style={{
            fontSize: '9px',
            fontFamily: 'var(--font-mono)',
            padding: '1px 5px',
            background:
              navStatus === 'NAVIGATING'
                ? 'rgba(6, 182, 212, 0.25)'
                : 'rgba(255,255,255,0.06)',
            color: navStatus === 'NAVIGATING' ? 'var(--rover)' : 'var(--text-secondary)',
            fontWeight: 700,
            letterSpacing: '0.05em',
          }}
        >
          {navStatus}
        </span>
      </div>

      {/* Dynamic Mid-Course Reroute Alert Banner */}
      {rerouteAlert && (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.2)',
            borderLeft: '3px solid var(--caution)',
            padding: '5px 8px',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: '#fef08a',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            animation: 'status-blink 1.5s infinite alternate',
          }}
        >
          <AlertTriangle size={13} color="var(--caution)" />
          <span>{rerouteAlert.message}</span>
        </div>
      )}

      <div
        style={{
          fontSize: '11px',
          color: 'var(--text-primary)',
          lineHeight: 1.35,
          fontFamily: 'var(--font-sans)',
        }}
      >
        {toolMode !== 'nav' ? (
          <span style={{ color: '#f97316' }}>
            [HAZARD INJECT MODE]: CLICK 3D TERRAIN TO INJECT{' '}
            <strong>{toolMode.toUpperCase()}</strong> AND TRIGGER REAL-TIME REROUTE.
          </span>
        ) : !startPoint ? (
          <span style={{ color: '#67e8f9' }}>
            [1/3] CLICK TERRAIN TO DROP <strong>START PIN (CYAN)</strong>
          </span>
        ) : !destinationPoint ? (
          <span style={{ color: '#fde047' }}>
            [2/3] CLICK TERRAIN TO DROP <strong>DESTINATION PIN (AMBER)</strong>
          </span>
        ) : !routeSuccess ? (
          <span style={{ color: 'var(--hazard)' }}>
            [BLOCKED] {failureReason || 'Target cell is in an impassable volcanic fissure.'}
          </span>
        ) : (
          <span style={{ color: 'var(--safe)' }}>
            [3/3] TRAJECTORY VERIFIED. SELECT ROUTE & ENGAGE PLAY.
          </span>
        )}
      </div>

      {/* 2. Interactive Tool Mode: Nav Pin Drop vs Live Hazard Injection */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div
          style={{
            fontSize: '9px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
          }}
        >
          TERRAIN INTERACTION & HAZARD INJECTION
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
          <button
            className={`mc-camera-btn ${toolMode === 'nav' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('nav')}
            title="Standard waypoint marker pin selection"
          >
            <Crosshair size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            NAV SELECT
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'landslide' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('landslide')}
            title="Inject Landslide Scarp on click + live reroute"
            style={{
              borderColor: toolMode === 'landslide' ? '#ea580c' : 'rgba(255,255,255,0.1)',
              color: toolMode === 'landslide' ? '#fdba74' : 'inherit',
            }}
          >
            <Mountain size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            LANDSLIDE
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'vortex' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('vortex')}
            title="Spawn Dust Vortex corridor on click + live reroute"
            style={{
              borderColor: toolMode === 'vortex' ? '#38bdf8' : 'rgba(255,255,255,0.1)',
              color: toolMode === 'vortex' ? '#7dd3fc' : 'inherit',
            }}
          >
            <Wind size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            DUST VORTEX
          </button>
          <button
            className={`mc-camera-btn ${toolMode === 'fissure' ? 'active' : ''}`}
            onClick={() => onSetToolMode && onSetToolMode('fissure')}
            title="Erupt Volcanic Magma Fissure on click + live reroute"
            style={{
              borderColor: toolMode === 'fissure' ? '#ef4444' : 'rgba(255,255,255,0.1)',
              color: toolMode === 'fissure' ? '#fca5a5' : 'inherit',
            }}
          >
            <Flame size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            ERUPT FISSURE
          </button>
        </div>
      </div>

      {/* 3. Artificial Horizon Inclinometer Widget */}
      <ArtificialHorizon
        pitchDeg={environmentalData?.roverPitch ?? 0}
        rollDeg={environmentalData?.roverRoll ?? 0}
      />

      {/* 4. Tactical Camera Modes (Orbit, Rover Chase, Mastcam POV) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div
          style={{
            fontSize: '9px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
          }}
        >
          CAMERA CONTROLLER
        </div>
        <div className="mc-camera-modes">
          <button
            className={`mc-camera-btn ${cameraMode === 'ORBIT' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('ORBIT')}
            title="Inspect terrain from orbit, click waypoints"
          >
            ORBIT
          </button>
          <button
            className={`mc-camera-btn ${cameraMode === 'ROVER_CHASE' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('ROVER_CHASE')}
            title="Follow rover from third-person chase camera"
          >
            CHASE CAM
          </button>
          <button
            className={`mc-camera-btn ${cameraMode === 'MASTCAM_POV' ? 'active' : ''}`}
            onClick={() => onSetCameraMode('MASTCAM_POV')}
            title="Lock camera to Rover's Mastcam optic head"
          >
            MASTCAM POV
          </button>
        </div>
      </div>

      {/* 5. Endpoint Coordinates Module */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
        <div
          style={{
            background: 'rgba(6, 182, 212, 0.05)',
            border:
              selectionMode === 'start'
                ? '1px solid var(--rover)'
                : '1px solid rgba(6, 182, 212, 0.2)',
            padding: '6px 8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '9px', color: 'var(--rover)', fontWeight: 700 }}>
              START [CYAN]
            </span>
            <button
              onClick={() => onSetSelectionMode(selectionMode === 'start' ? 'auto' : 'start')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '9px',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
              }}
            >
              {selectionMode === 'start' ? 'PICKING' : 'RE-PICK'}
            </button>
          </div>
          <span className="mono" style={{ fontSize: '11px', fontWeight: 600, color: '#a5f3fc' }}>
            {startPoint ? `(${startPoint[0]}, ${startPoint[1]})` : 'NOT SET'}
          </span>
        </div>

        <div
          style={{
            background: 'rgba(245, 158, 11, 0.05)',
            border:
              selectionMode === 'destination'
                ? '1px solid var(--caution)'
                : '1px solid rgba(245, 158, 11, 0.2)',
            padding: '6px 8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '9px', color: 'var(--caution)', fontWeight: 700 }}>
              GOAL [AMBER]
            </span>
            <button
              onClick={() =>
                onSetSelectionMode(selectionMode === 'destination' ? 'auto' : 'destination')
              }
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '9px',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
              }}
            >
              {selectionMode === 'destination' ? 'PICKING' : 'RE-PICK'}
            </button>
          </div>
          <span className="mono" style={{ fontSize: '11px', fontWeight: 600, color: '#fde68a' }}>
            {destinationPoint ? `(${destinationPoint[0]}, ${destinationPoint[1]})` : 'NOT SET'}
          </span>
        </div>
      </div>

      {/* 6. Dual-Route Tactical Selector & Delta Matrix */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span
            style={{
              fontSize: '9px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-muted)',
              letterSpacing: '0.08em',
            }}
          >
            TRAJECTORY SELECTOR
          </span>
          {(startPoint || destinationPoint) && (
            <button
              onClick={onResetPoints}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '9px',
                cursor: 'pointer',
              }}
            >
              [CLEAR PINS]
            </button>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
          <button
            onClick={() => onSelectRoute('safest')}
            disabled={!navigation?.safest?.route?.success}
            style={{
              padding: '6px 8px',
              border:
                activeRoute === 'safest'
                  ? '1px solid var(--safe)'
                  : '1px solid rgba(255,255,255,0.08)',
              background:
                activeRoute === 'safest'
                  ? 'rgba(16, 185, 129, 0.12)'
                  : 'rgba(255,255,255,0.02)',
              color: 'var(--text-primary)',
              cursor: navigation?.safest?.route?.success ? 'pointer' : 'not-allowed',
              textAlign: 'left',
              borderRadius: 0,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--safe)',
                fontWeight: 700,
                fontSize: '10px',
              }}
            >
              <Shield size={11} />
              <span>GREEN ROUTE</span>
            </div>
            <div className="mono" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
              {safestMetrics?.total_distance
                ? `${safestMetrics.total_distance.toFixed(1)} m`
                : '—'}
            </div>
          </button>

          <button
            onClick={() => onSelectRoute('shortest')}
            disabled={!navigation?.shortest?.route?.success}
            style={{
              padding: '6px 8px',
              border:
                activeRoute === 'shortest'
                  ? '1px solid var(--hazard)'
                  : '1px solid rgba(255,255,255,0.08)',
              background:
                activeRoute === 'shortest'
                  ? 'rgba(239, 68, 68, 0.12)'
                  : 'rgba(255,255,255,0.02)',
              color: 'var(--text-primary)',
              cursor: navigation?.shortest?.route?.success ? 'pointer' : 'not-allowed',
              textAlign: 'left',
              borderRadius: 0,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--hazard)',
                fontWeight: 700,
                fontSize: '10px',
              }}
            >
              <Zap size={11} />
              <span>RED ROUTE</span>
            </div>
            <div className="mono" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
              {shortestMetrics?.total_distance
                ? `${shortestMetrics.total_distance.toFixed(1)} m`
                : '—'}
            </div>
          </button>
        </div>

        {/* Compact Tabular Delta Matrix */}
        {safestMetrics && shortestMetrics && (
          <table className="mc-matrix-table" style={{ marginTop: '4px' }}>
            <thead>
              <tr>
                <th>METRIC</th>
                <th style={{ color: 'var(--safe)' }}>SAFEST</th>
                <th style={{ color: 'var(--hazard)' }}>SHORTEST</th>
                <th style={{ textAlign: 'right' }}>DELTA</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Distance</td>
                <td>{safestMetrics.total_distance?.toFixed(1)}m</td>
                <td>{shortestMetrics.total_distance?.toFixed(1)}m</td>
                <td
                  style={{
                    textAlign: 'right',
                    color:
                      summary?.distance_penalty_pct > 0
                        ? 'var(--caution)'
                        : 'var(--safe)',
                  }}
                >
                  +{summary?.distance_penalty_pct?.toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td>Risk Cost</td>
                <td style={{ color: 'var(--safe)' }}>
                  {safestMetrics.total_cost?.toFixed(1)}
                </td>
                <td>{shortestMetrics.total_cost?.toFixed(1)}</td>
                <td style={{ textAlign: 'right', color: 'var(--safe)' }}>
                  -{summary?.cost_reduction_pct?.toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td>Caution Steps</td>
                <td>{safestMetrics.caution_steps ?? 0}</td>
                <td>{shortestMetrics.caution_steps ?? 0}</td>
                <td style={{ textAlign: 'right', color: 'var(--safe)' }}>
                  -{summary?.caution_steps_avoided ?? 0}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* 7. Navigator Recommendation Box */}
      {summary?.recommendation && (
        <div
          style={{
            borderLeft: '2px solid var(--safe)',
            background: 'rgba(16, 185, 129, 0.06)',
            padding: '6px 8px',
            fontSize: '10px',
            lineHeight: 1.4,
            color: 'var(--text-secondary)',
            fontStyle: 'italic',
          }}
        >
          &ldquo;{summary.recommendation}&rdquo;
        </div>
      )}
    </div>
  );
}
