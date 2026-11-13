import React from 'react';
import { Target, AlertTriangle, ShieldCheck, ShieldAlert, Award } from 'lucide-react';

export default function ScienceTargets({
  targets = [],
  selectedTargetId,
  onSelectTarget,
}) {
  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Target size={18} />
          Science Intelligence Prioritization Matrix
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Rule 2 Hard Safety Gated (Unsafe = Priority 0)
        </div>
      </div>

      <div className="targets-table-wrapper">
        <table className="targets-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Target Site</th>
              <th>Classification</th>
              <th>Sci Value</th>
              <th style={{ color: 'var(--cyan-safe)' }}>Op Priority</th>
              <th>Status</th>
              <th>Distance</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {targets.map((tgt, index) => {
              const isSelected = selectedTargetId === tgt.id;
              const isGated = tgt.operational_priority === 0.0;

              return (
                <tr
                  key={tgt.id}
                  className={isSelected ? 'selected-target' : ''}
                  onClick={() => onSelectTarget(tgt)}
                >
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>
                    #{index + 1}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: '#fff' }}>{tgt.name}</div>
                    <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      ID: {tgt.id} | [{tgt.location[0]}, {tgt.location[1]}]
                    </div>
                  </td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {tgt.target_type.replace(/_/g, ' ')}
                  </td>
                  <td className="mono" style={{ fontWeight: 600, color: '#ffb300' }}>
                    {tgt.scientific_value.toFixed(1)}
                  </td>
                  <td
                    className="mono"
                    style={{
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      color: isGated ? '#ff1744' : '#00f0ff',
                    }}
                  >
                    {tgt.operational_priority.toFixed(1)}
                  </td>
                  <td>
                    {tgt.accessibility_status === 'OPTIMAL' && (
                      <span className="badge badge-optimal">OPTIMAL</span>
                    )}
                    {tgt.accessibility_status === 'CAUTION' && (
                      <span className="badge badge-caution">CAUTION</span>
                    )}
                    {tgt.accessibility_status === 'UNREACHABLE_HAZARD' && (
                      <span className="badge badge-gated">GATED (0.0)</span>
                    )}
                  </td>
                  <td className="mono" style={{ fontSize: '0.75rem' }}>
                    {isGated ? 'UNREACHABLE' : `${tgt.estimated_distance.toFixed(1)} m`}
                  </td>
                  <td>
                    <button
                      className={`btn-tactical ${isGated ? '' : 'btn-cyan'}`}
                      style={{ padding: '0.25rem 0.6rem', fontSize: '0.7rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTarget(tgt);
                      }}
                      disabled={isGated}
                    >
                      {isGated ? 'LOCKED' : isSelected ? 'ENGAGED' : 'NAVIGATE'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
