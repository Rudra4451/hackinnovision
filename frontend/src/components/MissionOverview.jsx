import React from 'react';
import { BatteryCharging, Compass, Radio, Sun, Thermometer, ShieldCheck, Cpu } from 'lucide-react';

export default function MissionOverview({ telemetry, activeTarget }) {
  const t = telemetry || {
    sol: 142,
    rover_name: 'A.R.E.S. MARS-09',
    rover_position: [2, 2],
    battery_level_pct: 94.2,
    solar_irradiance_w_m2: 582.4,
    chassis_temperature_c: -28.4,
    drive_motor_health: 'NOMINAL',
    spectrometer_status: 'CALIBRATED',
    active_navigation_mode: 'safest',
    comms_latency_sec: 874.1,
    mission_phase: 'PRIMARY_RECONNAISSANCE',
  };

  const commsMinutes = (t.comms_latency_sec / 60).toFixed(1);

  return (
    <header className="mission-header">
      <div className="mission-brand">
        <div className="mission-logo">
          <Cpu size={24} color="#fff" />
        </div>
        <div>
          <h1 className="mission-title">{t.rover_name}</h1>
          <div className="mission-subtitle">
            PLANETARY RECONNAISSANCE & AUTONOMOUS NAVIGATION // TRACK A
          </div>
        </div>
      </div>

      <div className="telemetry-strip">
        <div className="telemetry-item">
          <span className="telemetry-label">Mission Sol</span>
          <span className="telemetry-val mono" style={{ color: 'var(--mars-accent)' }}>
            SOL {t.sol}
          </span>
        </div>

        <div className="telemetry-item">
          <span className="telemetry-label">Rover Coordinates</span>
          <span className="telemetry-val mono">
            [{t.rover_position[0]}, {t.rover_position[1]}]
          </span>
        </div>

        <div className="telemetry-item">
          <span className="telemetry-label">Power Level</span>
          <span className="telemetry-val mono" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <BatteryCharging size={16} color="var(--cyan-safe)" />
            {t.battery_level_pct}%
          </span>
        </div>

        <div className="telemetry-item">
          <span className="telemetry-label">Thermal / Solar</span>
          <span className="telemetry-val mono">
            {t.chassis_temperature_c}°C / {t.solar_irradiance_w_m2.toFixed(0)} W/m²
          </span>
        </div>

        <div className="telemetry-item">
          <span className="telemetry-label">Earth Uplink Delay</span>
          <span className="telemetry-val mono" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Radio size={14} color="var(--amber-caution)" />
            {commsMinutes} min
          </span>
        </div>

        <div className="telemetry-item" style={{ alignItems: 'center' }}>
          <span className="badge badge-optimal">
            <ShieldCheck size={12} />
            {t.drive_motor_health}
          </span>
        </div>
      </div>
    </header>
  );
}
