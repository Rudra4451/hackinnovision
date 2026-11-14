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
} from 'lucide-react';
import axios from 'axios';

const BACKEND_BASE = 'http://127.0.0.1:8000';

const SEMANTIC_CLASSES = [
  { name: 'ROCK', color: '#808080', desc: 'Outcrops & boulders' },
  { name: 'SAND', color: '#EDC989', desc: 'Dunes & aeolian ripples' },
  { name: 'SOIL', color: '#B85032', desc: 'Martian oxidized regolith' },
  { name: 'VEGETATION', color: '#2ECC71', desc: 'Terrestrial biomass' },
  { name: 'WATER', color: '#3498DB', desc: 'Liquid bodies' },
  { name: 'OBSTACLE', color: '#E74C3C', desc: 'Impassable hazards' },
  { name: 'UNKNOWN', color: '#6C3483', desc: 'Shadows / glare / unclassified' },
];

export default function VisionScoreDashboard() {
  const [environment, setEnvironment] = useState('MARS');
  const [viewMode, setViewMode] = useState('overlay'); // 'overlay' | 'frame' | 'mask' | 'side-by-side'
  const [isStreaming, setIsStreaming] = useState(true);
  const [isInjectingObstacle, setIsInjectingObstacle] = useState(false);
  const [currentFrameData, setCurrentFrameData] = useState(null);
  const [segmentationData, setSegmentationData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const fileInputRef = useRef(null);
  const pollingTimerRef = useRef(null);

  // 1. Fetch Latest Camera Frame & Run Detection
  const fetchCameraFrame = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_BASE}/api/visionscore/camera/frame`, {
        params: { environment, include_segmentation: true },
        timeout: 4000,
      });
      setCurrentFrameData(res.data);
      if (res.data.alert) {
        // Refresh alerts feed on new alert
        fetchAlerts();
      }
      setErrorMessage(null);
    } catch (err) {
      // Fallback message if backend isn't actively running
      if (!errorMessage) {
        setErrorMessage('Connecting to VisionScore 2.0 backend on :8000...');
      }
    }
  }, [environment, errorMessage]);

  // 2. Fetch Alerts List
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_BASE}/api/visionscore/alerts`, {
        params: { limit: 20 },
        timeout: 3000,
      });
      setAlerts(res.data.alerts || []);
      if (!selectedAlert && res.data.alerts?.length > 0) {
        setSelectedAlert(res.data.alerts[0]);
      }
    } catch (err) {
      console.warn('Could not retrieve alerts feed:', err.message);
    }
  }, [selectedAlert]);

  // Polling loop for live camera frame
  useEffect(() => {
    fetchCameraFrame();
    fetchAlerts();

    if (isStreaming) {
      pollingTimerRef.current = setInterval(() => {
        fetchCameraFrame();
      }, 1500);
    }
    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [isStreaming, fetchCameraFrame, fetchAlerts]);

  // 3. Toggle Simulated Obstacle in Feed
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

  // 4. Handle Image File Upload
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setErrorMessage(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('environment', environment);
    formData.append('include_preview', 'true');

    try {
      const res = await axios.post(`${BACKEND_BASE}/api/visionscore/segment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 8000,
      });
      setSegmentationData(res.data);
      setCurrentFrameData((prev) => ({
        ...prev,
        frame_data_uri: res.data.original_data_uri,
        overlay_data_uri: res.data.overlay_data_uri,
        dominant_class: res.data.dominant_class,
        class_percentages: res.data.class_pixel_percentages,
      }));
      fetchAlerts();
    } catch (err) {
      setErrorMessage(`Upload segmentation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 5. Handle Verification Status Update
  const handleVerifyAlert = async (eventId, status) => {
    try {
      await axios.post(`${BACKEND_BASE}/api/visionscore/alerts/${eventId}/verify`, {
        status,
        notes: `Operator verification via Dark Space HUD at ${new Date().toISOString()}`,
      });
      fetchAlerts();
      if (selectedAlert?.event_id === eventId) {
        setSelectedAlert((prev) => ({ ...prev, verification_status: status }));
      }
    } catch (err) {
      console.error('Failed to verify alert:', err);
    }
  };

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
        {/* Left: Environment Profile & Stream Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Camera size={16} color="var(--rover)" />
            <span style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '0.04em' }}>
              VISIONSCORE 2.0
            </span>
          </div>

          {/* Environment Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-primary)', padding: '2px 4px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '0 4px' }}>PROFILE:</span>
            {['MARS', 'EARTH', 'SIMULATION'].map((env) => (
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

          {/* Stream Controls */}
          <button
            onClick={() => setIsStreaming(!isStreaming)}
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
            {isStreaming ? 'STREAM ACTIVE' : 'STREAM PAUSED'}
          </button>
        </div>

        {/* Right: Trigger Obstacle Simulation & Upload */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleToggleObstacle}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: isInjectingObstacle ? 'rgba(231, 76, 60, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              color: isInjectingObstacle ? '#FF6B6B' : 'var(--text-primary)',
              border: `1px solid ${isInjectingObstacle ? '#E74C3C' : 'var(--border-subtle)'}`,
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <ShieldAlert size={13} color={isInjectingObstacle ? '#FF6B6B' : 'var(--caution)'} />
            {isInjectingObstacle ? 'SIMULATED OBSTACLE INJECTED' : 'INJECT OBSTACLE TEST'}
          </button>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="image/*"
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <Upload size={12} />
            UPLOAD IMAGE
          </button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* MAIN SPLIT WORKSPACE: Left (Viewer) & Right (Alerts Stack)    */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left Column: Live Viewport & Semantic Viewer */}
        <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--border-subtle)', overflowY: 'auto', padding: '16px', gap: '16px' }}>
          {/* View Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-surface)', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              {[
                { id: 'overlay', label: 'Semantic Overlay', icon: Layers },
                { id: 'frame', label: 'Clean Camera Frame', icon: Eye },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setViewMode(m.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: viewMode === m.id ? 'var(--rover)' : 'transparent',
                    color: viewMode === m.id ? '#000' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <m.icon size={13} />
                  {m.label}
                </button>
              ))}
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
              padding: '10px 14px',
              color: '#FF6B6B',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} />
                <span>
                  <strong>CRITICAL HAZARD DETECTED:</strong> High-contrast obstacle in path. Auto-capture triggered.
                </span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
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
            minHeight: '340px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}>
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', color: 'var(--rover)' }}>
                <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>SEGMENTING TERRAIN PIXELS...</span>
              </div>
            ) : currentFrameData ? (
              <img
                src={
                  viewMode === 'overlay' && currentFrameData.overlay_data_uri
                    ? currentFrameData.overlay_data_uri
                    : currentFrameData.frame_data_uri
                }
                alt="VisionScore Feed"
                style={{ width: '100%', height: 'auto', maxHeight: '480px', objectFit: 'contain', display: 'block' }}
              />
            ) : (
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                Awaiting camera stream initialization...
              </div>
            )}
          </div>

          {/* Semantic Classes Distribution & Legend */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
              <span>SEMANTIC CLASS DISTRIBUTION</span>
              <span style={{ fontSize: '10px' }}>ALGORITHMIC DEMO MODEL (PSM-TCS)</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              {SEMANTIC_CLASSES.map((cls) => {
                const pct = currentFrameData?.class_percentages?.[cls.name] ?? 0;
                return (
                  <div key={cls.name} style={{ background: 'var(--bg-primary)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: cls.color }} />
                        <span style={{ fontSize: '11px', fontWeight: 600 }}>{cls.name}</span>
                      </div>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                        {pct.toFixed(1)}%
                      </span>
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
        <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg-surface)', overflowY: 'auto', padding: '16px', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={16} color="var(--caution)" />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>OBSTACLE ALERTS FEED</span>
            </div>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              {alerts.length} CAPTURED
            </span>
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
                <div style={{ width: '100%', height: '140px', background: '#090D14', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px' }}>
                  <img
                    src={`${BACKEND_BASE}/${selectedAlert.annotated_path}`}
                    alt="Alert Preview"
                    onError={(e) => {
                      // Fallback if image path relative
                      e.target.style.display = 'none';
                    }}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                </div>
              )}

              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 10px 0' }}>
                {selectedAlert.explanation}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)', marginBottom: '12px' }}>
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
              EVENT HISTORY LOG
            </span>
            {alerts.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '11px' }}>
                No obstacle events triggered. System operating nominally.
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

