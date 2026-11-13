import React from 'react';
import { Layers, Eye, EyeOff, Sliders } from 'lucide-react';

export default function TerrainControls({
  overlays,
  onChangeOverlay,
  displayScale,
  onChangeDisplayScale,
  isLockedCamera,
  onToggleLockCamera,
}) {
  return (
    <div className="mc-overlay-toolbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)', fontWeight: 600, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        <Layers size={14} color="var(--rover)" />
        <span>Overlays</span>
      </div>

      <label className="mc-toolbar-item">
        <input
          type="checkbox"
          checked={overlays.route}
          onChange={(e) => onChangeOverlay('route', e.target.checked)}
        />
        <span>Route</span>
      </label>

      <label className="mc-toolbar-item">
        <input
          type="checkbox"
          checked={overlays.hazards}
          onChange={(e) => onChangeOverlay('hazards', e.target.checked)}
        />
        <span style={{ color: 'var(--hazard)' }}>Hazards</span>
      </label>

      <label className="mc-toolbar-item">
        <input
          type="checkbox"
          checked={overlays.caution}
          onChange={(e) => onChangeOverlay('caution', e.target.checked)}
        />
        <span style={{ color: 'var(--caution)' }}>Caution</span>
      </label>

      <label className="mc-toolbar-item">
        <input
          type="checkbox"
          checked={overlays.rover}
          onChange={(e) => onChangeOverlay('rover', e.target.checked)}
        />
        <span style={{ color: 'var(--rover)' }}>Rover</span>
      </label>

      <label className="mc-toolbar-item">
        <input
          type="checkbox"
          checked={overlays.contours}
          onChange={(e) => onChangeOverlay('contours', e.target.checked)}
        />
        <span>Contours</span>
      </label>

      <div style={{ width: '1px', height: '16px', background: 'var(--border-subtle)' }} />

      <div className="mc-exaggeration-slider">
        <Sliders size={13} />
        <span>Z Scale:</span>
        <input
          type="range"
          min="0.5"
          max="3.0"
          step="0.1"
          value={displayScale}
          onChange={(e) => onChangeDisplayScale(parseFloat(e.target.value))}
          title="Display Vertical Exaggeration (Display only, does not alter DEM measurements)"
        />
        <span className="mc-badge-scale">{displayScale.toFixed(1)}× DISPLAY SCALE</span>
      </div>
    </div>
  );
}
