import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function ErrorBanner({ error, onRetry }) {
  if (!error) return null;

  return (
    <div
      style={{
        margin: '16px',
        padding: '16px',
        backgroundColor: 'rgba(239, 68, 68, 0.12)',
        border: '1px solid var(--hazard)',
        borderRadius: '6px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--hazard)', fontWeight: 600 }}>
          <AlertCircle size={18} />
          <span>{error.title || 'Mission Control System Alert'}</span>
        </div>
        {onRetry && (
          <button className="mc-btn" onClick={onRetry} style={{ padding: '4px 8px', fontSize: '11px' }}>
            <RefreshCw size={12} />
            RETRY LINK
          </button>
        )}
      </div>

      <div style={{ color: 'var(--text-primary)', fontSize: '13px' }}>
        {error.message}
      </div>

      {error.timestamp && (
        <div className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          Last Link Attempt: {error.timestamp}
        </div>
      )}

      {error.details && error.details.length > 0 && (
        <div
          className="mono"
          style={{
            background: 'var(--bg-base)',
            padding: '8px',
            borderRadius: '4px',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            maxHeight: '100px',
            overflowY: 'auto',
          }}
        >
          {error.details.map((d, i) => (
            <div key={i}>• {d}</div>
          ))}
        </div>
      )}

      {error.samples && error.samples.length > 0 && (
        <div className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Bad data samples (row, col: value):{' '}
          {error.samples.map((s) => `(${s.row}, ${s.col}: ${s.value})`).join(', ')}
        </div>
      )}
    </div>
  );
}
