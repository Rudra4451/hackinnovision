import React, { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, FastForward, Navigation } from 'lucide-react';

export default function RoverSimulation({
  routeComparison,
  terrain,
  currentStep,
  onStepChange,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const path = routeComparison?.safest?.route?.path || [];
  const maxSteps = Math.max(0, path.length - 1);

  useEffect(() => {
    let interval = null;
    if (isPlaying) {
      interval = setInterval(() => {
        onStepChange((prev) => {
          if (prev >= maxSteps) {
            setIsPlaying(false);
            return maxSteps;
          }
          return prev + 1;
        });
      }, 150);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, maxSteps, onStepChange]);

  if (path.length === 0) return null;

  const activePos = path[currentStep] || path[0];
  const activeCost =
    terrain?.cost_map_display?.[activePos[0]]?.[activePos[1]] ?? 1.0;

  return (
    <div className="hud-panel" style={{ marginTop: '0.5rem' }}>
      <div className="hud-panel-header">
        <div className="hud-panel-title">
          <Navigation size={18} />
          Autonomous Rover Waypoint Traversal Simulator
        </div>
        <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--cyan-safe)' }}>
          WAYPOINT {currentStep} / {maxSteps} [{activePos[0]}, {activePos[1]}]
        </div>
      </div>

      <div className="simulation-bar">
        <button
          className="btn-tactical btn-cyan"
          style={{ padding: '0.4rem 0.8rem' }}
          onClick={() => setIsPlaying(!isPlaying)}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          {isPlaying ? 'PAUSE' : 'PLAY'}
        </button>

        <button
          className="btn-tactical"
          style={{ padding: '0.4rem 0.6rem' }}
          onClick={() => {
            setIsPlaying(false);
            onStepChange(0);
          }}
          title="Reset to Origin"
        >
          <RotateCcw size={16} />
        </button>

        <input
          type="range"
          min="0"
          max={maxSteps}
          value={currentStep}
          onChange={(e) => {
            setIsPlaying(false);
            onStepChange(Number(e.target.value));
          }}
          className="simulation-slider"
        />

        <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', minWidth: '140px', textAlign: 'right' }}>
          Cell Cost: <span style={{ color: activeCost > 2.0 ? '#ffb300' : '#00f0ff', fontWeight: 600 }}>{activeCost.toFixed(1)}</span> | 
          Prog: {Math.round((currentStep / Math.max(1, maxSteps)) * 100)}%
        </div>
      </div>
    </div>
  );
}
