"""
ODYSSEY VisionScore 2.0 Standalone Model Runner & Visual HTML Report Generator.

Run this script directly to execute the VisionScore 2.0 model, perform semantic terrain
segmentation, test automated obstacle alerts, and generate a self-contained interactive
HTML report viewable directly in any browser without external server setup.

Usage:
    python run_visionscore.py [--env MARS] [--image path/to/image.png] [--inject-obstacle]
"""

import argparse
import base64
from datetime import datetime, timezone
import io
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
from PIL import Image

from visionscore.config import (
    AlertConfig,
    EnvironmentProfile,
    SEMANTIC_COLOR_PALETTE,
    SemanticClass,
)
from visionscore.image_input import (
    ImageInputHandler,
    SimulatedCameraFeed,
    UnifiedImage,
)
from visionscore.obstacle_detector import ObstacleEventDetector
from visionscore.semantic import segment_terrain
from visionscore.terrain_integration import (
    evaluate_candidate_path_safety,
    integrate_visual_obstacle,
)
from core.terrain import build_terrain_intelligence


def array_to_base64_uri(arr: np.ndarray, format: str = "PNG") -> str:
    """Converts a NumPy RGB uint8 array to base64 Data URI."""
    pil = Image.fromarray(arr)
    buf = io.BytesIO()
    pil.save(buf, format=format)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def run_pipeline(
    environment: str = "MARS",
    image_path: str = None,
    inject_obstacle: bool = True,
    output_dir: str = "outputs/visionscore",
) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        env_profile = EnvironmentProfile(environment.upper())
    except ValueError:
        env_profile = EnvironmentProfile.MARS

    print(f"\n================================================================================")
    print(f"       ODYSSEY VISIONSCORE 2.0: AI TERRAIN MODEL EXECUTION & REPORT")
    print(f"================================================================================")
    print(f"[*] Environment Profile : {env_profile.value}")
    print(f"[*] Output Directory    : {out_path.resolve()}")

    # 1. Ingest image
    if image_path and Path(image_path).exists():
        print(f"[*] Ingesting custom image: {image_path}")
        handler = ImageInputHandler()
        unified_img = handler.load_from_path(image_path, environment=env_profile)
    else:
        print(f"[*] Generating high-fidelity mast camera frame (Obstacle Injection: {inject_obstacle})...")
        stream = SimulatedCameraFeed(environment=env_profile, inject_obstacle=inject_obstacle)
        raw_frame, meta = stream.capture_frame()
        unified_img = UnifiedImage(
            image_id=f"mastcam_{meta['frame_index']}",
            image=raw_frame,
            source="simulated_camera",
            environment=env_profile,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=meta,
        )

    # 2. Run Semantic Segmentation
    print(f"[*] Running Semantic Terrain Segmentation (PSM-TCS 2.0)...")
    seg_res = segment_terrain(unified_img, environment=env_profile)
    print(f"    - Dominant Class : {seg_res.dominant_class}")
    print(f"    - Confidence     : {seg_res.confidence_information.get('overall_confidence', 0.0):.2f}")
    for sc, pct in seg_res.class_pixel_percentages.items():
        if pct > 0.01:
            print(f"    - {sc.ljust(12)}: {pct:5.1f}%")

    # 3. Run Obstacle Detection & Event Capture
    print(f"[*] Evaluating Obstacle Detection & Image Alert Criteria...")
    detector = ObstacleEventDetector(config=AlertConfig(storage_dir=str(out_path / "alerts")))
    alert = detector.process_frame(unified_img, segmentation=seg_res)

    if alert:
        print(f"    [!] ALERT TRIGGERED: [{alert.event_id}]")
        print(f"        Category : {alert.detection_category}")
        print(f"        Coverage : {alert.obstacle_area_pct:.1f}%")
        print(f"        Confidence: {alert.confidence:.2f}")
    else:
        print(f"    [i] No critical obstacle event triggered (below detection threshold).")

    # 4. Save PNG artifacts
    orig_png = out_path / "original_frame.png"
    overlay_png = out_path / "semantic_overlay.png"
    color_map_png = out_path / "color_map.png"

    seg_res.save_overlay(overlay_png)
    seg_res.save_color_map(color_map_png)
    Image.fromarray(unified_img.image).save(orig_png)
    print(f"[*] Saved visual artifacts:")
    print(f"    - Original Frame    : {orig_png}")
    print(f"    - Semantic Overlay  : {overlay_png}")
    print(f"    - Class Color Map   : {color_map_png}")

    # 5. Build HTML Interactive Report
    orig_b64 = array_to_base64_uri(unified_img.image)
    overlay_b64 = array_to_base64_uri(seg_res.overlay_image)
    colormap_b64 = array_to_base64_uri(seg_res.color_map)
    alert_b64 = array_to_base64_uri(alert.annotated_image) if alert else None

    # Generate progress bar rows
    bars_html = ""
    for sc in SemanticClass:
        pct = seg_res.class_pixel_percentages.get(sc.value, 0.0)
        rgb = SEMANTIC_COLOR_PALETTE[sc]
        hex_c = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        bars_html += f"""
        <div style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span><strong style="color: {hex_c};">■</strong> {sc.value}</span>
            <span style="font-family: monospace;">{pct:.1f}%</span>
          </div>
          <div style="width: 100%; height: 6px; background: #1a2234; border-radius: 3px; overflow: hidden;">
            <div style="width: {min(pct, 100):.1f}%; height: 100%; background: {hex_c};"></div>
          </div>
        </div>
        """

    alert_banner_html = ""
    if alert:
        alert_banner_html = f"""
        <div style="background: rgba(231,76,60,0.15); border: 1px solid #E74C3C; border-radius: 8px; padding: 14px; margin-bottom: 20px; color: #FF6B6B;">
          <h3 style="margin: 0 0 6px 0; font-size: 15px;">🚨 AUTOMATIC OBSTACLE ALERT: {alert.event_id}</h3>
          <p style="margin: 0; font-size: 13px; color: #E0E0E0;">{alert.explanation}</p>
          <div style="display: flex; gap: 20px; font-size: 12px; font-family: monospace; margin-top: 8px; color: #88A0C0;">
            <span>CONFIDENCE: {alert.confidence*100:.1f}%</span>
            <span>SURFACE COVERAGE: {alert.obstacle_area_pct:.1f}%</span>
            <span>STATUS: {alert.verification_status}</span>
          </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ODYSSEY VisionScore 2.0 Report</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #0A0E17;
      color: #E2E8F0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid #1E293B;
      margin-bottom: 24px;
    }}
    .title {{ font-size: 20px; font-weight: 700; color: #38BDF8; letter-spacing: 0.05em; }}
    .badge {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid #38BDF8;
      color: #38BDF8;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #1E293B;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card-title {{
      font-size: 14px;
      font-weight: 600;
      color: #94A3B8;
      margin-top: 0;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .img-container {{
      background: #000;
      border-radius: 6px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
    }}
    .img-container img {{
      width: 100%;
      height: auto;
      max-height: 440px;
      object-fit: contain;
      display: block;
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .tab-btn {{
      background: #1E293B;
      border: none;
      color: #94A3B8;
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }}
    .tab-btn.active {{
      background: #38BDF8;
      color: #000;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">🔴 MARS-09 ODYSSEY: VISIONSCORE 2.0 AI REPORT</div>
      <div style="font-size: 12px; color: #64748B; margin-top: 4px;">Semantic Terrain Segmentation & Obstacle Alert Analysis</div>
    </div>
    <div style="display: flex; gap: 8px; align-items: center;">
      <span class="badge">ENV: {env_profile.value}</span>
      <span class="badge" style="border-color: #10B981; color: #10B981;">DOMINANT: {seg_res.dominant_class}</span>
    </div>
  </div>

  {alert_banner_html}

  <div class="grid">
    <div>
      <div class="card">
        <div class="tabs">
          <button class="tab-btn active" onclick="showImg('overlay')">Semantic Overlay</button>
          <button class="tab-btn" onclick="showImg('original')">Original Camera Frame</button>
          <button class="tab-btn" onclick="showImg('colormap')">Color Map</button>
          {"<button class='tab-btn' onclick='showImg(\"alert\")'>Alert Annotation</button>" if alert else ""}
        </div>
        <div class="img-container">
          <img id="mainView" src="{overlay_b64}" alt="VisionScore Output">
        </div>
      </div>
    </div>

    <div>
      <div class="card">
        <h3 class="card-title">Geological Classification</h3>
        {bars_html}
      </div>

      <div class="card">
        <h3 class="card-title">Model Status & Telemetry</h3>
        <div style="font-size: 12px; font-family: monospace; color: #94A3B8; line-height: 1.6;">
          <div>MODEL: {seg_res.model_status.get('model_name', 'PSM-TCS 2.0')}</div>
          <div>REAL AI WEIGHTS: {seg_res.model_status.get('is_real_ai_model')} (Heuristic Baseline)</div>
          <div>CONFIDENCE: {seg_res.confidence_information.get('overall_confidence', 0.0):.2f}</div>
          <div>KNOWN FRACTION: {seg_res.confidence_information.get('known_surface_fraction', 0.0)*100:.1f}%</div>
          <div>REGIONS DETECTED: {len(seg_res.region_segments)}</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    function showImg(type) {{
      const img = document.getElementById('mainView');
      const btns = document.querySelectorAll('.tab-btn');
      btns.forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');

      if (type === 'overlay') img.src = '{overlay_b64}';
      if (type === 'original') img.src = '{orig_b64}';
      if (type === 'colormap') img.src = '{colormap_b64}';
      if (type === 'alert') img.src = '{alert_b64 if alert else overlay_b64}';
    }}
  </script>
</body>
</html>"""

    html_file = out_path / "visionscore_report.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[+] Interactive Report Generated Successfully!")
    print(f"    Direct Browser Link: file:///{html_file.resolve().as_posix()}")
    print(f"================================================================================\n")
    return html_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run VisionScore 2.0 AI Model")
    parser.add_argument("--env", type=str, default="MARS", choices=["MARS", "EARTH", "SIMULATION"])
    parser.add_argument("--image", type=str, default=None, help="Optional image path to analyze")
    parser.add_argument("--no-obstacle", action="store_true", help="Do not inject simulated obstacle")
    args = parser.parse_args()

    run_pipeline(
        environment=args.env,
        image_path=args.image,
        inject_obstacle=not args.no_obstacle,
    )
