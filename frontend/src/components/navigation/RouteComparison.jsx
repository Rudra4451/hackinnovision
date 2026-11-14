import React, { useState } from 'react';
import { ChevronDown, ChevronUp, GitCompare, Shield, Zap } from 'lucide-react';

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
    <div
      style={{
        padding: '0',
        overflow: 'hidden',
        background: '#121212',
        border: '1px solid #333333',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      {/* Collapsible Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#161616',
          border: 'none',
          borderBottom: isOpen ? '1px solid #333333' : 'none',
          padding: '8px 12px',
          cursor: 'pointer',
          color: '#D4D4D4',
          textAlign: 'left',
        }}
        aria-expanded={isOpen}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitCompare size={13} color="#0284C7" />
          <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            A.R.E.S. TRAJECTORY COMPARISON
          </span>
          <span
            style={{
              fontSize: '9px',
              fontFamily: 'var(--font-mono)',
              border: '1px solid #0284C7',
              color: '#0284C7',
              padding: '1px 5px',
              fontWeight: 700,
            }}
          >
            DUAL REACHABLE
          </span>
        </div>
        <div style={{ color: '#858585' }}>
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {/* Collapsible Drawer Content */}
      {isOpen && (
        <div style={{ padding: '8px 12px 12px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Comparison Table with Visible Borders */}
          <div style={{ overflowX: 'auto' }}>
            <table
              className="ares-table"
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                border: '1px solid #333333',
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <thead>
                <tr style={{ background: '#181818' }}>
                  <th style={{ border: '1px solid #333333', padding: '5px 8px', fontWeight: 600, color: '#858585' }}>
                    METRIC
                  </th>
                  <th style={{ border: '1px solid #333333', padding: '5px 8px', fontWeight: 600, color: '#0284C7' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Shield size={10} /> SAFEST
                    </span>
                  </th>
                  <th style={{ border: '1px solid #333333', padding: '5px 8px', fontWeight: 600, color: '#DC2626' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Zap size={10} /> SHORTEST
                    </span>
                  </th>
                  <th style={{ border: '1px solid #333333', padding: '5px 8px', fontWeight: 600, textAlign: 'right', color: '#D4D4D4' }}>
                    DELTA
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>Distance</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#D4D4D4' }}>{formatNum(safeM.total_distance, 1, 'm')}</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#D4D4D4' }}>{formatNum(shortM.total_distance, 1, 'm')}</td>
                  <td
                    style={{
                      border: '1px solid #333333',
                      padding: '5px 8px',
                      textAlign: 'right',
                      color: distPen > 0 ? '#D97706' : '#0284C7',
                      fontWeight: 600,
                    }}
                  >
                    {distPen > 0 ? `+${formatNum(distPen, 1)}%` : `${formatNum(distPen, 1)}%`}
                  </td>
                </tr>

                <tr>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>Risk Cost</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#0284C7', fontWeight: 600 }}>{formatNum(safeM.total_cost, 1)}</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#DC2626', fontWeight: 600 }}>{formatNum(shortM.total_cost, 1)}</td>
                  <td
                    style={{
                      border: '1px solid #333333',
                      padding: '5px 8px',
                      textAlign: 'right',
                      color: costRed > 0 ? '#0284C7' : '#858585',
                      fontWeight: 600,
                    }}
                  >
                    {costRed > 0 ? `-${formatNum(costRed, 1)}%` : '0%'}
                  </td>
                </tr>

                <tr>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>Caution Cells</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: safeM.caution_steps > 0 ? '#D97706' : '#0284C7' }}>
                    {safeM.caution_steps ?? 0}
                  </td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: shortM.caution_steps > 0 ? '#D97706' : '#858585' }}>
                    {shortM.caution_steps ?? 0}
                  </td>
                  <td
                    style={{
                      border: '1px solid #333333',
                      padding: '5px 8px',
                      textAlign: 'right',
                      color: cautionAvoided > 0 ? '#0284C7' : '#858585',
                      fontWeight: 600,
                    }}
                  >
                    {cautionAvoided > 0 ? `-${cautionAvoided}` : '0'}
                  </td>
                </tr>

                <tr>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>Avg Cost</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#D4D4D4' }}>{formatNum(safeM.avg_terrain_cost, 2)}</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#D4D4D4' }}>{formatNum(shortM.avg_terrain_cost, 2)}</td>
                  <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#858585' }}>
                    {safeM.avg_terrain_cost && shortM.avg_terrain_cost
                      ? (safeM.avg_terrain_cost - shortM.avg_terrain_cost < 0 ? '-' : '+') +
                        Math.abs(safeM.avg_terrain_cost - shortM.avg_terrain_cost).toFixed(2)
                      : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Quoted Recommendation Callout Box */}
          {summary.recommendation && (
            <div
              style={{
                borderLeft: '2px solid #0284C7',
                background: '#161616',
                border: '1px solid #333333',
                borderLeftWidth: '2px',
                padding: '6px 10px',
                fontSize: '10px',
                lineHeight: 1.4,
                color: '#858585',
              }}
            >
              &ldquo;{summary.recommendation}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
