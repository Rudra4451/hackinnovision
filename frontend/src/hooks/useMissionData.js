import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { validateTerrain } from '../utils/validateTerrain';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export function useMissionData(start = [2, 2], goal = [45, 45]) {
  const [dem, setDem] = useState(null);
  const [costMap, setCostMap] = useState(null);
  const [navigation, setNavigation] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMissionData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await axios.get(`${API_BASE}/api/mission`, {
        params: {
          start_r: start[0],
          start_c: start[1],
          goal_r: goal[0],
          goal_c: goal[1],
        },
        timeout: 12000,
      });

      const data = res.data;

      // 1. Validate DEM integrity
      const terrainValidation = validateTerrain(data.dem);
      setValidation(terrainValidation);

      if (!terrainValidation.isValid) {
        setError({
          type: 'INVALID_DEM',
          title: 'DEM Elevation Integrity Failure',
          message: terrainValidation.message,
          details: terrainValidation.errors,
          samples: terrainValidation.badSamples,
        });
        setDem(null);
        setCostMap(null);
        setNavigation(null);
        return;
      }

      // 2. Shape congruence check (§7.2, §8.1)
      const demRows = data.dem.rows;
      const demCols = data.dem.cols;
      const costRows = data.cost_map.rows;
      const costCols = data.cost_map.cols;

      if (demRows !== costRows || demCols !== costCols) {
        setError({
          type: 'GRID_MISMATCH',
          title: 'Spatial Dimension Mismatch',
          message: `Grid dimension mismatch: DEM is ${demRows}×${demCols}, but cost map is ${costRows}×${costCols}.`,
        });
        setDem(null);
        setCostMap(null);
        setNavigation(null);
        return;
      }

      // 3. Normalize "Infinity" string sentinels to JavaScript Infinity
      const normalizedCost = data.cost_map.cost.map((row) =>
        row.map((c) => (c === 'Infinity' ? Infinity : c === 'NaN' ? NaN : typeof c === 'number' ? c : parseFloat(c)))
      );

      setDem(data.dem);
      setCostMap({
        ...data.cost_map,
        cost: normalizedCost,
      });
      setNavigation(data.navigation);
    } catch (err) {
      console.error('[ARES] Mission data fetch failed:', err);
      setError({
        type: 'BACKEND_OFFLINE',
        title: 'Mission Control Telemetry Offline',
        message: err.response?.data?.detail || err.message || 'Unable to establish link with flight controller.',
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setLoading(false);
    }
  }, [start?.[0], start?.[1], goal?.[0], goal?.[1]]);

  useEffect(() => {
    fetchMissionData();
  }, [fetchMissionData]);

  const integrity = {
    demLoaded: !!dem,
    costMapLoaded: !!costMap,
    routeLoaded: !!navigation?.safest?.route?.success,
    timestamp: new Date().toLocaleTimeString(),
  };

  return {
    dem,
    costMap,
    navigation,
    validation,
    loading,
    error,
    reload: fetchMissionData,
    integrity,
  };
}
