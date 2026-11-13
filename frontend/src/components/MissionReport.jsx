import React, { useState } from 'react';
import { FileText, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';

export default function MissionReport({ reportMarkdown }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = () => {
    if (reportMarkdown) {
      navigator.clipboard.writeText(reportMarkdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <FileText size={18} />
          Planetary Reconnaissance Mission Briefing (Markdown)
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="btn-tactical"
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            onClick={handleCopy}
          >
            {copied ? <Check size={14} color="#00e676" /> : <Copy size={14} />}
            {copied ? 'COPIED' : 'COPY BRIEF'}
          </button>
          <button
            className="btn-tactical"
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? 'COLLAPSE' : 'EXPAND'}
          </button>
        </div>
      </div>

      <pre
        className="mono"
        style={{
          background: 'rgba(0, 0, 0, 0.4)',
          padding: '1rem',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#cbd5e1',
          overflowX: 'auto',
          maxHeight: expanded ? '600px' : '220px',
          whiteSpace: 'pre-wrap',
          lineHeight: 1.5,
          border: '1px solid var(--border-subtle)',
        }}
      >
        {reportMarkdown || 'Loading tactical telemetry briefing...'}
      </pre>
    </div>
  );
}
