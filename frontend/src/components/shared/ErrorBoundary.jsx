import React from 'react';
import { AlertOctagon } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[MARS-09] Component boundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '24px',
            margin: '16px',
            background: 'var(--bg-panel)',
            border: '1px solid var(--hazard)',
            borderRadius: '8px',
            color: 'var(--text-primary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--hazard)', marginBottom: '8px' }}>
            <AlertOctagon size={20} />
            <span style={{ fontWeight: 600, fontSize: '15px' }}>
              {this.props.fallbackTitle || 'Component Execution Failure'}
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred in this module.'}
          </p>
          <button
            className="mc-btn"
            style={{ marginTop: '12px', fontSize: '12px' }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            RESET MODULE
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
