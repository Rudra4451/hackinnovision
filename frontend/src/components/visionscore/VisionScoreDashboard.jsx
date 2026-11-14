import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Camera,
  AlertTriangle,
  Layers,
  Upload,
  Play,
  Pause,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Eye,
  ShieldAlert,
  Sliders,
  Clock,
  Sparkles,
  Download,
  RotateCcw,
  Compass,
  Filter,
  Trash2,
  Columns,
} from 'lucide-react';
import axios from 'axios';

const BACKEND_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Mars AI4Mars NASA JPL Benchmark Taxonomy (Active Supported vs Planned Models)
const SEMANTIC_CLASSES = [
  { name: 'SOIL', labelId: 0, color: '#B85032', desc: 'Oxidized regolith plains & cohesive soil', active: true, traction: 'Nominal (Safe)' },
  { name: 'BEDROCK', labelId: 1, color: '#6B7280', desc: 'Solid exposed rock pavement & basement strata', active: true, traction: 'High (Safe)' },
  { name: 'SAND', labelId: 2, color: '#EDC989', desc: 'Aeolian dunes, ripples & drift sheets', active: true, traction: 'Low (Slip Risk)' },
  { name: 'BOULDER', labelId: 3, color: '#4B5563', desc: 'Large discrete rock hazards & morphological blocks', active: true, traction: 'Hazard (Collision)' },
  { name: 'UNKNOWN', labelId: 255, color: '#6C3483', desc: 'Shadows / glare / unclassified regions', active: true, traction: 'Uncertain' },
  { name: 'REGOLITH', labelId: null, color: '#C2410C', desc: 'Weathered mantle (Planned model)', active: false, traction: 'Planned' },
  { name: 'DUST', labelId: null, color: '#F59E0B', desc: 'Fine atmospheric fallout mantle (Planned)', active: false, traction: 'Planned' },
  { name: 'CRATER', labelId: null, color: '#431407', desc: 'Impact rim & depression walls (Planned)', active: false, traction: 'Planned' },
];

export default function VisionScoreDashboard() {
  const [environment, setEnvironment] = useState('MARS');
  const [terrainMode, setTerrainMode] = useState('MIXED'); // 'MIXED' | 'SOIL' | 'BEDROCK' | 'SAND' | 'BOULDER'
  const [viewMode, setViewMode] = useState('overlay'); // 'overlay' | 'mask' | 'frame' | 'side-by-side'
  const [isStreaming, setIsStreaming] = useState(true);
  const [isInjectingObstacle, setIsInjectingObstacle] = useState(false);
  const [hazardFilterOnly, setHazardFilterOnly] = useState(false);
  const [selectedTerrainFilter, setSelectedTerrainFilter] = useState('ALL'); // 'ALL' | 'SOIL' | 'BEDROCK' | 'SAND' | 'BOULDER' | 'UNKNOWN'
  const [alertStatusFilter, setAlertStatusFilter] = useState('ALL'); // 'ALL' | 'UNVERIFIED' | 'CONFIRMED' | 'FALSE_POSITIVE'

  const [currentFrameData, setCurrentFrameData] = useState(null);
  const [isUploadedImage, setIsUploadedImage] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const fileInputRef = useRef(null);
  const pollingTimerRef = useRef(null);

  // 1. Fetch Latest Camera Frame & Run Detection
  const fetchCameraFrame = useCallback(async () => {
    if (isUploadedImage) return; // Do not overwrite user-uploaded image during live polling

    try {
      const res = await axios.get(`${BACKEND_BASE}/api/visionscore/camera/frame`, {
        params: { environment, terrain_mode: terrainMode, include_segmentation: true },
        timeout: 4000,
      });
      setCurrentFrameData(res.data);
      if (res.data.alert) {
        fetchAlerts();
      }
      setErrorMessage(null);
    } catch (err) {
      if (!errorMessage) {
        setErrorMessage('Connecting to VisionScore 2.0 backend on :8000...');
      }
    }
  }, [environment, terrainMode, isUploadedImage, errorMessage]);

  // 2. Fetch Alerts List
  const fetchAlerts = useCallback(async () => {
    try {
      const params = { limit: 30 };
      if (alertStatusFilter !== 'ALL') {
        params.status = alertStatusFilter;
      }
      const res = await axios.get(`${BACKEND_BASE}/api/visionscore/alerts`, {
        params,
        timeout: 3000,
      });
      setAlerts(res.data.alerts || []);
      if (!selectedAlert && res.data.alerts?.length > 0) {
        setSelectedAlert(res.data.alerts[0]);
      }
    } catch (err) {
      console.warn('Could not retrieve alerts feed:', err.message);
    }
  }, [alertStatusFilter, selectedAlert]);

  // Polling loop for live camera frame
  useEffect(() => {
    fetchCameraFrame();
    fetchAlerts();

    if (isStreaming && !isUploadedImage) {
      pollingTimerRef.current = setInterval(() => {
        fetchCameraFrame();
      }, 1500);
    }
    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [isStreaming, isUploadedImage, fetchCameraFrame, fetchAlerts]);

  // 3. Switch Camera Terrain Profile
  const handleSelectTerrainMode = async (mode) => {
    setTerrainMode(mode);
    setIsUploadedImage(false);
    try {
      await axios.post(`${BACKEND_BASE}/api/visionscore/camera/terrain`, null, {
        params: { mode },
      });
      fetchCameraFrame();
    } catch (err) {
      console.error('Failed to set terrain mode:', err);
    }
  };

  // 4. Toggle Simulated Obstacle in Feed
  const handleToggleObstacle = async () => {
    try {
      const nextState = !isInjectingObstacle;
      await axios.post(`${BACKEND_BASE}/api/visionscore/camera/trigger`, null, {
        params: { enable: nextState },
      });
      setIsInjectingObstacle(nextState);
      fetchCameraFrame();
    } catch (err) {
      console.error('Failed to toggle obstacle trigger:', err);
    }
  };

  // 5. Handle Image File Upload
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setErrorMessage(null);
    setIsUploadedImage(true);
    setIsStreaming(false); // Pause live stream on upload

    const formData = new FormData();
    formData.append('file', file);
    formData.append('environment', environment);
    formData.append('include_preview', 'true');

    try {
      const res = await axios.post(`${BACKEND_BASE}/api/visionscore/segment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 10000,
      });
      setCurrentFrameData({
        ...res.data,
        frame_data_uri: res.data.original_data_uri,
        overlay_data_uri: res.data.overlay_data_uri,
        color_map_data_uri: res.data.color_map_data_uri,
        dominant_class: res.data.dominant_class,
        class_percentages: res.data.class_pixel_percentages,
        risk_assessment: res.data.risk_assessment,
      });
      fetchAlerts();
    } catch (err) {
      setErrorMessage(`Upload segmentation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 6. Explicit Analyze Button
  const handleAnalyzeCurrentFrame = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${BACKEND_BASE}/api/visionscore/segment`, null, {
        params: { environment, include_preview: true },
        timeout: 8000,
      });
      setCurrentFrameData((prev) => ({
        ...prev,
        ...res.data,
        frame_data_uri: res.data.original_data_uri,
        overlay_data_uri: res.data.overlay_data_uri,
        color_map_data_uri: res.data.color_map_data_uri,
        dominant_class: res.data.dominant_class,
        class_percentages: res.data.class_pixel_percentages,
        risk_assessment: res.data.risk_assessment,
      }));
      fetchAlerts();
    } catch (err) {
      setErrorMessage(`Analysis failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 7. Reset Button: Clears uploads & filters, restores live feed
  const handleResetDashboard = () => {
    setIsUploadedImage(false);
    setSelectedTerrainFilter('ALL');
    setHazardFilterOnly(false);
    setViewMode('overlay');
    setIsStreaming(true);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    fetchCameraFrame();
  };

  // 8. Clear Alert History
  const handleClearAlerts = async () => {
    try {
      await axios.post(`${BACKEND_BASE}/api/visionscore/alerts/clear`);
      setAlerts([]);
      setSelectedAlert(null);
    } catch (err) {
      console.error('Failed to clear alerts:', err);
    }
  };

  // 9. Handle Verification Status Update
  const handleVerifyAlert = async (eventId, status) => {
    try {
      await axios.post(`${BACKEND_BASE}/api/visionscore/alerts/${eventId}/verify`, {
        status,
        notes: `Operator verification via Mars Mission HUD at ${new Date().toISOString()}`,
      });
      fetchAlerts();
      if (selectedAlert?.event_id === eventId) {
        setSelectedAlert((prev) => ({ ...prev, verification_status: status }));
      }
    } catch (err) {
      console.error('Failed to verify alert:', err);
    }
  };

  // 10. Export JSON Report
  const handleExportReport = () => {
    const reportData = {
      system: 'ARES VisionScore 2.0',
      timestamp: new Date().toISOString(),
      environment,
      terrainMode,
      telemetry: currentFrameData,
      activeAlertsCount: alerts.length,
      alerts,
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `visionscore_report_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const risk = currentFrameData?.risk_assessment;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)', color: 'var(--text-primary)', overflow: 'hidden' }}>
      {/* ───────────────────────────────────────────────────────────── */}
      {/* TOP HEADER CONTROLS                                           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        {/* Left: Subsystem Name, Environment & Stream Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <img src="/image_57d289.png" alt="ARES Logo" style={{ height: '20px', width: 'auto', objectFit: 'contain' }} />
            <span style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '0.04em' }}>
              ARES // VISIONSCORE 2.0
            </span>
          </div>

          {/* Profile Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-primary)', padding: '2px 4px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '0 4px' }}>ENV:</span>
            {['MARS', 'SIMULATION_MARS'].map((env) => (
              <button
                key={env}
                onClick={() => setEnvironment(env)}
                style={{
                  background: environment === env ? 'var(--rover)' : 'transparent',
                  color: environment === env ? '#000' : 'var(--text-secondary)',
                  border: 'none',
                  borderRadius: '3px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {env}
              </button>
            ))}
          </div>

          {/* Simulated Terrain Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-primary)', padding: '2px 4px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '0 4px' }}>FEED:</span>
            {['MIXED', 'SOIL', 'BEDROCK', 'SAND', 'BOULDER'].map((mode) => (
              <button
                key={mode}
                onClick={() => handleSelectTerrainMode(mode)}
                title={`Switch camera feed to synthetic ${mode} scene`}
                style={{
                  background: terrainMode === mode && !isUploadedImage ? 'rgba(6, 182, 212, 0.25)' : 'transparent',
                  color: terrainMode === mode && !isUploadedImage ? 'var(--rover)' : 'var(--text-secondary)',
                  border: `1px solid ${terrainMode === mode && !isUploadedImage ? 'var(--rover)' : 'transparent'}`,
                  borderRadius: '3px',
                  padding: '2px 6px',
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Stream Controls */}
          <button
            onClick={() => {
              if (isUploadedImage) {
                setIsUploadedImage(false);
                setIsStreaming(true);
                fetchCameraFrame();
              } else {
                setIsStreaming(!isStreaming);
              }
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: isStreaming ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: isStreaming ? 'var(--safe)' : 'var(--hazard)',
              border: `1px solid ${isStreaming ? 'var(--safe)' : 'var(--hazard)'}`,
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {isStreaming ? <Pause size={12} /> : <Play size={12} />}
            {isStreaming ? 'CAMERA ACTIVE' : isUploadedImage ? 'SHOW LIVE FEED' : 'CAMERA PAUSED'}
          </button>
        </div>

        {/* Right: Actions (Analyze, Reset, Refresh, Inject, Upload, Export) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <button
            onClick={handleAnalyzeCurrentFrame}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'rgba(6, 182, 212, 0.2)',
              color: 'var(--rover)',
              border: '1px solid var(--rover)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Sparkles size={12} />
            ANALYZE
          </button>

          <button
            onClick={fetchCameraFrame}
            title="Refresh current frame and telemetry"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={12} />
            REFRESH
          </button>

          <button
            onClick={handleResetDashboard}
            title="Reset analysis and restore nominal live feed"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--bg-primary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={12} />
            RESET
          </button>

          <button
            onClick={handleToggleObstacle}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: isInjectingObstacle ? 'rgba(231, 76, 60, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              color: isInjectingObstacle ? '#FF6B6B' : 'var(--text-primary)',
              border: `1px solid ${isInjectingObstacle ? '#E74C3C' : 'var(--border-subtle)'}`,
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <ShieldAlert size={12} color={isInjectingObstacle ? '#FF6B6B' : 'var(--caution)'} />
            {isInjectingObstacle ? 'OBSTACLE INJECTED' : 'INJECT OBSTACLE'}
          </button>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="image/*,.png,.jpg,.jpeg"
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <Upload size={12} />
            UPLOAD IMAGE
          </button>

          <button
            onClick={handleExportReport}
            title="Export full diagnostic report as JSON"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <Download size={12} />
            EXPORT
          </button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* MAIN SPLIT WORKSPACE: Left (Viewer) & Right (Alerts Stack)    */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left Column: Live Viewport & Semantic Viewer */}
        <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--border-subtle)', overflowY: 'auto', padding: '14px', gap: '12px' }}>
          
          {/* View Mode & Filter Switchers Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-surface)', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '6px' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {[
                { id: 'overlay', label: 'Semantic Overlay', icon: Layers },
                { id: 'mask', label: 'Segmentation Mask', icon: Sparkles },
                { id: 'frame', label: 'Original Frame', icon: Eye },
                { id: 'side-by-side', label: 'Side-by-Side', icon: Columns },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setViewMode(m.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: viewMode === m.id ? 'var(--rover)' : 'transparent',
                    color: viewMode === m.id ? '#000' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <m.icon size={12} />
                  {m.label}
                </button>
              ))}

              <button
                onClick={() => setHazardFilterOnly(!hazardFilterOnly)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: hazardFilterOnly ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                  color: hazardFilterOnly ? 'var(--hazard)' : 'var(--text-secondary)',
                  border: `1px solid ${hazardFilterOnly ? 'var(--hazard)' : 'var(--border-subtle)'}`,
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Filter size={12} />
                {hazardFilterOnly ? 'HAZARDS ISOLATED' : 'FILTER HAZARDS'}
              </button>
            </div>

            {/* Dominant Class Readout */}
            {currentFrameData?.dominant_class && (
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                DOMINANT: <strong style={{ color: 'var(--safe)' }}>{currentFrameData.dominant_class}</strong>
              </span>
            )}
          </div>

          {/* Active Obstacle Alert Banner */}
          {currentFrameData?.alert_active && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(231, 76, 60, 0.15)',
              border: '1px solid #E74C3C',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#FF6B6B',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={15} />
                <span>
                  <strong>{risk?.status || 'OBSTACLE DETECTED'}:</strong> {risk?.explanation || 'High-contrast morphological feature in path.'}
                </span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                ID: {currentFrameData.alert?.event_id || 'PENDING'}
              </span>
            </div>
          )}

          {/* Image Display Canvas */}
          <div style={{
            position: 'relative',
            background: '#090D14',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            minHeight: '320px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}>
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', color: 'var(--rover)' }}>
                <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>SEGMENTING TERRAIN PIXELS (AI4MARS)...</span>
              </div>
            ) : currentFrameData ? (
              viewMode === 'side-by-side' ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', width: '100%', height: '100%', gap: '4px' }}>
                  <div style={{ position: 'relative' }}>
                    <span style={{ position: 'absolute', top: 6, left: 6, background: 'rgba(0,0,0,0.7)', padding: '2px 6px', fontSize: '10px', borderRadius: '3px' }}>CAMERA FRAME</span>
                    <img
                      src={currentFrameData.frame_data_uri}
                      alt="Raw Camera"
                      style={{ width: '100%', height: 'auto', maxHeight: '420px', objectFit: 'contain', display: 'block' }}
                    />
                  </div>
                  <div style={{ position: 'relative' }}>
                    <span style={{ position: 'absolute', top: 6, left: 6, background: 'rgba(0,0,0,0.7)', padding: '2px 6px', fontSize: '10px', borderRadius: '3px' }}>SEMANTIC OVERLAY</span>
                    <img
                      src={currentFrameData.overlay_data_uri || currentFrameData.frame_data_uri}
                      alt="Overlay"
                      style={{ width: '100%', height: 'auto', maxHeight: '420px', objectFit: 'contain', display: 'block' }}
                    />
                  </div>
                </div>
              ) : (
                <img
                  src={
                    viewMode === 'mask' && currentFrameData.color_map_data_uri
                      ? currentFrameData.color_map_data_uri
                      : viewMode === 'overlay' && currentFrameData.overlay_data_uri
                      ? currentFrameData.overlay_data_uri
                      : currentFrameData.frame_data_uri
                  }
                  alt="VisionScore View"
                  style={{
                    width: '100%',
                    height: 'auto',
                    maxHeight: '420px',
                    objectFit: 'contain',
                    display: 'block',
                    filter: hazardFilterOnly ? 'contrast(1.3) saturate(1.4)' : 'none',
                  }}
                />
              )
            ) : (
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                Awaiting camera stream initialization...
              </div>
            )}
          </div>

          {/* Terrain Risk Assessment Card (Phase E) */}
          {risk && (
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  TERRAIN RISK ASSESSMENT (§PHASE E)
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '3px',
                  background:
                    risk.risk_level === 'SAFE'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : risk.risk_level === 'CAUTION' || risk.risk_level === 'LOW RISK'
                      ? 'rgba(245, 158, 11, 0.2)'
                      : 'rgba(239, 68, 68, 0.2)',
                  color:
                    risk.risk_level === 'SAFE'
                      ? 'var(--safe)'
                      : risk.risk_level === 'CAUTION' || risk.risk_level === 'LOW RISK'
                      ? 'var(--caution)'
                      : 'var(--hazard)',
                }}>
                  {risk.status} ({risk.risk_level})
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                <div>RISK SCORE: <strong>{risk.risk_score?.toFixed(2)}</strong> / 1.0</div>
                <div>CONFIDENCE: <strong>{(risk.confidence * 100).toFixed(0)}%</strong></div>
                <div>CORRIDOR: <strong style={{ color: risk.in_travel_corridor ? 'var(--hazard)' : 'var(--safe)' }}>{risk.in_travel_corridor ? 'INTERSECTING' : 'CLEAR'}</strong></div>
              </div>

              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '6px' }}>
                <strong>ACTION:</strong> <span style={{ color: 'var(--rover)' }}>{risk.recommended_action}</span> — {risk.explanation}
              </div>
            </div>
          )}

          {/* Semantic Classes Distribution & Filter Buttons (Phase B & C) */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
              <span>AI4MARS SEMANTIC TERRAIN CATEGORIES</span>
              <span style={{ fontSize: '10px' }}>CLICK TO FILTER & INSPECT SUBSTRATE</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              {SEMANTIC_CLASSES.map((cls) => {
                const pct = currentFrameData?.class_percentages?.[cls.name] ?? 0;
                const isSelected = selectedTerrainFilter === cls.name;
                return (
                  <div
                    key={cls.name}
                    onClick={() => {
                      if (cls.active) {
                        setSelectedTerrainFilter(selectedTerrainFilter === cls.name ? 'ALL' : cls.name);
                      }
                    }}
                    style={{
                      background: isSelected ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-primary)',
                      padding: '8px',
                      borderRadius: '4px',
                      border: `1px solid ${isSelected ? 'var(--rover)' : 'var(--border-subtle)'}`,
                      cursor: cls.active ? 'pointer' : 'default',
                      opacity: cls.active ? 1.0 : 0.6,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: cls.color }} />
                        <span style={{ fontSize: '11px', fontWeight: 600 }}>
                          {cls.name}
                          {cls.labelId !== null && <span style={{ fontSize: '9px', color: 'var(--text-secondary)', marginLeft: '3px' }}>[{cls.labelId}]</span>}
                          {!cls.active && <span style={{ fontSize: '9px', color: 'var(--text-secondary)', marginLeft: '3px' }}>(Ext)</span>}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                        {pct.toFixed(1)}%
                      </span>
                    </div>

                    <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      {cls.traction}
                    </div>

                    {/* Progress Bar */}
                    <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: cls.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Obstacle Alerts & Verification Stack */}
        <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg-surface)', overflowY: 'auto', padding: '14px', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={16} color="var(--caution)" />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>OBSTACLE ALERTS FEED</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <select
                value={alertStatusFilter}
                onChange={(e) => setAlertStatusFilter(e.target.value)}
                style={{
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '10px',
                }}
              >
                <option value="ALL">ALL STATUSES</option>
                <option value="UNVERIFIED">UNVERIFIED</option>
                <option value="CONFIRMED">CONFIRMED</option>
                <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
              </select>
              <button
                onClick={handleClearAlerts}
                title="Clear all alerts"
                style={{
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px',
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          {/* Selected Alert Detailed Card */}
          {selectedAlert && (
            <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--rover)' }}>
                  {selectedAlert.event_id}
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '3px',
                  background:
                    selectedAlert.verification_status === 'CONFIRMED'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : selectedAlert.verification_status === 'FALSE_POSITIVE'
                      ? 'rgba(239, 68, 68, 0.2)'
                      : 'rgba(245, 158, 11, 0.2)',
                  color:
                    selectedAlert.verification_status === 'CONFIRMED'
                      ? 'var(--safe)'
                      : selectedAlert.verification_status === 'FALSE_POSITIVE'
                      ? 'var(--hazard)'
                      : 'var(--caution)',
                }}>
                  {selectedAlert.verification_status}
                </span>
              </div>

              {/* Thumbnail */}
              {selectedAlert.annotated_path && (
                <div style={{ width: '100%', height: '130px', background: '#090D14', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px' }}>
                  <img
                    src={`${BACKEND_BASE}/${selectedAlert.annotated_path}`}
                    alt="Alert Preview"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                </div>
              )}

              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 10px 0' }}>
                {selectedAlert.explanation}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
                <div>CONFIDENCE: {(selectedAlert.confidence * 100).toFixed(0)}%</div>
                <div>COVERAGE: {selectedAlert.obstacle_area_pct?.toFixed(1)}%</div>
                <div>SOURCE: {selectedAlert.source}</div>
                <div>ENV: {selectedAlert.environment}</div>
              </div>

              {/* Verification Buttons */}
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={() => handleVerifyAlert(selectedAlert.event_id, 'CONFIRMED')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: 'var(--safe)',
                    border: '1px solid var(--safe)',
                    borderRadius: '4px',
                    padding: '6px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <CheckCircle2 size={12} /> CONFIRM
                </button>
                <button
                  onClick={() => handleVerifyAlert(selectedAlert.event_id, 'FALSE_POSITIVE')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    background: 'rgba(239, 68, 68, 0.15)',
                    color: 'var(--hazard)',
                    border: '1px solid var(--hazard)',
                    borderRadius: '4px',
                    padding: '6px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <XCircle size={12} /> FALSE POS
                </button>
              </div>
            </div>
          )}

          {/* List of Captured Events */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              EVENT HISTORY LOG ({alerts.length})
            </span>
            {alerts.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '11px', background: 'var(--bg-primary)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                No obstacle events recorded. Surface traversability nominal.
              </div>
            ) : (
              alerts.map((al) => (
                <div
                  key={al.event_id}
                  onClick={() => setSelectedAlert(al)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    background: selectedAlert?.event_id === al.event_id ? 'rgba(6, 182, 212, 0.1)' : 'var(--bg-primary)',
                    border: `1px solid ${selectedAlert?.event_id === al.event_id ? 'var(--rover)' : 'var(--border-subtle)'}`,
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                      {al.event_id.substring(0, 18)}...
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                      {new Date(al.timestamp).toLocaleTimeString()} · {al.source}
                    </div>
                  </div>
                  <span style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color:
                      al.verification_status === 'CONFIRMED'
                        ? 'var(--safe)'
                        : al.verification_status === 'FALSE_POSITIVE'
                        ? 'var(--hazard)'
                        : 'var(--caution)',
                  }}>
                    {al.verification_status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
