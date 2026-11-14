import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * A.R.E.S. Attitude Inclinometer / Artificial Horizon
 * Brutalist Aerospace Telemetry: Zero curves, strict hairline borders, tabular numerals.
 */
export default function ArtificialHorizon({ pitchDeg = 0, rollDeg = 0 }) {
  const p = parseFloat(pitchDeg) || 0;
  const r = parseFloat(rollDeg) || 0;

  const isWarning = Math.abs(p) > 18 || Math.abs(r) > 15;
  const isCritical = Math.abs(p) > 28 || Math.abs(r) > 22;

  // Scale: 1 degree pitch = 1.3 pixels vertical shift
  const pitchShiftPx = -p * 1.3;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        padding: '6px',
        background: '#121212',
        border: '1px solid #333333',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '9px', color: '#858585', letterSpacing: '0.08em', fontWeight: 600 }}>
          ATTITUDE INCLINOMETER
        </span>
        {isWarning && (
          <span
            style={{
              fontSize: '8px',
              fontWeight: 700,
              color: isCritical ? '#DC2626' : '#D97706',
              border: `1px solid ${isCritical ? '#DC2626' : '#D97706'}`,
              padding: '0 4px',
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
            }}
          >
            <AlertTriangle size={9} />
            {isCritical ? 'ROLLOVER CRITICAL' : 'SLOPE CAUTION'}
          </span>
        )}
      </div>

      {/* Graphical Horizon Box */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '52px',
          overflow: 'hidden',
          background: '#161616',
          border: '1px solid #333333',
        }}
      >
        {/* Tilting Horizon & Pitch Ladder Group */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: '140px',
            height: '140px',
            marginTop: '-70px',
            marginLeft: '-70px',
            transform: `rotate(${r}deg)`,
            pointerEvents: 'none',
          }}
        >
          {/* Pitch Container */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: 0,
              right: 0,
              transform: `translateY(${pitchShiftPx}px)`,
            }}
          >
            {/* Horizon Center Line (0°) */}
            <div
              style={{
                position: 'absolute',
                top: '0px',
                left: '10px',
                right: '10px',
                height: '1px',
                background: '#D4D4D4',
              }}
            />

            {/* +10° Pitch Marker */}
            <div
              style={{
                position: 'absolute',
                top: '-13px',
                left: '35px',
                right: '35px',
                height: '1px',
                background: '#858585',
              }}
            />

            {/* -10° Pitch Marker */}
            <div
              style={{
                position: 'absolute',
                top: '13px',
                left: '35px',
                right: '35px',
                height: '1px',
                background: '#858585',
              }}
            />

            {/* +20° Pitch Marker */}
            <div
              style={{
                position: 'absolute',
                top: '-26px',
                left: '45px',
                right: '45px',
                height: '1px',
                background: '#555555',
              }}
            />

            {/* -20° Pitch Marker */}
            <div
              style={{
                position: 'absolute',
                top: '26px',
                left: '45px',
                right: '45px',
                height: '1px',
                background: '#555555',
              }}
            />
          </div>
        </div>

        {/* Center Aircraft Reticle (Fixed Chassis Center) */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: '28px',
            height: '6px',
            marginTop: '-3px',
            marginLeft: '-14px',
            pointerEvents: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ width: '8px', height: '2px', background: '#0284C7' }} />
          <div style={{ width: '2px', height: '2px', background: '#0284C7' }} />
          <div style={{ width: '8px', height: '2px', background: '#0284C7' }} />
        </div>

        {/* Dynamic Telemetry Numbers */}
        <div
          style={{
            position: 'absolute',
            bottom: '2px',
            left: '4px',
            fontSize: '9px',
            color: '#858585',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          P: <span style={{ color: Math.abs(p) > 20 ? '#DC2626' : '#D4D4D4', fontWeight: 600 }}>{p.toFixed(1)}°</span>
        </div>
        <div
          style={{
            position: 'absolute',
            bottom: '2px',
            right: '4px',
            fontSize: '9px',
            color: '#858585',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          R: <span style={{ color: Math.abs(r) > 15 ? '#DC2626' : '#D4D4D4', fontWeight: 600 }}>{r.toFixed(1)}°</span>
        </div>
      </div>
    </div>
  );
}
