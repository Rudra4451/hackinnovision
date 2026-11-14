import React, { useState } from 'react';
import { Route, Shield, Zap } from 'lucide-react';

export default function RouteMetrics({ navigation }) {
  const [activeMode, setActiveMode] = useState('safest'); // 'safest' | 'shortest'

  if (!navigation) return null;

  const currentRouteData = navigation[activeMode];
  const metrics = currentRouteData?.metrics || {};
  const isSuccess = currentRouteData?.route?.success ?? false;
  const failureReason = currentRouteData?.route?.reason || 'Unknown trajectory planning error';

  const formatValue = (val, decimals = 2, unit = '') => {
    if (val === undefined || val === null || val === 'NaN' || Number.isNaN(val)) {
      return '—';
    }
    if (val === 'Infinity' || val === Infinity) {
      return '∞ (HAZARD)';
    }
    const num = typeof val === 'number' ? val : parseFloat(val);
    return `${num.toFixed(decimals)}${unit ? ' ' + unit : ''}`;
  };

  return (
    <div className="telemetry-card">
      <div className="section-header">
        <span>Navigation Telemetry</span>
        {/* Planner Mode Switcher (§5.2) */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            className={`mc-btn ${activeMode === 'safest' ? 'mc-btn-active' : ''}`}
            style={{ padding: '2px 8px', fontSize: '11px' }}
            onClick={() => setActiveMode('safest')}
          >
            <Shield size={12} color="var(--safe)" />
            SAFEST
          </button>
          <button
            className={`mc-btn ${activeMode === 'shortest' ? 'mc-btn-active' : ''}`}
            style={{ padding: '2px 8px', fontSize: '11px' }}
            onClick={() => setActiveMode('shortest')}
          >
            <Zap size={12} color="var(--hazard)" />
            SHORTEST
          </button>
        </div>
      </div>

      {!isSuccess ? (
        <div style={{ padding: '8px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--hazard)', borderRadius: '4px', color: 'var(--hazard)', fontSize: '12px' }}>
          Route unavailable — {failureReason}
        </div>
      ) : (
        <>
          {/* Primary KPI Row (§5.2) */}
          <div className="kpi-grid">
            <div className="kpi-cell">
              <span className="unit-label">TOTAL DISTANCE</span>
              <div className="kpi-number" style={{ color: activeMode === 'safest' ? 'var(--safe)' : 'var(--text-primary)' }}>
                {formatValue(metrics.total_distance, 1)}
              </div>
              <span className="unit-label">METERS</span>
            </div>

            <div className="kpi-cell">
              <span className="unit-label">AVG TERRAIN COST</span>
              <div className="kpi-number">
                {formatValue(metrics.avg_terrain_cost, 2)}
              </div>
              <span className="unit-label">UNITS</span>
            </div>

            <div className="kpi-cell">
              <span className="unit-label">CAUTION STEPS</span>
              <div
                className="kpi-number"
                style={{ color: metrics.caution_steps > 0 ? 'var(--caution)' : 'var(--safe)' }}
              >
                {metrics.caution_steps ?? '—'}
              </div>
              <span className="unit-label">&gt; 2.0x SLIP/SLOPE</span>
            </div>
          </div>

          {/* Secondary Rows (§5.2) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '4px' }}>
            <div className="kpi-cell">
              <span className="unit-label">MAX CELL COST</span>
              <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
                {formatValue(metrics.max_cell_cost, 1)}
              </span>
            </div>

            <div className="kpi-cell">
              <span className="unit-label">TOTAL STEPS</span>
              <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
                {metrics.step_count ?? '—'}
              </span>
            </div>

            <div className="kpi-cell">
              <span className="unit-label">EXPLORED NODES</span>
              <span className="mono" style={{ fontSize: '13px', fontWeight: 600 }}>
                {currentRouteData?.route?.nodes_explored ?? '—'}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
