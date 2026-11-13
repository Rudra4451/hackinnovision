import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getTerrain = async () => {
  const response = await api.get('/api/navigation/terrain');
  return response.data;
};

export const compareRoutes = async (start, goal, customCostMap = null) => {
  const payload = {
    start: [start[0], start[1]],
    goal: [goal[0], goal[1]],
    use_custom_cost_map: !!customCostMap,
    custom_cost_map: customCostMap,
  };
  const response = await api.post('/api/navigation/compare', payload);
  return response.data;
};

export const getScienceTargets = async (roverR = 2, roverC = 2) => {
  const response = await api.get('/api/science/targets', {
    params: { rover_r: roverR, rover_c: roverC },
  });
  return response.data;
};

export const getTargetDetail = async (targetId, roverR = 2, roverC = 2) => {
  const response = await api.get(`/api/science/targets/${targetId}`, {
    params: { rover_r: roverR, rover_c: roverC },
  });
  return response.data;
};

export const getMissionTelemetry = async () => {
  const response = await api.get('/api/mission/telemetry');
  return response.data;
};

export const getMissionReport = async (roverR = 2, roverC = 2) => {
  const response = await api.get('/api/science/report', {
    params: { rover_r: roverR, rover_c: roverC },
  });
  return response.data;
};

export default api;
