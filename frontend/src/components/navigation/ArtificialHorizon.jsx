import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * Tactical Artificial Horizon & Inclinometer Widget
 * Displays pitch ladder and roll horizon for real-time rover attitude stability.
 */
export default function ArtificialHorizon({ pitchDeg = 0, rollDeg = 0 }) {
  const p = parseFloat(pitchDeg) || 0;
  const r = parseFloat(rollDeg) || 0;

  const isWarning = Math.abs(p) > 18 || Math.abs(r) > 15;
  const isCritical = Math.abs(p) > 28 || Math.abs(r) > 22;

  // Scale: 1 degree pitch = 1.4 pixels vertical shift
  const pitchShiftPx = -p * 1.4;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        padding: '6px 8px',
        background: isCritical
          ? 'rgba(239, 68, 68, 0.15)'
          : isWarning
          ? 'rgba(245, 158, 11, 0.12)'
          : 'rgba(255, 255, 255, 0.02)',
        border: isCritical
          ? '1px solid var(--hazard)'
          : isWarning
          ? '1px solid var(--caution)'
          : '1px solid rgba(255, 255, 255, 0.08)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          ATTITUDE INCLINOMETER
        </span>
        {isWarning && (
          <span
            style={{
              fontSize: '8px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              color: isCritical ? 'var(--hazard)' : 'var(--caution)',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
          >
            <AlertTriangle size={10} />
            {isCritical ? 'ROLLOVER CRITICAL' : 'SLOPE CAUTION'}
          </span>
        )}
      </div>

      {/* Graphical Horizon Box */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '56px',
          overflow: 'hidden',
          background: '#04070b',
          border: '1px solid rgba(255, 255, 255, 0.1)',
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
            transition: 'transform 80ms ease-out',
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
              transition: 'transform 80ms ease-out',
            }}
          >
            {/* Horizon Center Line (0°) */}
            <div
              style={{
                position: 'absolute',
                top: '0px',
                left: '10px',
                right: '10px',
                height: '1.5px',
                background: '#06b6d4',
                boxShadow: '0 0 6px rgba(6, 182, 212, 0.6)',
              }}
            />

            {/* +20° Line */}
            <div
              style={{
                position: 'absolute',
                top: '-28px',
                left: '42px',
                right: '42px',
                height: '1px',
                background: 'rgba(255, 255, 255, 0.45)',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '7px',
                fontFamily: 'var(--font-mono)',
                color: 'rgba(255, 255, 255, 0.7)',
                marginTop: '-5px',
              }}
            >
              <span>+20</span>
              <span>+20</span>
            </div>

            {/* +10° Line */}
            <div
              style={{
                position: 'absolute',
                top: '-14px',
                left: '32px',
                right: '32px',
                height: '1px',
                background: 'rgba(255, 255, 255, 0.4)',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '7px',
                fontFamily: 'var(--font-mono)',
                color: 'rgba(255, 255, 255, 0.6)',
                marginTop: '-5px',
              }}
            >
              <span>+10</span>
              <span>+10</span>
            </div>

            {/* -10° Line */}
            <div
              style={{
                position: 'absolute',
                top: '14px',
                left: '32px',
                right: '32px',
                height: '1px',
                background: 'rgba(255, 255, 255, 0.4)',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '7px',
                fontFamily: 'var(--font-mono)',
                color: 'rgba(255, 255, 255, 0.6)',
                marginTop: '-4px',
              }}
            >
              <span>-10</span>
              <span>-10</span>
            </div>

            {/* -20° Line */}
            <div
              style={{
                position: 'absolute',
                top: '28px',
                left: '42px',
                right: '42px',
                height: '1px',
                background: 'rgba(255, 255, 255, 0.45)',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '7px',
                fontFamily: 'var(--font-mono)',
                color: 'rgba(255, 255, 255, 0.7)',
                marginTop: '-4px',
              }}
            >
              <span>-20</span>
              <span>-20</span>
            </div>
          </div>
        </div>

        {/* Fixed Center Chassis Reticle [ - • - ] */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            pointerEvents: 'none',
          }}
        >
          <div style={{ width: '12px', height: '2px', background: '#ffffff' }} />
          <div style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#ef4444' }} />
          <div style={{ width: '12px', height: '2px', background: '#ffffff' }} />
        </div>
      </div>

      {/* Numeric Readouts */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
        <span>
          PITCH:{' '}
          <strong style={{ color: Math.abs(p) > 18 ? 'var(--hazard)' : 'var(--text-primary)' }}>
            {p > 0 ? `+${p.toFixed(1)}` : p.toFixed(1)}°
          </strong>
        </span>
        <span>
          ROLL:{' '}
          <strong style={{ color: Math.abs(r) > 15 ? 'var(--hazard)' : 'var(--text-primary)' }}>
            {r > 0 ? `+${r.toFixed(1)}` : r.toFixed(1)}°
          </strong>
        </span>
      </div>
    </div>
  );
}
