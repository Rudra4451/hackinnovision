import React from 'react';

export default function StatusChip({ status = 'READY', label = null }) {
  const displayLabel = label || status;

  const styleMap = {
    READY: {
      bg: 'rgba(99, 102, 241, 0.15)',
      border: 'var(--accent-info)',
      color: '#A5B4FC',
      dotColor: 'var(--accent-info)',
      blink: false,
    },
    RUNNING: {
      bg: 'rgba(6, 182, 212, 0.15)',
      border: 'var(--rover)',
      color: 'var(--rover)',
      dotColor: 'var(--rover)',
      blink: true,
    },
    PAUSED: {
      bg: 'rgba(245, 158, 11, 0.15)',
      border: 'var(--caution)',
      color: 'var(--caution)',
      dotColor: 'var(--caution)',
      blink: false,
    },
    COMPLETED: {
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'var(--safe)',
      color: 'var(--safe)',
      dotColor: 'var(--safe)',
      blink: false,
    },
    FAILED: {
      bg: 'rgba(239, 68, 68, 0.15)',
      border: 'var(--hazard)',
      color: 'var(--hazard)',
      dotColor: 'var(--hazard)',
      blink: false,
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
        padding: '3px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.05em',
        background: current.bg,
        border: `1px solid ${current.border}`,
        color: current.color,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: current.dotColor,
        }}
        className={current.blink ? 'status-blinking' : ''}
      />
      {displayLabel}
    </span>
  );
}
