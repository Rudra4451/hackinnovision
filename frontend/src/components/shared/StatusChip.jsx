import React from 'react';

/**
 * A.R.E.S. Status Chip Indicator
 * Strict Brutalist Aerospace: Square indicator dot, zero curves, 1px border, tabular font.
 */
export default function StatusChip({ status = 'READY', label = null }) {
  const displayLabel = label || status;

  const styleMap = {
    READY: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: false,
    },
    INITIALIZING: {
      bg: '#181818',
      border: '#858585',
      color: '#D4D4D4',
      dotColor: '#858585',
      blink: true,
    },
    NAVIGATING: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: true,
    },
    RUNNING: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: true,
    },
    PAUSED: {
      bg: '#181818',
      border: '#D97706',
      color: '#D97706',
      dotColor: '#D97706',
      blink: false,
    },
    ARRIVED: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: false,
    },
    COMPLETED: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: false,
    },
    BLOCKED: {
      bg: '#1a1010',
      border: '#DC2626',
      color: '#DC2626',
      dotColor: '#DC2626',
      blink: false,
    },
    OFFLINE: {
      bg: '#1a1010',
      border: '#DC2626',
      color: '#DC2626',
      dotColor: '#DC2626',
      blink: false,
    },
    FAILED: {
      bg: '#1a1010',
      border: '#DC2626',
      color: '#DC2626',
      dotColor: '#DC2626',
      blink: false,
    },
    SELECT_START: {
      bg: '#181818',
      border: '#0284C7',
      color: '#0284C7',
      dotColor: '#0284C7',
      blink: true,
    },
    SELECT_GOAL: {
      bg: '#181818',
      border: '#D97706',
      color: '#D97706',
      dotColor: '#D97706',
      blink: true,
    },
  };

  const current = styleMap[status] || styleMap.READY;

  return (
    <span
      className="mono"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '2px 7px',
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.08em',
        background: current.bg,
        border: `1px solid ${current.border}`,
        color: current.color,
        borderRadius: '0px',
        textTransform: 'uppercase',
      }}
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          backgroundColor: current.dotColor,
          display: 'inline-block',
        }}
        className={current.blink ? 'status-blinking' : ''}
      />
      {displayLabel}
    </span>
  );
}
