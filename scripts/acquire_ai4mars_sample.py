"""
AI4Mars Real Sample Acquisition Script.

Downloads a curated set of genuine NASA/JPL Curiosity Mars rover Navcam images
and ground-truth semantic segmentation masks directly into data/ai4mars/.
"""

import concurrent.futures
import io
import json
from pathlib import Path
import sys
import urllib.request

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "ai4mars"
IMG_DIR = DATA_DIR / "images"
LBL_DIR = DATA_DIR / "labels"

HF_API_URL = "https://huggingface.co/api/datasets/harpreetsahota/ai4mars-msl"
HF_BASE_URL = "https://huggingface.co/datasets/harpreetsahota/ai4mars-msl/resolve/main"
GITHUB_MASK_URL = "https://raw.githubusercontent.com/surasakphetmanee/mars-rover-edgecheck/main/sam_labels"

SCENES = [
    "NLB_439226140EDR_F0240000NCAM00350M1",
    "NLB_442593301EDR_F0250312NCAM00353M1",
    "NLB_443663262EDR_F0251238NCAM00289M1",
    "NLB_443668744EDR_F0251238NCAM00292M1",
    "NLB_457152554EDR_F0380000NCAM00275M1",
    "NLB_459291152EDR_F0391552NCAM00252M1",
    "NLB_463107188EDR_F0410748NCAM00274M1",
    "NLB_505898434EDR_F0521162NCAM12753M1",
    "NLB_512555120EDR_F0532644NCAM00264M1",
    "NLB_520359112EDR_F0550940NCAM00654M1",
    "NLB_525149367EDR_F0570774NCAM00654M1",
    "NLB_525149717EDR_F0570774NCAM07753M1",
    "NLB_543357370EDR_F0613076NCAM00287M1",
    "NLB_552677513EDR_F0642088NCAM00255M1",
    "NLB_552682173EDR_F0642088NCAM07753M1",
    "NLB_556756244EDR_F0651642NCAM00285M1",
    "NLB_565373417EDR_F0670650NCAM12753M1",
    "NLB_574078440EDR_F0681626NCAM00354M1",
    "NLB_613582793EDR_F0760556NCAM00385M1",
    "NLB_613583763EDR_F0760568NCAM00354M1",
]


def acquire_ai4mars_subset():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    LBL_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Fetching file index from HuggingFace...")
    req = urllib.request.Request(HF_API_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        meta = json.loads(resp.read().decode())
    
    siblings = [s.get("rfilename") for s in meta.get("siblings", [])]
    img_map = {}
    for s in siblings:
        if s.endswith(".JPG"):
            stem = Path(s).stem
            img_map[stem] = s

    print(f"Index retrieved. Mapping {len(SCENES)} target scenes...")

    def fetch_scene(scene_id):
        img_target = IMG_DIR / f"{scene_id}.JPG"
        lbl_target = LBL_DIR / f"{scene_id}.png"

        if img_target.exists() and lbl_target.exists():
            return scene_id, "already_cached"

        # Download Mask from GitHub
        mask_url = f"{GITHUB_MASK_URL}/{scene_id}.png"
        req_m = urllib.request.Request(mask_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_m, timeout=20) as resp_m:
            mask_data = resp_m.read()

        # Download Image from HuggingFace
        rel_path = img_map.get(scene_id)
        if not rel_path:
            raise RuntimeError(f"Scene {scene_id} not found in HuggingFace index.")
        
        img_url = f"{HF_BASE_URL}/{rel_path}"
        req_i = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_i, timeout=20) as resp_i:
            img_data = resp_i.read()

        # Validate with Pillow
        img = Image.open(io.BytesIO(img_data))
        mask = Image.open(io.BytesIO(mask_data))

        if img.size != mask.size:
            raise ValueError(f"Size mismatch: img={img.size}, mask={mask.size}")

        with open(img_target, "wb") as f:
            f.write(img_data)
        with open(lbl_target, "wb") as f:
            f.write(mask_data)

        classes = np.unique(np.array(mask)).tolist()
        return scene_id, f"downloaded ({img.size[0]}x{img.size[1]}, classes={classes})"

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_scene, s): s for s in SCENES}
        for future in concurrent.futures.as_completed(futures):
            scene_id = futures[future]
            try:
                sid, status = future.result()
                print(f"  [OK] {sid}: {status}")
            except Exception as e:
                print(f"  [ERR] {scene_id}: {e}", file=sys.stderr)

    # Summary verification
    imgs = list(IMG_DIR.glob("*.JPG"))
    lbls = list(LBL_DIR.glob("*.png"))
    print(f"\nCompleted! Verified {len(imgs)} images and {len(lbls)} masks in {DATA_DIR}.")


if __name__ == "__main__":
    acquire_ai4mars_subset()

