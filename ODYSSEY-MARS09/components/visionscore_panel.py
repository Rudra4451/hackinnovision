"""
ODYSSEY MARS-09: Streamlit VisionScore 2.0 Component.
Provides visual semantic segmentation and automatic obstacle image alert feed.
"""

from datetime import datetime
import io
import numpy as np
from PIL import Image
import streamlit as st

from visionscore.config import EnvironmentProfile, SEMANTIC_COLOR_PALETTE, SemanticClass
from visionscore.image_input import SimulatedCameraFeed, UnifiedImage
from visionscore.obstacle_detector import get_obstacle_detector
from visionscore.semantic import segment_terrain

_STREAM_FEED = SimulatedCameraFeed(environment=EnvironmentProfile.MARS)


def render_visionscore_panel() -> None:
    """Renders the interactive VisionScore 2.0 and Obstacle Alert Dashboard in Streamlit."""
    st.subheader("👁️ VisionScore 2.0: Semantic Terrain Segmentation & Real-Time Obstacle Alerts")
    st.caption("Planetary Autonomous Computer Vision — Algorithmic Multi-Band Segmentation & Event Capture")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        env_choice = st.selectbox(
            "Operational Environment Profile",
            ["MARS", "EARTH", "SIMULATION"],
            index=0,
            key="vs_env_select",
        )
    with c2:
        inject_obstacle = st.toggle("Inject Simulated Obstacle", value=_STREAM_FEED.inject_obstacle, key="vs_inj_obs")
        _STREAM_FEED.set_obstacle_injection(inject_obstacle)
    with c3:
        uploaded_file = st.file_uploader("Upload External Terrain Image", type=["png", "jpg", "jpeg"], key="vs_upload")

    env_profile = EnvironmentProfile(env_choice)

    # 1. Ingest Image Frame
    if uploaded_file is not None:
        pil_img = Image.open(uploaded_file).convert("RGB")
        img_arr = np.array(pil_img)
        unified_img = UnifiedImage(
            image_id="uploaded_frame",
            image=img_arr,
            source="upload",
            environment=env_profile,
            timestamp=datetime.utcnow().isoformat(),
            metadata={"source": "Streamlit_Upload"},
        )
    else:
        # Pull from simulated camera feed
        raw_frame, meta = _STREAM_FEED.capture_frame()
        unified_img = UnifiedImage(
            image_id=f"sim_frame_{meta['frame_index']}",
            image=raw_frame,
            source="camera_frame",
            environment=env_profile,
            timestamp=datetime.utcnow().isoformat(),
            metadata=meta,
        )

    # 2. Run Semantic Segmentation
    seg_result = segment_terrain(unified_img, environment=env_profile)

    # 3. Run Automatic Obstacle Detection
    detector = get_obstacle_detector()
    alert = detector.process_frame(unified_img, segmentation=seg_result)

    # 4. Display Alert Banner if Triggered
    if alert:
        st.error(
            f"🚨 **OBSTACLE ALERT DETECTED [{alert.event_id}]**: "
            f"Confidence: {alert.confidence * 100:.1f}% | Surface Coverage: {alert.obstacle_area_pct:.1f}% | "
            f"Potential wheel-entrapment or rollover hazard."
        )

    # 5. Visual Views Split
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        st.markdown("**Original Camera Frame**")
        st.image(unified_img.image, use_container_width=True)

    with col_img2:
        st.markdown(f"**Semantic Overlay (Dominant: `{seg_result.dominant_class}`)**")
        st.image(seg_result.overlay_image, use_container_width=True)

    # 6. Semantic Class Distribution Bars
    st.write("---")
    st.subheader("Semantic Class Surface Area Distribution")
    cols = st.columns(len(SemanticClass))
    for idx, sc in enumerate(SemanticClass):
        pct = seg_result.class_pixel_percentages.get(sc.value, 0.0)
        color = SEMANTIC_COLOR_PALETTE[sc]
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        with cols[idx]:
            st.markdown(
                f"<div style='border-left: 4px solid {hex_color}; padding-left: 6px;'>"
                f"<strong>{sc.value}</strong><br>"
                f"<span style='font-size: 14px; font-family: monospace;'>{pct:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # 7. Obstacle Alerts Feed
    st.write("---")
    st.subheader("📋 Obstacle Event History & Verification")
    recent_alerts = detector.get_alerts(limit=5)
    if not recent_alerts:
        st.info("No obstacle events currently logged. MastCam feed indicates traversable conditions.")
    else:
        for al in recent_alerts:
            with st.expander(f"⚠️ {al.event_id} — {al.detection_category} ({al.verification_status})"):
                st.write(al.explanation)
                ca, cb = st.columns(2)
                with ca:
                    st.caption("Captured Moment")
                    st.image(al.captured_image, use_container_width=True)
                with cb:
                    st.caption("Diagnostic Annotation")
                    st.image(al.annotated_image, use_container_width=True)

                col_v1, col_v2 = st.columns(2)
                if col_v1.button("Confirm Hazard", key=f"btn_conf_{al.event_id}"):
                    detector.verify_alert(al.event_id, "CONFIRMED")
                    st.rerun()
                if col_v2.button("Mark False Positive", key=f"btn_fp_{al.event_id}"):
                    detector.verify_alert(al.event_id, "FALSE_POSITIVE")
                    st.rerun()

