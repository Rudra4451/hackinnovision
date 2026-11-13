import React, { useState } from 'react';
import { ChevronDown, ChevronUp, GitCompare, Shield, Zap, CheckCircle2 } from 'lucide-react';

export default function RouteComparison({ navigation }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!navigation || !navigation.summary || !navigation.summary.both_reachable) {
    return null;
  }

  const { safest, shortest, summary } = navigation;
  const safeM = safest?.metrics || {};
  const shortM = shortest?.metrics || {};

  const formatNum = (val, dec = 1, unit = '') => {
    if (val === undefined || val === null || val === 'NaN' || Number.isNaN(val)) return '—';
    if (val === 'Infinity' || val === Infinity) return '∞';
    const num = typeof val === 'number' ? val : parseFloat(val);
    return `${num.toFixed(dec)}${unit ? ' ' + unit : ''}`;
  };

  const costRed = summary.cost_reduction_pct;
  const distPen = summary.distance_penalty_pct;
  const cautionAvoided = summary.caution_steps_avoided;

  return (
    <div className="telemetry-card" style={{ padding: '0', overflow: 'hidden' }}>
      {/* Collapsible Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'transparent',
          border: 'none',
          padding: '10px 14px',
          cursor: 'pointer',
          color: 'var(--text-primary)',
          textAlign: 'left'
        }}
        aria-expanded={isOpen}
      >
        <div style={{ display: 'flex', alignContent: 'center', alignItems: 'center', gap: '8px' }}>
          <GitCompare size={14} color="var(--accent-info)" />
          <span className="section-header" style={{ marginBottom: 0 }}>
            Route Comparison
          </span>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              background: 'rgba(16, 185, 129, 0.15)',
              color: 'var(--safe)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: 600
            }}
          >
            BOTH REACHABLE
          </span>
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Collapsible Drawer Content */}
      {isOpen && (
        <div style={{ padding: '0 14px 14px 14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Comparison Table */}
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)'
              }}
            >
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '6px 4px', fontWeight: 500 }}>METRIC</th>
                  <th style={{ padding: '6px 4px', fontWeight: 500, color: 'var(--safe)' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Shield size={10} /> SAFEST
                    </span>
                  </th>
                  <th style={{ padding: '6px 4px', fontWeight: 500, color: 'var(--text-primary)' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Zap size={10} color="var(--hazard)" /> SHORTEST
                    </span>
                  </th>
                  <th style={{ padding: '6px 4px', fontWeight: 500, textAlign: 'right' }}>DELTA</th>
                </tr>
              </thead>
              <tbody>
                {/* Distance */}
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>Distance</td>
                  <td style={{ padding: '6px 4px', color: 'var(--text-primary)' }}>{formatNum(safeM.total_distance, 1, 'm')}</td>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>{formatNum(shortM.total_distance, 1, 'm')}</td>
                  <td
                    style={{
                      padding: '6px 4px',
                      textAlign: 'right',
                      color: distPen > 0 ? 'var(--caution)' : 'var(--safe)',
                      fontWeight: 600
                    }}
                  >
                    {distPen > 0 ? `+${formatNum(distPen, 1)}%` : `${formatNum(distPen, 1)}%`}
                  </td>
                </tr>

                {/* Accumulated Cost */}
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>Cost</td>
                  <td style={{ padding: '6px 4px', color: 'var(--safe)', fontWeight: 600 }}>{formatNum(safeM.total_cost, 1)}</td>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>{formatNum(shortM.total_cost, 1)}</td>
                  <td
                    style={{
                      padding: '6px 4px',
                      textAlign: 'right',
                      color: costRed > 0 ? 'var(--safe)' : 'var(--text-secondary)',
                      fontWeight: 600
                    }}
                  >
                    {costRed > 0 ? `-${formatNum(costRed, 1)}%` : '0%'}
                  </td>
                </tr>

                {/* Caution Steps */}
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>Caution Steps</td>
                  <td style={{ padding: '6px 4px', color: safeM.caution_steps > 0 ? 'var(--caution)' : 'var(--safe)' }}>
                    {safeM.caution_steps ?? 0}
                  </td>
                  <td style={{ padding: '6px 4px', color: shortM.caution_steps > 0 ? 'var(--caution)' : 'var(--text-secondary)' }}>
                    {shortM.caution_steps ?? 0}
                  </td>
                  <td
                    style={{
                      padding: '6px 4px',
                      textAlign: 'right',
                      color: cautionAvoided > 0 ? 'var(--safe)' : 'var(--text-secondary)',
                      fontWeight: 600
                    }}
                  >
                    {cautionAvoided > 0 ? `-${cautionAvoided} avoided` : '0'}
                  </td>
                </tr>

                {/* Avg Terrain Cost */}
                <tr>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>Avg Cost</td>
                  <td style={{ padding: '6px 4px', color: 'var(--text-primary)' }}>{formatNum(safeM.avg_terrain_cost, 2)}</td>
                  <td style={{ padding: '6px 4px', color: 'var(--text-secondary)' }}>{formatNum(shortM.avg_terrain_cost, 2)}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'right', color: 'var(--text-secondary)' }}>
                    {safeM.avg_terrain_cost && shortM.avg_terrain_cost
                      ? (safeM.avg_terrain_cost - shortM.avg_terrain_cost < 0 ? '-' : '+') +
                        Math.abs(safeM.avg_terrain_cost - shortM.avg_terrain_cost).toFixed(2)
                      : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Quoted Recommendation Callout Box (§5.3) */}
          {summary.recommendation && (
            <div
              style={{
                borderLeft: '3px solid var(--safe)',
                background: 'rgba(16, 185, 129, 0.08)',
                padding: '8px 12px',
                borderRadius: '0 4px 4px 0',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                borderLeftWidth: '3px',
                fontSize: '11px',
                lineHeight: 1.5,
                color: 'var(--text-primary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px', color: 'var(--safe)', fontWeight: 600, fontSize: '10px' }}>
                <CheckCircle2 size={12} />
                <span>MISSION NAVIGATOR RECOMMENDATION</span>
              </div>
              <span style={{ fontStyle: 'italic' }}>
                &ldquo;{summary.recommendation}&rdquo;
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
