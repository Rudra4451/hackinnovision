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
    console.error('[A.R.E.S.] Component boundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '16px',
            margin: '12px',
            background: '#1a1010',
            border: '1px solid #DC2626',
            borderRadius: '0px',
            color: '#D4D4D4',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#DC2626', marginBottom: '6px' }}>
            <AlertOctagon size={16} />
            <span style={{ fontWeight: 700, fontSize: '13px', textTransform: 'uppercase' }}>
              [MODULE CRASH] {this.props.fallbackTitle || 'SUBSYSTEM EXECUTION FAILURE'}
            </span>
          </div>
          <p style={{ fontSize: '11px', color: '#858585' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred in this module.'}
          </p>
          <button
            className="mc-btn"
            style={{ marginTop: '10px', fontSize: '10px' }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            [ REINITIALIZE MODULE ]
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
