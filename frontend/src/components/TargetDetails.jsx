import React from 'react';
import { Microscope, AlertTriangle, CheckCircle, Info, Sparkles, Activity } from 'lucide-react';

export default function TargetDetails({ target }) {
  if (!target) {
    return (
      <div className="hud-panel">
        <div className="hud-panel-title">
          <Microscope size={18} />
          Spectroscopic Intelligence & Uncertainty Analysis
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
          Select a candidate target from the prioritization matrix to inspect orbital spectral features.
        </div>
      </div>
    );
  }

  const isGated = target.operational_priority === 0.0;
  const sig = target.spectral_signature || {};
  const hydrationPct = Math.round((sig.hydration_index || 0.5) * 100);
  const diversityPct = Math.round((sig.mineral_diversity || 0.5) * 100);
  const snr = sig.signal_to_noise || 8.0;

  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Microscope size={18} />
          {target.name} (ID: {target.id})
        </div>
        <div>
          {isGated ? (
            <span className="badge badge-gated">RULE 2 GATED: HAZARD</span>
          ) : (
            <span className="badge badge-optimal">OPERATIONAL RANK ACTIVE</span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div className="tradeoff-stat-box">
          <div className="stat-val" style={{ color: '#ffb300' }}>
            {target.scientific_value.toFixed(1)} / 100
          </div>
          <div className="stat-label">Inherent Scientific Value</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val" style={{ color: isGated ? '#ff1744' : '#00f0ff' }}>
            {target.operational_priority.toFixed(1)} / 100
          </div>
          <div className="stat-label">Operational Priority (Safety-Adjusted)</div>
        </div>
      </div>

      {/* Uncertainty & Entropy */}
      <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem', border: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Activity size={14} color="var(--cyan-safe)" />
            Shannon Entropy Uncertainty
          </span>
          <span className="mono" style={{ fontSize: '0.85rem', color: '#00f0ff', fontWeight: 600 }}>
            {(target.confidence_level * 100).toFixed(1)}% Confidence
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Normalized Entropy: <span className="mono" style={{ color: '#fff' }}>{target.uncertainty_score.toFixed(3)}</span> | 
          Physical coordinates: <span className="mono" style={{ color: '#fff' }}>[{target.location[0]}, {target.location[1]}]</span>
        </div>
      </div>

      {/* Spectral Signatures */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <Sparkles size={14} color="#ff7043" />
          Multi-Band Spectral Extraction
        </div>

        <div className="spectral-bar-item">
          <span>Hydration Index:</span>
          <div className="spectral-progress">
            <div className="spectral-progress-fill" style={{ width: `${hydrationPct}%` }} />
          </div>
          <span>{hydrationPct}%</span>
        </div>

        <div className="spectral-bar-item">
          <span>Mineral Diversity:</span>
          <div className="spectral-progress">
            <div className="spectral-progress-fill" style={{ width: `${diversityPct}%`, background: 'linear-gradient(90deg, #ffb300, #00e676)' }} />
          </div>
          <span>{diversityPct}%</span>
        </div>

        <div className="spectral-bar-item">
          <span>Spectrometer SNR:</span>
          <span style={{ color: '#00f0ff', fontWeight: 600 }}>{snr.toFixed(1)} : 1</span>
        </div>
      </div>

      {/* Justification & Operational Assessment */}
      <div style={{ padding: '0.75rem', borderRadius: '4px', background: isGated ? 'rgba(255, 23, 68, 0.08)' : 'rgba(0, 240, 255, 0.05)', borderLeft: `3px solid ${isGated ? '#ff1744' : '#00f0ff'}` }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600, color: isGated ? '#ff1744' : '#00f0ff', marginBottom: '0.2rem' }}>
          {isGated ? 'Operational Safety Gate Lockdown' : 'Evidence-Based Tactical Justification'}
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
          {target.justification}
        </p>
      </div>
    </div>
  );
}
