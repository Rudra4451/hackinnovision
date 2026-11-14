import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function ErrorBanner({ error, onRetry }) {
  if (!error) return null;

  return (
    <div
      style={{
        margin: '12px',
        padding: '12px',
        backgroundColor: '#1a1010',
        border: '1px solid #DC2626',
        borderRadius: '0px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#DC2626', fontWeight: 700, fontSize: '11px' }}>
          <AlertCircle size={14} />
          <span>[SYSTEM ALERT] {error.title || 'COMMUNICATION LINK FAILURE'}</span>
        </div>
        {onRetry && (
          <button className="mc-btn" onClick={onRetry} style={{ padding: '2px 8px', fontSize: '10px' }}>
            <RefreshCw size={10} />
            RETRY LINK
          </button>
        )}
      </div>

      <div style={{ color: '#D4D4D4', fontSize: '11px' }}>
        {error.message}
      </div>

      {error.timestamp && (
        <div className="mono" style={{ fontSize: '9px', color: '#858585' }}>
          TIMESTAMP: {error.timestamp}
        </div>
      )}

      {error.details && error.details.length > 0 && (
        <div
          className="mono"
          style={{
            background: '#121212',
            padding: '6px',
            border: '1px solid #333333',
            borderRadius: '0px',
            fontSize: '10px',
            color: '#858585',
            maxHeight: '90px',
            overflowY: 'auto',
          }}
        >
          {error.details.map((d, i) => (
            <div key={i}>&gt; {d}</div>
          ))}
        </div>
      )}
    </div>
  );
}
