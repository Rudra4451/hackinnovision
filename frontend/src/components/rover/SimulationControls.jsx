import React from 'react';
import { Play, Pause, RotateCcw, ChevronLeft, ChevronRight, Gauge } from 'lucide-react';

export default function SimulationControls({
  status,
  currentIndex,
  maxIndex,
  speed,
  progressPct,
  onStart,
  onPause,
  onStepForward,
  onStepBackward,
  onReset,
  onSeek,
  onChangeSpeed,
  disabled = false,
}) {
  const isRunning = status === 'RUNNING';

  return (
    <div className="telemetry-card">
      <div className="section-header">
        <span>Simulation Controls</span>
        <span className="mono unit-label">
          STEP {currentIndex} / {maxIndex}
        </span>
      </div>

      {/* Progress Track (§4.4) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div className="mc-sim-progress-track">
          <div className="mc-sim-progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <input
          type="range"
          min="0"
          max={maxIndex}
          value={currentIndex}
          onChange={(e) => onSeek(Number(e.target.value))}
          disabled={disabled || maxIndex === 0}
          style={{ width: '100%', accentColor: 'var(--rover)', cursor: 'pointer' }}
        />
      </div>

      {/* Control Buttons (§4.2) */}
      <div className="mc-controls-row">
        <div style={{ display: 'flex', gap: '6px' }}>
          {isRunning ? (
            <button className="mc-btn mc-btn-active" onClick={onPause} disabled={disabled}>
              <Pause size={14} />
              PAUSE
            </button>
          ) : (
            <button className="mc-btn" onClick={onStart} disabled={disabled || maxIndex === 0}>
              <Play size={14} />
              {status === 'PAUSED' ? 'RESUME' : 'START'}
            </button>
          )}

          <button className="mc-btn" onClick={onStepBackward} disabled={disabled || currentIndex <= 0} title="Step Back">
            <ChevronLeft size={14} />
          </button>

          <button className="mc-btn" onClick={onStepForward} disabled={disabled || currentIndex >= maxIndex} title="Step Forward">
            <ChevronRight size={14} />
          </button>

          <button className="mc-btn" onClick={onReset} disabled={disabled} title="Reset to Origin">
            <RotateCcw size={14} />
          </button>
        </div>

        {/* Speed Selector (0.5x, 1x, 2x, 4x) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Gauge size={13} color="var(--text-secondary)" />
          {[0.5, 1, 2, 4].map((s) => (
            <button
              key={s}
              className={`mc-btn ${speed === s ? 'mc-btn-active' : ''}`}
              style={{ padding: '2px 6px', fontSize: '11px', fontFamily: 'JetBrains Mono' }}
              onClick={() => onChangeSpeed(s)}
              disabled={disabled}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
