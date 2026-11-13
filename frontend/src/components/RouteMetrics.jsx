import React from 'react';
import { Shield, Zap, TrendingDown, AlertCircle, Compass, CheckCircle } from 'lucide-react';

export default function RouteMetrics({ routeComparison }) {
  if (!routeComparison) {
    return (
      <div className="hud-panel">
        <div className="hud-panel-title">
          <Zap size={18} />
          Autonomous Trajectory Telemetry
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
          Select a destination or science target on the map to compute dual-route telemetry.
        </div>
      </div>
    );
  }

  const { shortest, safest, summary } = routeComparison;
  const sMetrics = shortest?.metrics || {};
  const safeMetrics = safest?.metrics || {};

  return (
    <div className="hud-panel">
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Zap size={18} />
          Route Risk Analysis & Telemetry Trade-Off
        </div>
        {summary?.both_reachable ? (
          <span className="badge badge-optimal">
            <CheckCircle size={12} />
            Dual Trajectory Solved
          </span>
        ) : (
          <span className="badge badge-gated">
            <AlertCircle size={12} />
            Unreachable / Hazard Lock
          </span>
        )}
      </div>

      {/* Comparison Telemetry Table */}
      <table className="targets-table">
        <thead>
          <tr>
            <th>Telemetry Parameter</th>
            <th style={{ color: '#ff1744' }}>Shortest Route</th>
            <th style={{ color: '#00f0ff' }}>Safest Route</th>
            <th style={{ textAlign: 'right' }}>Trade-Off Delta</th>
          </tr>
        </thead>
        <tbody className="mono">
          <tr>
            <td>Total Traverse Distance</td>
            <td>{sMetrics.total_distance?.toFixed(2)} m</td>
            <td style={{ color: '#00f0ff', fontWeight: 600 }}>
              {safeMetrics.total_distance?.toFixed(2)} m
            </td>
            <td style={{ textAlign: 'right', color: summary?.distance_delta > 0 ? '#ffb300' : '#00e676' }}>
              +{summary?.distance_delta?.toFixed(2)} m ({summary?.distance_penalty_pct?.toFixed(1)}%)
            </td>
          </tr>
          <tr>
            <td>Accumulated Risk Cost</td>
            <td>{sMetrics.total_cost?.toFixed(2)}</td>
            <td style={{ color: '#00f0ff', fontWeight: 600 }}>
              {safeMetrics.total_cost?.toFixed(2)}
            </td>
            <td style={{ textAlign: 'right', color: '#00f0ff', fontWeight: 600 }}>
              -{summary?.cost_reduction_pct?.toFixed(1)}% Cost
            </td>
          </tr>
          <tr>
            <td>Caution Steps (&gt;2.0 Cost)</td>
            <td style={{ color: sMetrics.caution_steps > 0 ? '#ffb300' : 'inherit' }}>
              {sMetrics.caution_steps} steps
            </td>
            <td style={{ color: '#00f0ff' }}>
              {safeMetrics.caution_steps} steps
            </td>
            <td style={{ textAlign: 'right', color: '#00e676', fontWeight: 600 }}>
              {summary?.caution_steps_avoided} Avoided
            </td>
          </tr>
          <tr>
            <td>Mean Cell Terrain Cost</td>
            <td>{sMetrics.avg_terrain_cost?.toFixed(2)}</td>
            <td style={{ color: '#00f0ff' }}>{safeMetrics.avg_terrain_cost?.toFixed(2)}</td>
            <td style={{ textAlign: 'right' }}>
              {(sMetrics.avg_terrain_cost - safeMetrics.avg_terrain_cost).toFixed(2)}
            </td>
          </tr>
          <tr>
            <td>Max Single-Cell Hazard</td>
            <td>{sMetrics.max_cell_cost?.toFixed(1)}</td>
            <td style={{ color: '#00f0ff' }}>{safeMetrics.max_cell_cost?.toFixed(1)}</td>
            <td style={{ textAlign: 'right' }}>-</td>
          </tr>
        </tbody>
      </table>

      {/* Summary Stat Boxes */}
      <div className="tradeoff-metrics-grid">
        <div className="tradeoff-stat-box">
          <div className="stat-val" style={{ color: '#00f0ff' }}>
            {summary?.cost_reduction_pct?.toFixed(1)}%
          </div>
          <div className="stat-label">Risk Reduction</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val" style={{ color: '#00e676' }}>
            {summary?.caution_steps_avoided}
          </div>
          <div className="stat-label">Caution Steps Avoided</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val" style={{ color: '#ffb300' }}>
            +{summary?.distance_delta?.toFixed(1)} m
          </div>
          <div className="stat-label">Detour Distance</div>
        </div>

        <div className="tradeoff-stat-box">
          <div className="stat-val mono" style={{ color: '#f0f4f8' }}>
            {safest?.route?.nodes_explored || 0}
          </div>
          <div className="stat-label">A* Nodes Explored</div>
        </div>
      </div>

      {/* Mission Recommendation Callout */}
      <div className="route-tradeoff-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--cyan-safe)', fontWeight: 600, fontSize: '0.8rem', textTransform: 'uppercase' }}>
          <Shield size={14} />
          MARS-09 Flight Controller Recommendation
        </div>
        <p style={{ marginTop: '0.4rem', fontSize: '0.82rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
          {summary?.recommendation}
        </p>
      </div>
    </div>
  );
}
