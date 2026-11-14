import React from 'react';

/**
 * A.R.E.S. Strict Geometric SVG Logo
 * Strict, utilitarian aerospace emblem: thick-bordered triangle intersecting a precision crosshair,
 * bracketed monospace moniker [ A.R.E.S. ], and raw military-spec barcode asset.
 * Monochrome (#D4D4D4 / #DC2626). Zero gradients. Zero curves.
 */
export default function AresLogo({ size = 48, monochrome = false, showText = true, className = '' }) {
  const primaryColor = '#D4D4D4';
  const accentColor = monochrome ? '#D4D4D4' : '#DC2626';

  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`} style={{ fontFamily: 'var(--font-mono)' }}>
      {/* Strict Geometric Emblem SVG */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        {/* Outer Hairline Calibration Grid Frame */}
        <rect x="2" y="2" width="96" height="96" stroke="#333333" strokeWidth="1" />
        
        {/* Hairline Corner Alignment Ticks */}
        <path d="M 2 12 L 12 12 L 12 2" stroke={primaryColor} strokeWidth="1.5" fill="none" />
        <path d="M 98 12 L 88 12 L 88 2" stroke={primaryColor} strokeWidth="1.5" fill="none" />
        <path d="M 2 88 L 12 88 L 12 98" stroke={primaryColor} strokeWidth="1.5" fill="none" />
        <path d="M 98 88 L 88 88 L 88 98" stroke={primaryColor} strokeWidth="1.5" fill="none" />

        {/* Thick-Bordered Sharp Triangle */}
        <polygon
          points="50,14 86,78 14,78"
          fill="none"
          stroke={primaryColor}
          strokeWidth="4"
          strokeLinejoin="miter"
        />

        {/* Inner Inverted Geometric Delta */}
        <polygon
          points="50,68 32,36 68,36"
          fill="none"
          stroke="#333333"
          strokeWidth="1.5"
          strokeLinejoin="miter"
        />

        {/* Precision Target Crosshair Intersecting Triangle */}
        <line x1="50" y1="6" x2="50" y2="88" stroke={accentColor} strokeWidth="1.5" strokeDasharray="6 2" />
        <line x1="8" y1="52" x2="92" y2="52" stroke={accentColor} strokeWidth="1.5" strokeDasharray="6 2" />

        {/* Reticle Center Box */}
        <rect x="46" y="48" width="8" height="8" fill="#121212" stroke={primaryColor} strokeWidth="1.5" />
        <rect x="48" y="50" width="4" height="4" fill={accentColor} />

        {/* Horizontal Baseline Datum */}
        <line x1="22" y1="84" x2="78" y2="84" stroke="#555555" strokeWidth="1.5" />
      </svg>

      {/* Bracketed Monospace Moniker & Raw Barcode Asset */}
      {showText && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: size >= 40 ? '16px' : '13px',
                fontWeight: 700,
                letterSpacing: '0.18em',
                color: primaryColor,
              }}
            >
              [ A.R.E.S. ]
            </span>
            <span
              style={{
                fontSize: '9px',
                color: accentColor,
                border: `1px solid ${accentColor}`,
                padding: '0px 4px',
                fontWeight: 700,
                letterSpacing: '0.08em',
              }}
            >
              MARS-09
            </span>
          </div>

          {/* Raw Barcode Asset */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              height: '8px',
              gap: '2px',
              opacity: 0.75,
            }}
            title="MIL-STD-ARES-09-NAV"
          >
            <div style={{ width: '2px', height: '100%', background: primaryColor }} />
            <div style={{ width: '4px', height: '100%', background: primaryColor }} />
            <div style={{ width: '1px', height: '100%', background: primaryColor }} />
            <div style={{ width: '3px', height: '100%', background: primaryColor }} />
            <div style={{ width: '1px', height: '100%', background: primaryColor }} />
            <div style={{ width: '5px', height: '100%', background: primaryColor }} />
            <div style={{ width: '2px', height: '100%', background: primaryColor }} />
            <div style={{ width: '1px', height: '100%', background: primaryColor }} />
            <div style={{ width: '4px', height: '100%', background: accentColor }} />
            <div style={{ width: '2px', height: '100%', background: primaryColor }} />
            <div style={{ width: '6px', height: '100%', background: primaryColor }} />
            <div style={{ width: '1px', height: '100%', background: primaryColor }} />
            <div style={{ width: '3px', height: '100%', background: primaryColor }} />
            <div style={{ width: '2px', height: '100%', background: primaryColor }} />
            <span style={{ fontSize: '7px', color: '#858585', marginLeft: '4px', letterSpacing: '0.1em' }}>
              SEC-09-REV4
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
