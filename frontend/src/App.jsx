import React, { useState, useEffect, useCallback } from 'react';
import {
  getTerrain,
  compareRoutes,
  getScienceTargets,
  getMissionTelemetry,
  getMissionReport,
} from './api/client';

import MissionOverview from './components/MissionOverview';
import NavigationMap from './components/NavigationMap';
import RouteMetrics from './components/RouteMetrics';
import RoverSimulation from './components/RoverSimulation';
import ScienceTargets from './components/ScienceTargets';
import TargetDetails from './components/TargetDetails';
import TerrainExplorer from './components/TerrainExplorer';
import MissionReport from './components/MissionReport';

export default function App() {
  const [terrain, setTerrain] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [scienceData, setScienceData] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [routeComparison, setRouteComparison] = useState(null);
  const [inspectedCell, setInspectedCell] = useState(null);
  const [simulationStep, setSimulationStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const roverPos = telemetry?.rover_position || [2, 2];

  // Load initial mission payload
  useEffect(() => {
    async function initMission() {
      try {
        setLoading(true);
        const [terrainRes, telemRes, sciRes] = await Promise.all([
          getTerrain(),
          getMissionTelemetry(),
          getScienceTargets(2, 2),
        ]);

        setTerrain(terrainRes);
        setTelemetry(telemRes);
        setScienceData(sciRes);

        // Select top ranked target by default
        if (sciRes?.targets?.length > 0) {
          const topTgt = sciRes.targets[0];
          setSelectedTarget(topTgt);

          // Calculate initial trajectory to top target
          const routeRes = await compareRoutes([2, 2], topTgt.location);
          setRouteComparison(routeRes);
        }
      } catch (err) {
        console.error('Mission initialization error:', err);
        setError('Failed to initialize communication with MARS-09 Flight Controller.');
      } finally {
        setLoading(false);
      }
    }

    initMission();
  }, []);

  // Update route when a new target or goal is selected
  const handleSelectTarget = useCallback(
    async (tgt) => {
      setSelectedTarget(tgt);
      setSimulationStep(0);
      setInspectedCell({ row: tgt.location[0], col: tgt.location[1] });

      if (tgt.operational_priority === 0.0) {
        // Target is gated/unreachable
        if (tgt.route_details) {
          setRouteComparison(tgt.route_details);
        } else {
          try {
            const res = await compareRoutes(roverPos, tgt.location);
            setRouteComparison(res);
          } catch (e) {
            console.error(e);
          }
        }
        return;
      }

      try {
        const res = await compareRoutes(roverPos, tgt.location);
        setRouteComparison(res);
      } catch (err) {
        console.error('Route calculation failed:', err);
      }
    },
    [roverPos]
  );

  // Handle clicking on map cells to inspect or navigate
  const handleCellClick = useCallback(
    async (row, col) => {
      setInspectedCell({ row, col });

      // Check if clicked cell matches an existing target
      const match = scienceData?.targets?.find(
        (t) => t.location[0] === row && t.location[1] === col
      );
      if (match) {
        handleSelectTarget(match);
      }
    },
    [scienceData, handleSelectTarget]
  );

  // Set inspected arbitrary cell as new destination
  const handleSetCustomGoal = useCallback(
    async ([row, col]) => {
      setSimulationStep(0);
      try {
        const res = await compareRoutes(roverPos, [row, col]);
        setRouteComparison(res);
      } catch (err) {
        console.error('Custom route comparison failed:', err);
      }
    },
    [roverPos]
  );

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '1rem' }}>
        <div className="mono" style={{ color: 'var(--cyan-safe)', fontSize: '1.2rem', letterSpacing: '0.1em' }}>
          INITIALIZING MARS-09 ODYSSEY FLIGHT TELEMETRY...
        </div>
        <div style={{ width: '200px', height: '3px', background: 'rgba(255, 112, 67, 0.2)', overflow: 'hidden' }}>
          <div style={{ width: '50%', height: '100%', background: 'var(--mars-rust)', animation: 'pulse 1s infinite alternate' }} />
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* 1. Top Mission Telemetry HUD */}
      <MissionOverview telemetry={telemetry} activeTarget={selectedTarget} />

      {error && (
        <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 23, 68, 0.2)', border: '1px solid #ff1744', borderRadius: '4px', color: '#ff1744', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* 2. Main Grid: Left = Navigation Canvas & Route Telemetry, Right = Science Intelligence */}
      <div className="dashboard-grid">
        {/* Left Column: Tactical Navigation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <NavigationMap
            terrain={terrain}
            routeComparison={routeComparison}
            roverPos={roverPos}
            activeTarget={selectedTarget}
            allTargets={scienceData?.targets || []}
            onCellClick={handleCellClick}
            simulationStep={simulationStep}
          />

          <RoverSimulation
            routeComparison={routeComparison}
            terrain={terrain}
            currentStep={simulationStep}
            onStepChange={setSimulationStep}
          />

          <RouteMetrics routeComparison={routeComparison} />
        </div>

        {/* Right Column: Science Intelligence & Inspection */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <ScienceTargets
            targets={scienceData?.targets || []}
            selectedTargetId={selectedTarget?.id}
            onSelectTarget={handleSelectTarget}
          />

          <TargetDetails target={selectedTarget} />

          <TerrainExplorer
            inspectedCell={inspectedCell}
            terrain={terrain}
            onSetAsGoal={handleSetCustomGoal}
          />

          <MissionReport reportMarkdown={scienceData?.overall_recommendation} />
        </div>
      </div>
    </div>
  );
}
