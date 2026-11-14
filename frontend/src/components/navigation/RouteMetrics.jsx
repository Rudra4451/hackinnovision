import React, { useState } from 'react';

/**
 * A.R.E.S. Navigation Route Metrics
 * Utilitarian Brutalist Telemetry: Literal HTML <table> with visible 1px borders.
 * Zero floating UI cards. Zero rounded corners. Tabular monospace numerals.
 */
export default function RouteMetrics({ navigation }) {
  const [activeMode, setActiveMode] = useState('safest'); // 'safest' | 'shortest'

  if (!navigation) return null;

  const currentRouteData = navigation[activeMode];
  const metrics = currentRouteData?.metrics || {};
  const isSuccess = currentRouteData?.route?.success ?? false;
  const failureReason = currentRouteData?.route?.reason || 'TRAJECTORY UNREACHABLE';

  const formatValue = (val, decimals = 1, unit = '') => {
    if (val === undefined || val === null || val === 'NaN' || Number.isNaN(val)) return '—';
    if (val === 'Infinity' || val === Infinity) return '∞ [HAZARD]';
    const num = typeof val === 'number' ? val : parseFloat(val);
    return `${num.toFixed(decimals)}${unit ? ' ' + unit : ''}`;
  };

  const safeM = navigation.safest?.metrics || {};
  const shortM = navigation.shortest?.metrics || {};
  const summary = navigation.summary || {};

  return (
    <div
      style={{
        background: '#121212',
        border: '1px solid #333333',
        padding: '8px',
        color: '#D4D4D4',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <div className="section-header">
        <span>A.R.E.S. TRAJECTORY TELEMETRY</span>
        <div style={{ display: 'flex', gap: '0', border: '1px solid #333333' }}>
          <button
            className={`mc-btn ${activeMode === 'safest' ? 'mc-btn-active' : ''}`}
            style={{ padding: '2px 8px', fontSize: '10px', border: 'none', borderRight: '1px solid #333333' }}
            onClick={() => setActiveMode('safest')}
          >
            SAFEST [NOMINAL]
          </button>
          <button
            className={`mc-btn ${activeMode === 'shortest' ? 'mc-btn-active' : ''}`}
            style={{ padding: '2px 8px', fontSize: '10px', border: 'none' }}
            onClick={() => setActiveMode('shortest')}
          >
            SHORTEST [DIRECT]
          </button>
        </div>
      </div>

      {!isSuccess ? (
        <div
          style={{
            padding: '6px 8px',
            background: '#1a1010',
            border: '1px solid #DC2626',
            color: '#DC2626',
            fontSize: '11px',
            marginTop: '4px',
          }}
        >
          [ALERT] TRAJECTORY BLOCKED: {failureReason}
        </div>
      ) : (
        /* Literal HTML <table> with visible borders, zero floating cards */
        <table
          className="ares-table"
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            border: '1px solid #333333',
            fontSize: '10px',
            marginTop: '6px',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <thead>
            <tr style={{ background: '#181818' }}>
              <th style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'left', color: '#858585' }}>
                TELEMETRY PARAMETER
              </th>
              <th style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#0284C7' }}>
                SAFEST (NOMINAL)
              </th>
              <th style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#DC2626' }}>
                SHORTEST (DIRECT)
              </th>
              <th style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4' }}>
                DELTA
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>
                TOTAL DISTANCE
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4', fontWeight: 600 }}>
                {formatValue(safeM.total_distance, 1, 'm')}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4', fontWeight: 600 }}>
                {formatValue(shortM.total_distance, 1, 'm')}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D97706' }}>
                +{summary.distance_penalty_pct ? summary.distance_penalty_pct.toFixed(1) : '0.0'}%
              </td>
            </tr>
            <tr>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>
                AGGREGATE RISK COST
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#0284C7', fontWeight: 600 }}>
                {formatValue(safeM.total_cost, 1)}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#DC2626', fontWeight: 600 }}>
                {formatValue(shortM.total_cost, 1)}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#0284C7' }}>
                -{summary.cost_reduction_pct ? summary.cost_reduction_pct.toFixed(1) : '0.0'}%
              </td>
            </tr>
            <tr>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>
                AVERAGE CELL COST
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4' }}>
                {formatValue(safeM.avg_terrain_cost, 2)}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4' }}>
                {formatValue(shortM.avg_terrain_cost, 2)}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#858585' }}>
                {shortM.avg_terrain_cost && safeM.avg_terrain_cost
                  ? (safeM.avg_terrain_cost - shortM.avg_terrain_cost).toFixed(2)
                  : '—'}
              </td>
            </tr>
            <tr>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>
                CAUTION CELLS (&gt;2.0)
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#0284C7', fontWeight: 600 }}>
                {safeM.caution_steps ?? 0}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D97706', fontWeight: 600 }}>
                {shortM.caution_steps ?? 0}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#0284C7' }}>
                -{summary.caution_steps_avoided ?? 0}
              </td>
            </tr>
            <tr>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', color: '#858585' }}>
                WAYPOINT COUNT
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4' }}>
                {safeM.step_count ?? 0}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#D4D4D4' }}>
                {shortM.step_count ?? 0}
              </td>
              <td style={{ border: '1px solid #333333', padding: '5px 8px', textAlign: 'right', color: '#858585' }}>
                {safeM.step_count && shortM.step_count ? `${safeM.step_count - shortM.step_count}` : '0'}
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
