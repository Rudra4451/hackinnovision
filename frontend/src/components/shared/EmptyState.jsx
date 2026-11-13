import React from 'react';
import { Database, AlertTriangle } from 'lucide-react';

export default function EmptyState({ title, message, icon: Icon = Database }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        gap: '12px',
        height: '100%',
        color: 'var(--text-secondary)',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: 'var(--bg-elevated)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--border-subtle)',
          color: 'var(--text-muted)',
        }}
      >
        <Icon size={24} />
      </div>

      <div style={{ color: 'var(--text-primary)', fontSize: '15px', fontWeight: 600 }}>
        {title}
      </div>

      <div style={{ maxWidth: '380px', fontSize: '13px', lineHeight: 1.5 }}>
        {message}
      </div>
    </div>
  );
}
