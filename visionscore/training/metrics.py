"""
Evaluation Metrics for Mars Terrain Semantic Segmentation.

Calculates:
- Mean Intersection over Union (mIoU)
- Per-class IoU (Soil, Bedrock, Sand, Boulder)
- Pixel Accuracy
- Confusion Matrix (normalized & raw)
- Class balance distributions
"""

from typing import Dict, List, Optional
import numpy as np

from visionscore.models.mars_net import CLASS_NAMES, IGNORE_INDEX, NUM_CLASSES


class SegmentationMetrics:
    """Evaluates semantic segmentation predictions against ground-truth masks."""

    def __init__(
        self,
        num_classes: int = NUM_CLASSES,
        class_names: Optional[List[str]] = None,
        ignore_index: int = IGNORE_INDEX,
    ):
        self.num_classes = num_classes
        self.class_names = class_names or CLASS_NAMES
        self.ignore_index = ignore_index
        self.confusion_matrix = np.zeros((num_classes, num_classes), dtype=np.int64)

    def reset(self) -> None:
        self.confusion_matrix = np.zeros((self.num_classes, self.num_classes), dtype=np.int64)

    def update(self, pred: np.ndarray, target: np.ndarray) -> None:
        """
        Updates confusion matrix with predicted and ground-truth masks.
        Ignores pixels where target == ignore_index.
        """
        valid_mask = (target != self.ignore_index) & (target >= 0) & (target < self.num_classes)
        p = pred[valid_mask].astype(np.int64)
        t = target[valid_mask].astype(np.int64)

        if len(t) == 0:
            return

        indices = t * self.num_classes + p
        counts = np.bincount(indices, minlength=self.num_classes ** 2)
        self.confusion_matrix += counts.reshape(self.num_classes, self.num_classes)

    def compute(self) -> Dict[str, float]:
        """
        Computes mIoU, per-class IoU, and overall pixel accuracy.
        """
        tp = np.diag(self.confusion_matrix)
        fp = np.sum(self.confusion_matrix, axis=0) - tp
        fn = np.sum(self.confusion_matrix, axis=1) - tp

        denom = tp + fp + fn
        # Avoid division by zero for classes not present in test split
        valid_classes = denom > 0
        ious = np.zeros(self.num_classes, dtype=np.float64)
        ious[valid_classes] = tp[valid_classes] / denom[valid_classes]

        miou = float(np.mean(ious[valid_classes])) if np.any(valid_classes) else 0.0
        total_pixels = np.sum(self.confusion_matrix)
        pixel_acc = float(np.sum(tp) / total_pixels) if total_pixels > 0 else 0.0

        metrics: Dict[str, float] = {
            "mIoU": round(miou, 4),
            "pixel_accuracy": round(pixel_acc, 4),
        }

        for idx, name in enumerate(self.class_names):
            metrics[f"IoU_{name}"] = round(float(ious[idx]), 4)

        return metrics

    def get_confusion_matrix(self, normalized: bool = False) -> np.ndarray:
        if not normalized:
            return self.confusion_matrix.copy()
        row_sums = self.confusion_matrix.sum(axis=1, keepdims=True)
        return np.where(row_sums > 0, self.confusion_matrix / row_sums, 0.0)

