"""
Test Suite for ODYSSEY Task 2B: Mars Dataset Pipeline (AI4Mars).

Verifies:
1. AI4Mars label mapping: 0->SOIL, 1->BEDROCK, 2->SAND, 3->BOULDER, 255->IGNORE_INDEX.
2. Ignore index preservation during mask remapping.
3. Image and mask discovery across standard folder structures.
4. Paired loading and spatial dimension validation.
5. Handling of missing files and invalid/corrupted files.
6. Target resolution resizing (bilinear for images, nearest neighbor for masks).
7. Sequence-aware, leak-free train/val/test reproducible partitioning and manifest persistence.
"""

import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from visionscore.config import SemanticClass
from visionscore.dataset import (
    AI4MARS_DEFAULT_LABEL_MAP,
    AI4MARS_IGNORE_INDEX,
    AI4MARS_SEMANTIC_NAMES,
    AI4MarsDataset,
    AI4MarsSemanticLabel,
    CorruptedDataError,
    DatasetSplitManifest,
    MissingDataError,
    compute_loss_mask,
    extract_sol_and_sequence,
    remap_ai4mars_mask,
)
from core.terrain import build_terrain_intelligence


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def synthetic_ai4mars_dir(tmp_path: Path) -> Path:
    """
    Creates a small, realistic synthetic AI4Mars directory with paired images and masks.
    Simulates Curiosity/Perseverance rover file naming schemes across multiple Sols.
    """
    img_dir = tmp_path / "images"
    mask_dir = tmp_path / "labels"
    img_dir.mkdir(parents=True)
    mask_dir.mkdir(parents=True)

    # Create 6 samples across 2 sequences/sols
    samples_info = [
        ("NLB_0421_001_EDR", 421, (100, 100)),
        ("NLB_0421_002_EDR", 421, (100, 100)),
        ("NLB_0421_003_EDR", 421, (100, 100)),
        ("NRB_0550_001_EDR", 550, (100, 100)),
        ("NRB_0550_002_EDR", 550, (100, 100)),
        ("NRB_0550_003_EDR", 550, (100, 100)),
    ]

    for stem, sol, (h, w) in samples_info:
        # 1. Create synthetic RGB Mars image
        img_arr = np.zeros((h, w, 3), dtype=np.uint8)
        img_arr[:, :, 0] = 185  # Mars red
        img_arr[:, :, 1] = 95
        img_arr[:, :, 2] = 55
        Image.fromarray(img_arr).save(img_dir / f"{stem}.PNG")

        # 2. Create synthetic label mask with all 4 classes + 255 ignore index
        mask_arr = np.zeros((h, w), dtype=np.uint8)
        mask_arr[:25, :] = 0   # Soil
        mask_arr[25:50, :] = 1  # Bedrock
        mask_arr[50:75, :] = 2  # Sand
        mask_arr[75:90, :] = 3  # Boulder
        mask_arr[90:, :] = 255  # Null/Ignore (rover chassis or sky)
        Image.fromarray(mask_arr).save(mask_dir / f"{stem}.PNG")

    return tmp_path


# ============================================================================
# 1. Label Mapping & Ignore Index Tests
# ============================================================================

def test_ai4mars_default_label_map_values():
    """Verify exact AI4Mars class mappings to ODYSSEY SemanticClass."""
    assert AI4MARS_DEFAULT_LABEL_MAP[0] == SemanticClass.SOIL
    assert AI4MARS_DEFAULT_LABEL_MAP[1] == SemanticClass.BEDROCK
    assert AI4MARS_DEFAULT_LABEL_MAP[2] == SemanticClass.SAND
    assert AI4MARS_DEFAULT_LABEL_MAP[3] == SemanticClass.BOULDER
    assert AI4MARS_DEFAULT_LABEL_MAP[255] == SemanticClass.UNKNOWN
    assert AI4MARS_IGNORE_INDEX == 255


def test_remap_ai4mars_mask_and_ignore_index():
    """Verify mask remapping preserves valid classes and correctly isolates ignore_index."""
    raw = np.array([
        [0, 1],
        [2, 3],
        [255, 0],
    ], dtype=np.uint8)

    train_mask, semantic_names = remap_ai4mars_mask(raw, ignore_index=255)

    # Shape preservation
    assert train_mask.shape == (3, 2)
    assert semantic_names.shape == (3, 2)

    # Class mappings
    assert train_mask[0, 0] == 0
    assert semantic_names[0, 0] == "SOIL"

    assert train_mask[0, 1] == 1
    assert semantic_names[0, 1] == "BEDROCK"

    assert train_mask[1, 0] == 2
    assert semantic_names[1, 0] == "SAND"

    assert train_mask[1, 1] == 3
    assert semantic_names[1, 1] == "BOULDER"

    # Ignore index 255
    assert train_mask[2, 0] == 255
    assert semantic_names[2, 0] == "UNKNOWN"


def test_invalid_mask_dimensions_raises():
    """Verify 3D or 1D mask passed directly to remap_ai4mars_mask raises ValueError."""
    invalid_mask = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2-dimensional"):
        remap_ai4mars_mask(invalid_mask)


# ============================================================================
# 2. Sequence and Sol Metadata Extraction Tests
# ============================================================================

def test_extract_sol_and_sequence():
    """Verify Martian Sol and camera sequence ID extraction from filename stems."""
    sol, seq = extract_sol_and_sequence("NLB_0421_048382020EDR_F0000000AUT_04096M1")
    assert sol == 421
    assert seq == "NLB_0421"

    sol2, seq2 = extract_sol_and_sequence("sol_1050_mastcam_frame")
    assert sol2 == 1050
    assert "1050" in seq2


# ============================================================================
# 3. Dataset Discovery, Loading & Validation Tests
# ============================================================================

def test_dataset_discovery_and_length(synthetic_ai4mars_dir: Path):
    """Verify discovery of paired images and masks."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    assert len(dataset) == 6
    sample_ids = dataset.get_sample_ids()
    assert "NLB_0421_001_EDR" in sample_ids
    assert "NRB_0550_003_EDR" in sample_ids


def test_dataset_getitem_output_dimensions(synthetic_ai4mars_dir: Path):
    """Verify __getitem__ returns complete data dictionary with matching dimensions."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    sample = dataset[0]

    assert "sample_id" in sample
    assert "image" in sample
    assert "mask" in sample
    assert "training_mask" in sample
    assert "semantic_names" in sample

    assert sample["image"].shape == (100, 100, 3)
    assert sample["image"].dtype == np.uint8
    assert sample["mask"].shape == (100, 100)
    assert sample["training_mask"].shape == (100, 100)
    assert sample["sol"] == 421


def test_dataset_configurable_resizing(synthetic_ai4mars_dir: Path):
    """Verify configurable target_size resizes image and mask synchronously."""
    dataset = AI4MarsDataset(
        root_dir=synthetic_ai4mars_dir,
        target_size=(64, 48),  # (width, height)
    )
    sample = dataset[0]

    # NumPy shape is (height, width)
    assert sample["image"].shape == (48, 64, 3)
    assert sample["mask"].shape == (48, 64)
    assert sample["training_mask"].shape == (48, 64)

    # Verify discrete class labels are preserved without floating interpolation
    unique_labels = set(np.unique(sample["mask"]))
    assert unique_labels.issubset({0, 1, 2, 3, 255})


# ============================================================================
# 4. Error Handling: Missing & Corrupted Data Tests
# ============================================================================

def test_missing_root_directory_raises(tmp_path: Path):
    """Verify MissingDataError when root directory does not exist."""
    non_existent = tmp_path / "non_existent_mars_data"
    with pytest.raises(MissingDataError, match="does not exist"):
        AI4MarsDataset(root_dir=non_existent)


def test_empty_images_directory_raises(tmp_path: Path):
    """Verify MissingDataError when image directory is completely empty."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    with pytest.raises(MissingDataError, match="No valid image files discovered"):
        AI4MarsDataset(root_dir=empty_dir)


def test_missing_masks_when_required_raises(tmp_path: Path):
    """Verify MissingDataError when images exist but zero matching masks are found."""
    img_dir = tmp_path / "images"
    mask_dir = tmp_path / "labels"
    img_dir.mkdir()
    mask_dir.mkdir()

    # Create image only, no mask
    Image.new("RGB", (50, 50)).save(img_dir / "unmatched_frame.png")

    with pytest.raises(MissingDataError, match="zero matching masks"):
        AI4MarsDataset(root_dir=tmp_path, require_masks=True)


def test_corrupted_image_file_raises(tmp_path: Path):
    """Verify CorruptedDataError when image contains unreadable garbage bytes."""
    img_dir = tmp_path / "images"
    mask_dir = tmp_path / "labels"
    img_dir.mkdir()
    mask_dir.mkdir()

    bad_img = img_dir / "corrupted_img.png"
    bad_img.write_bytes(b"NOT_A_VALID_PNG_FILE_HEADER")

    good_mask = mask_dir / "corrupted_img.png"
    Image.new("L", (50, 50)).save(good_mask)

    dataset = AI4MarsDataset(root_dir=tmp_path)
    with pytest.raises(CorruptedDataError, match="Failed to read image"):
        _ = dataset[0]


def test_image_mask_dimension_mismatch_raises(tmp_path: Path):
    """Verify CorruptedDataError when image and mask have conflicting spatial dimensions."""
    img_dir = tmp_path / "images"
    mask_dir = tmp_path / "labels"
    img_dir.mkdir()
    mask_dir.mkdir()

    Image.new("RGB", (60, 60)).save(img_dir / "mismatch.png")
    Image.new("L", (80, 80)).save(mask_dir / "mismatch.png")

    dataset = AI4MarsDataset(root_dir=tmp_path)
    with pytest.raises(CorruptedDataError, match="Dimension mismatch"):
        _ = dataset[0]


# ============================================================================
# 5. Reproducible Dataset Splitting & Data Leakage Prevention Tests
# ============================================================================

def test_dataset_split_proportions_and_disjointness(synthetic_ai4mars_dir: Path):
    """Verify train, val, and test partitions are disjoint with zero overlap."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    manifest = dataset.split(train_ratio=0.50, val_ratio=0.25, test_ratio=0.25, seed=42, group_by_sequence=False)

    train_set = set(manifest.train_ids)
    val_set = set(manifest.val_ids)
    test_set = set(manifest.test_ids)

    # Zero leakage
    assert train_set.isdisjoint(val_set)
    assert train_set.isdisjoint(test_set)
    assert val_set.isdisjoint(test_set)

    # Total sample count matches
    assert len(train_set) + len(val_set) + len(test_set) == len(dataset)


def test_dataset_sequence_grouping_prevents_leakage(synthetic_ai4mars_dir: Path):
    """Verify that images from the same Sol / sequence key are kept in the same split."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    manifest = dataset.split(train_ratio=0.50, val_ratio=0.25, test_ratio=0.25, seed=123, group_by_sequence=True)

    # Check that Sol 421 images are all in the same partition
    sol_421_ids = [s.sample_id for s in dataset.samples if s.sol == 421]
    in_train = [sid in manifest.train_ids for sid in sol_421_ids]
    in_val = [sid in manifest.val_ids for sid in sol_421_ids]
    in_test = [sid in manifest.test_ids for sid in sol_421_ids]

    # Either ALL in train, ALL in val, or ALL in test
    assert all(in_train) or all(in_val) or all(in_test), "Sol 421 was split across multiple partitions!"


def test_manifest_save_and_load(synthetic_ai4mars_dir: Path, tmp_path: Path):
    """Verify DatasetSplitManifest can be serialized to JSON and cleanly reloaded."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    manifest_path = tmp_path / "manifests" / "split_manifest.json"

    manifest = dataset.split(
        train_ratio=0.60,
        val_ratio=0.20,
        test_ratio=0.20,
        seed=999,
        output_manifest_path=manifest_path,
    )
    assert manifest_path.exists()

    loaded = DatasetSplitManifest.load(manifest_path)
    assert loaded.seed == 999
    assert loaded.train_ids == manifest.train_ids
    assert loaded.val_ids == manifest.val_ids
    assert loaded.test_ids == manifest.test_ids
    assert loaded.total_samples == manifest.total_samples


# ============================================================================
# 6. Task 2C: Semantic & Traversability Separation & Loss Masking Tests
# ============================================================================

def test_strictly_semantic_labels_and_no_traversability_leakage():
    """
    Verify AI4Mars ground truth labels are strictly semantic:
    SOIL, BEDROCK, SAND, BOULDER, IGNORE.
    No automatic assignment of SAFE, CAUTION, or HAZARD by the dataset module.
    """
    assert AI4MarsSemanticLabel.SOIL.value == "SOIL"
    assert AI4MarsSemanticLabel.BEDROCK.value == "BEDROCK"
    assert AI4MarsSemanticLabel.SAND.value == "SAND"
    assert AI4MarsSemanticLabel.BOULDER.value == "BOULDER"
    assert AI4MarsSemanticLabel.IGNORE.value == "IGNORE"

    # Verify AI4MARS_SEMANTIC_NAMES
    assert AI4MARS_SEMANTIC_NAMES[0] == "SOIL"
    assert AI4MARS_SEMANTIC_NAMES[1] == "BEDROCK"
    assert AI4MARS_SEMANTIC_NAMES[2] == "SAND"
    assert AI4MARS_SEMANTIC_NAMES[3] == "BOULDER"
    assert AI4MARS_SEMANTIC_NAMES[255] == "IGNORE"


def test_loss_mask_excludes_ignore_index():
    """
    Verify compute_loss_mask strictly excludes 255 (rover body / sky) with weight 0.0,
    ensuring unannotated pixels never contribute to training gradient calculations.
    """
    sample_mask = np.array([
        [0, 1, 2],
        [3, 255, 0],
        [255, 255, 1],
    ], dtype=np.int32)

    loss_mask = compute_loss_mask(sample_mask, ignore_index=255)

    assert loss_mask.shape == (3, 3)
    assert loss_mask.dtype == bool

    # Valid geological pixels are True
    assert loss_mask[0, 0] is True or loss_mask[0, 0] == True
    assert loss_mask[0, 1] == True
    assert loss_mask[0, 2] == True
    assert loss_mask[1, 0] == True
    assert loss_mask[1, 2] == True
    assert loss_mask[2, 2] == True

    # Ignored pixels are strictly False
    assert loss_mask[1, 1] == False
    assert loss_mask[2, 0] == False
    assert loss_mask[2, 1] == False

    # Loss weights
    loss_weights = loss_mask.astype(np.float32)
    assert np.all(loss_weights[sample_mask == 255] == 0.0)
    assert np.all(loss_weights[sample_mask != 255] == 1.0)


def test_dataset_sample_contains_loss_mask(synthetic_ai4mars_dir: Path):
    """Verify AI4MarsDataset sample payload provides loss_mask and loss_weight."""
    dataset = AI4MarsDataset(root_dir=synthetic_ai4mars_dir)
    sample = dataset[0]

    assert "loss_mask" in sample
    assert "loss_weight" in sample
    assert sample["loss_mask"] is not None
    assert sample["loss_mask"].dtype == bool
    assert sample["loss_weight"].dtype == np.float32

    # Verification: wherever raw mask was 255, loss_mask MUST be False
    raw_mask = sample["mask"]
    ignore_coords = (raw_mask == 255)
    assert np.all(sample["loss_mask"][ignore_coords] == False)
    assert np.all(sample["loss_weight"][ignore_coords] == 0.0)


def test_navigation_contract_preservation():
    """
    Verify existing Member 3 navigation integration contract is preserved:
    - cost_map is 2D NumPy float64.
    - SAFE = 1.0.
    - CAUTION = 5.0 - 20.0.
    - HAZARD = np.inf.
    - risk_map is separate and normalized in [0.0, 1.0].
    """
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]
    risk_map = terrain["risk_map"]

    assert isinstance(cost_map, np.ndarray)
    assert cost_map.dtype == np.float64
    assert cost_map.shape == (100, 100)

    assert isinstance(risk_map, np.ndarray)
    assert risk_map.dtype == np.float64
    assert risk_map.shape == (100, 100)

    # Cost conventions
    assert np.any(cost_map == 1.0)
    assert np.any(np.isinf(cost_map))
    assert np.all(cost_map > 0.0)

    # Risk map normalization
    assert np.all(risk_map >= 0.0)
    assert np.all(risk_map <= 1.0)


def test_ai4mars_real_curated_data_loading():
    """Verify AI4MarsDataset directly loads the 20 real downloaded Curiosity scenes."""
    real_data_dir = Path("data/ai4mars")
    if not real_data_dir.exists() or not (real_data_dir / "images").exists():
        pytest.skip("Real AI4Mars sample data not downloaded yet.")

    dataset = AI4MarsDataset(root_dir=real_data_dir, target_size=(128, 128), require_masks=True)
    assert len(dataset) >= 20, f"Expected at least 20 real scenes, got {len(dataset)}"

    sample = dataset[0]
    assert sample["image"].shape == (128, 128, 3)
    assert sample["mask"].shape == (128, 128)
    assert sample["loss_mask"].shape == (128, 128)
    assert sample["loss_mask"].dtype == bool

    # Split verification
    manifest = dataset.split(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
    assert len(manifest.train_ids) + len(manifest.val_ids) + len(manifest.test_ids) == len(dataset)
    assert set(manifest.train_ids).isdisjoint(set(manifest.test_ids))



