"""
AI4Mars Dataset Ingestion, Preprocessing & Manifest Pipeline.

Provides modular, lightweight data loading, mask parsing, and leak-free dataset splitting
for Martian surface rover imagery conforming to NASA JPL AI4Mars specifications.

AI4Mars Benchmark Categories:
- 0: Soil (cohesive Martian regolith substrate)
- 1: Bedrock (firm exposed rock pavement)
- 2: Sand (aeolian dunes and ripple fields)
- 3: Big Rock / Boulder (prominent rock hazards)
- 255: Null / Unlabeled / Rover chassis / Sky (IGNORE_INDEX)

Notice:
    Does not require PyTorch or heavyweight GPU acceleration libraries.
    Designed for high throughput using standard NumPy and Pillow operations.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
from enum import Enum
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
from PIL import Image

from visionscore.config import SemanticClass

logger = logging.getLogger(__name__)

# Standard AI4Mars Ignore Label
AI4MARS_IGNORE_INDEX: int = 255


class AI4MarsSemanticLabel(str, Enum):
    """
    Pure geological semantic categories defined by NASA JPL AI4Mars benchmark.
    Kept strictly distinct from physical traversability classifications (SAFE, CAUTION, HAZARD).
    Physical safety cannot be inferred from optical semantics alone.
    """
    SOIL = "SOIL"
    BEDROCK = "BEDROCK"
    SAND = "SAND"
    BOULDER = "BOULDER"
    IGNORE = "IGNORE"


# Strict semantic name mapping for AI4Mars raw benchmark values
AI4MARS_SEMANTIC_NAMES: Dict[int, str] = {
    0: AI4MarsSemanticLabel.SOIL.value,
    1: AI4MarsSemanticLabel.BEDROCK.value,
    2: AI4MarsSemanticLabel.SAND.value,
    3: AI4MarsSemanticLabel.BOULDER.value,
    AI4MARS_IGNORE_INDEX: AI4MarsSemanticLabel.IGNORE.value,
}

# Standard AI4Mars Raw Class ID -> ODYSSEY SemanticClass Mapping
AI4MARS_DEFAULT_LABEL_MAP: Dict[int, SemanticClass] = {
    0: SemanticClass.SOIL,
    1: SemanticClass.BEDROCK,
    2: SemanticClass.SAND,
    3: SemanticClass.BOULDER,
    AI4MARS_IGNORE_INDEX: SemanticClass.UNKNOWN,
}

# Supported image and mask file extensions
SUPPORTED_IMAGE_EXTENSIONS: Tuple[str, ...] = (
    ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".PNG", ".JPG", ".JPEG"
)
SUPPORTED_MASK_EXTENSIONS: Tuple[str, ...] = (
    ".png", ".npy", ".PNG"
)


class DatasetError(Exception):
    """Base exception for AI4Mars dataset errors."""
    pass


class MissingDataError(DatasetError):
    """Raised when the specified directory is missing or contains no valid paired files."""
    pass


class CorruptedDataError(DatasetError):
    """Raised when an image or mask is unreadable, corrupted, or has dimension mismatches."""
    pass


@dataclass
class AI4MarsSample:
    """Represents a discovered image and corresponding semantic segmentation mask."""
    sample_id: str
    image_path: Path
    mask_path: Optional[Path] = None
    sol: Optional[int] = None
    sequence_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "image_path": str(self.image_path),
            "mask_path": str(self.mask_path) if self.mask_path else None,
            "sol": self.sol,
            "sequence_id": self.sequence_id,
            "metadata": self.metadata,
        }


@dataclass
class DatasetSplitManifest:
    """
    Serializable record documenting train, validation, and test sample partitioning.
    Guarantees zero data leakage and exact reproducibility.
    """
    train_ids: List[str]
    val_ids: List[str]
    test_ids: List[str]
    seed: int
    created_at_utc: str
    total_samples: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_ids": self.train_ids,
            "val_ids": self.val_ids,
            "test_ids": self.test_ids,
            "seed": self.seed,
            "created_at_utc": self.created_at_utc,
            "total_samples": self.total_samples,
            "split_counts": {
                "train": len(self.train_ids),
                "val": len(self.val_ids),
                "test": len(self.test_ids),
            },
            "metadata": self.metadata,
        }

    def save(self, filepath: Union[str, Path]) -> Path:
        """Persists the split manifest to disk as a structured JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "DatasetSplitManifest":
        """Loads a split manifest from an existing JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            train_ids=data["train_ids"],
            val_ids=data["val_ids"],
            test_ids=data["test_ids"],
            seed=data["seed"],
            created_at_utc=data["created_at_utc"],
            total_samples=data["total_samples"],
            metadata=data.get("metadata", {}),
        )


def extract_sol_and_sequence(filename: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Extracts Martian Sol (day) and camera sequence IDs from standard rover naming schemes.
    e.g. 'NLB_0421_048382020EDR_F0000000AUT_04096M1.PNG' -> Sol 421, Sequence 'NLB_0421'
    """
    sol = None
    sequence = None

    # Matches patterns like sol123, _0421_, sol_0042
    sol_match = re.search(r"(?:sol[_-]?|[_/])(\d{3,5})", filename, re.IGNORECASE)
    if sol_match:
        try:
            sol = int(sol_match.group(1))
        except ValueError:
            pass

    # Sequence key derived from prefix (first two tokens) or sol
    tokens = Path(filename).stem.split("_")
    if len(tokens) >= 2:
        sequence = f"{tokens[0]}_{tokens[1]}"
    elif sol is not None:
        sequence = f"SOL_{sol}"
    else:
        sequence = Path(filename).stem

    return sol, sequence


def remap_ai4mars_mask(
    raw_mask: np.ndarray,
    label_map: Optional[Dict[int, SemanticClass]] = None,
    ignore_index: int = AI4MARS_IGNORE_INDEX,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remaps an AI4Mars raw integer label mask to:
    1. Training target mask: integer array where valid classes are preserved and
       unlabeled/rover pixels retain `ignore_index`.
    2. Semantic name array: 2D object array containing SemanticClass string names.

    Args:
        raw_mask: 2D uint8 NumPy array of ground-truth labels.
        label_map: Optional mapping dictionary (defaults to AI4MARS_DEFAULT_LABEL_MAP).
        ignore_index: Value reserved for ignored/unlabeled training pixels (default: 255).

    Returns:
        Tuple of (remapped_training_mask, semantic_name_mask).
    """
    if raw_mask.ndim != 2:
        raise ValueError(f"Mask must be 2-dimensional (H, W), received ndim={raw_mask.ndim}")

    active_map = label_map or AI4MARS_DEFAULT_LABEL_MAP
    h, w = raw_mask.shape

    # Training mask keeps raw IDs or remapped target integers with ignore_index preserved
    remapped_train_mask = np.full((h, w), ignore_index, dtype=np.int32)
    semantic_names = np.full((h, w), SemanticClass.UNKNOWN.value, dtype=object)

    for raw_id, sem_cls in active_map.items():
        match_pixels = (raw_mask == raw_id)
        if raw_id != ignore_index:
            remapped_train_mask[match_pixels] = raw_id
            semantic_names[match_pixels] = sem_cls.value
        else:
            remapped_train_mask[match_pixels] = ignore_index
            semantic_names[match_pixels] = SemanticClass.UNKNOWN.value

    return remapped_train_mask, semantic_names


def compute_loss_mask(
    mask: np.ndarray,
    ignore_index: int = AI4MARS_IGNORE_INDEX,
) -> np.ndarray:
    """
    Computes a boolean mask indicating active pixels to include in neural training loss.
    Guarantees that ignored pixels (255 / rover body / sky) are excluded with loss weight 0.0.

    Args:
        mask: 2D integer NumPy array of ground-truth or training labels.
        ignore_index: Value reserved for ignored pixels (default: 255).

    Returns:
        2D boolean NumPy array where True denotes valid loss pixels and False denotes ignored pixels.
    """
    if mask.ndim != 2:
        raise ValueError(f"Mask must be 2-dimensional (H, W), received ndim={mask.ndim}")
    return (mask != ignore_index)


class AI4MarsDataset:
    """
    Modular, lightweight Mars Rover image and semantic mask dataset loader.

    Supports:
    - Automatic pairing of images and label masks across directory layouts:
      1. Co-located paired directories (`images/` and `labels/` or `masks/`).
      2. Flat directory containing matching filename stems.
    - Robust image validation (corrupted bytes, non-matching dimensions).
    - Configurable target resolution resizing (bilinear for RGB, nearest for masks).
    - Leak-free, sequence-aware train/val/test partitioning.
    """

    def __init__(
        self,
        root_dir: Union[str, Path],
        images_dir: Optional[str] = None,
        masks_dir: Optional[str] = None,
        target_size: Optional[Tuple[int, int]] = None,  # (width, height)
        label_map: Optional[Dict[int, SemanticClass]] = None,
        ignore_index: int = AI4MARS_IGNORE_INDEX,
        require_masks: bool = True,
    ):
        self.root_dir = Path(root_dir)
        self.images_dir = self._resolve_dir(images_dir, candidates=["images", "img", "raw", ""])
        self.masks_dir = self._resolve_dir(masks_dir, candidates=["labels", "masks", "annotations", ""])
        self.target_size = target_size
        self.label_map = label_map or AI4MARS_DEFAULT_LABEL_MAP
        self.ignore_index = ignore_index
        self.require_masks = require_masks

        # Discover paired samples
        self.samples: List[AI4MarsSample] = self._discover_samples()

    def _resolve_dir(self, explicit: Optional[str], candidates: List[str]) -> Path:
        """Finds the appropriate subdirectory within root_dir."""
        if explicit:
            candidate = self.root_dir / explicit
            if candidate.exists() and candidate.is_dir():
                return candidate
            # Or root_dir itself if explicit is empty
            if explicit == "":
                return self.root_dir

        for c in candidates:
            cand_path = self.root_dir / c if c else self.root_dir
            if cand_path.exists() and cand_path.is_dir():
                return cand_path

        return self.root_dir

    def _discover_samples(self) -> List[AI4MarsSample]:
        """Discovers and pairs image files with their ground-truth label masks."""
        if not self.root_dir.exists():
            raise MissingDataError(f"Dataset root directory does not exist: {self.root_dir}")

        image_files: List[Path] = []
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(self.images_dir.glob(f"*{ext}"))

        if not image_files:
            # Also check recursive search if images_dir has nested subfolders
            for ext in SUPPORTED_IMAGE_EXTENSIONS:
                image_files.extend(self.images_dir.rglob(f"*{ext}"))

        # Deduplicate paths
        image_files = sorted(list(set(image_files)))

        if not image_files:
            raise MissingDataError(f"No valid image files discovered in: {self.images_dir}")

        samples: List[AI4MarsSample] = []
        for img_path in image_files:
            stem = img_path.stem
            # Ignore label files if discovered in flat directory
            if stem.endswith("_mask") or stem.endswith("_label"):
                continue

            mask_path = self._find_matching_mask(stem)

            if self.require_masks and mask_path is None:
                # If masks are required, skip or warn
                continue

            sol, seq = extract_sol_and_sequence(stem)
            samples.append(
                AI4MarsSample(
                    sample_id=stem,
                    image_path=img_path,
                    mask_path=mask_path,
                    sol=sol,
                    sequence_id=seq,
                )
            )

        if self.require_masks and not samples:
            raise MissingDataError(
                f"Discovered {len(image_files)} images, but zero matching masks were found in {self.masks_dir}."
            )

        return samples

    def _find_matching_mask(self, stem: str) -> Optional[Path]:
        """Looks for a matching mask file with multiple standard naming conventions."""
        candidates = [
            stem,
            f"{stem}_mask",
            f"{stem}_label",
            f"{stem}.mask",
        ]
        for name in candidates:
            for ext in SUPPORTED_MASK_EXTENSIONS:
                p = self.masks_dir / f"{name}{ext}"
                if p.exists() and p.is_file():
                    return p
        return None

    def __len__(self) -> int:
        return len(self.samples)

    def get_sample_ids(self) -> List[str]:
        """Returns the list of sample IDs in the dataset."""
        return [s.sample_id for s in self.samples]

    def load_image(self, path: Path) -> np.ndarray:
        """Loads and normalizes an image to uint8 RGB NumPy array."""
        if not path.exists():
            raise MissingDataError(f"Image file does not exist: {path}")
        try:
            with Image.open(path) as pil_img:
                rgb = pil_img.convert("RGB")
                if self.target_size is not None:
                    rgb = rgb.resize(self.target_size, resample=Image.Resampling.BILINEAR)
                return np.array(rgb, dtype=np.uint8)
        except Exception as e:
            raise CorruptedDataError(f"Failed to read image at {path}: {str(e)}") from e

    def load_mask(self, path: Path) -> np.ndarray:
        """Loads and normalizes a mask to 2D integer NumPy array."""
        if not path.exists():
            raise MissingDataError(f"Mask file does not exist: {path}")
        try:
            if path.suffix.lower() == ".npy":
                mask_arr = np.load(path)
            else:
                with Image.open(path) as pil_mask:
                    if self.target_size is not None:
                        # Nearest neighbor resampling preserves discrete class labels
                        pil_mask = pil_mask.resize(self.target_size, resample=Image.Resampling.NEAREST)
                    mask_arr = np.array(pil_mask)

            if mask_arr.ndim == 3:
                # If RGB mask, take first channel
                mask_arr = mask_arr[:, :, 0]

            return mask_arr.astype(np.uint8)
        except Exception as e:
            raise CorruptedDataError(f"Failed to read mask at {path}: {str(e)}") from e

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        Loads and returns sample at index.
        Returns:
            Dict containing:
                - 'sample_id': Identifier
                - 'image': (H, W, 3) uint8 RGB array
                - 'mask': (H, W) raw integer array
                - 'training_mask': (H, W) array with ignore_index preserved
                - 'semantic_names': (H, W) array with SemanticClass strings
                - 'sol': Optional[int]
                - 'sequence_id': Optional[str]
        """
        if idx < 0 or idx >= len(self.samples):
            raise IndexError(f"Index {idx} out of bounds for dataset of length {len(self.samples)}")

        sample = self.samples[idx]
        image_arr = self.load_image(sample.image_path)

        mask_arr = None
        training_mask = None
        semantic_names = None

        loss_mask = None
        loss_weight = None

        if sample.mask_path is not None:
            mask_arr = self.load_mask(sample.mask_path)
            # Verify spatial dimensions match
            if image_arr.shape[:2] != mask_arr.shape[:2]:
                raise CorruptedDataError(
                    f"Dimension mismatch for sample {sample.sample_id}: "
                    f"Image {image_arr.shape[:2]} vs Mask {mask_arr.shape[:2]}"
                )

            training_mask, semantic_names = remap_ai4mars_mask(
                raw_mask=mask_arr,
                label_map=self.label_map,
                ignore_index=self.ignore_index,
            )
            loss_mask = compute_loss_mask(training_mask, self.ignore_index)
            loss_weight = loss_mask.astype(np.float32)

        return {
            "sample_id": sample.sample_id,
            "image": image_arr,
            "mask": mask_arr,
            "training_mask": training_mask,
            "semantic_names": semantic_names,
            "loss_mask": loss_mask,
            "loss_weight": loss_weight,
            "sol": sample.sol,
            "sequence_id": sample.sequence_id,
            "image_path": str(sample.image_path),
            "mask_path": str(sample.mask_path) if sample.mask_path else None,
        }

    def split(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
        group_by_sequence: bool = True,
        output_manifest_path: Optional[Union[str, Path]] = None,
    ) -> DatasetSplitManifest:
        """
        Splits dataset into disjoint train, validation, and test subsets.

        Guarantees:
        - Exact reproducibility via fixed random seed.
        - Zero overlapping sample IDs across partitions.
        - Sequence-aware grouping: Images from the same Sol or drive burst remain together
          to eliminate spatial/temporal data leakage between train and test sets.

        Args:
            train_ratio: Proportion allocated to training set.
            val_ratio: Proportion allocated to validation set.
            test_ratio: Proportion allocated to test set.
            seed: Pseudo-random generator seed.
            group_by_sequence: When True, groups samples by sequence_id to prevent leakage.
            output_manifest_path: Optional path to save JSON manifest file.

        Returns:
            DatasetSplitManifest detailing partitioned sample IDs.
        """
        if not math.isclose(train_ratio + val_ratio + test_ratio, 1.0, rel_tol=1e-3):
            raise ValueError(
                f"Split ratios must sum to 1.0 (received {train_ratio} + {val_ratio} + {test_ratio} = "
                f"{train_ratio + val_ratio + test_ratio})"
            )

        rng = np.random.default_rng(seed)

        if group_by_sequence:
            # Group sample IDs by sequence_id or sol
            groups: Dict[str, List[str]] = {}
            for s in self.samples:
                key = s.sequence_id or f"SOL_{s.sol}" if s.sol is not None else s.sample_id
                groups.setdefault(key, []).append(s.sample_id)

            group_keys = list(groups.keys())
            rng.shuffle(group_keys)

            num_groups = len(group_keys)
            train_end = int(round(num_groups * train_ratio))
            val_end = int(round(num_groups * (train_ratio + val_ratio)))

            # Prevent empty partitions if group count is small
            if num_groups >= 3:
                train_end = max(1, min(train_end, num_groups - 2))
                val_end = max(train_end + 1, min(val_end, num_groups - 1))

            train_keys = group_keys[:train_end]
            val_keys = group_keys[train_end:val_end]
            test_keys = group_keys[val_end:]

            train_ids = [sid for k in train_keys for sid in groups[k]]
            val_ids = [sid for k in val_keys for sid in groups[k]]
            test_ids = [sid for k in test_keys for sid in groups[k]]
        else:
            all_ids = [s.sample_id for s in self.samples]
            rng.shuffle(all_ids)

            n = len(all_ids)
            train_end = int(round(n * train_ratio))
            val_end = int(round(n * (train_ratio + val_ratio)))

            if n >= 3:
                train_end = max(1, min(train_end, n - 2))
                val_end = max(train_end + 1, min(val_end, n - 1))

            train_ids = all_ids[:train_end]
            val_ids = all_ids[train_end:val_end]
            test_ids = all_ids[val_end:]

        # Validate disjoint sets
        set_tr = set(train_ids)
        set_va = set(val_ids)
        set_te = set(test_ids)

        assert set_tr.isdisjoint(set_va), "Leakage detected: train and val share sample IDs"
        assert set_tr.isdisjoint(set_te), "Leakage detected: train and test share sample IDs"
        assert set_va.isdisjoint(set_te), "Leakage detected: val and test share sample IDs"

        manifest = DatasetSplitManifest(
            train_ids=sorted(train_ids),
            val_ids=sorted(val_ids),
            test_ids=sorted(test_ids),
            seed=seed,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            total_samples=len(self.samples),
            metadata={
                "grouped_by_sequence": group_by_sequence,
                "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
            },
        )

        if output_manifest_path is not None:
            manifest.save(output_manifest_path)

        return manifest


# Import math at module level for float comparisons
import math

