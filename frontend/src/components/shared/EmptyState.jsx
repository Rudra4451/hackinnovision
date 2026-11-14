import React from 'react';
import { Database } from 'lucide-react';

export default function EmptyState({ title, message, icon: Icon = Database }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '36px 20px',
        textAlign: 'center',
        gap: '10px',
        height: '100%',
        color: '#858585',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '0px',
          background: '#161616',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #333333',
          color: '#858585',
        }}
      >
        <Icon size={20} />
      </div>

      <div style={{ color: '#D4D4D4', fontSize: '13px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        {title}
      </div>

      <div style={{ maxWidth: '360px', fontSize: '11px', lineHeight: 1.4, color: '#858585' }}>
        {message}
      </div>
    </div>
  );
}
