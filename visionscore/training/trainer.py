"""
Mars Terrain Model Trainer.

Handles reproducible training loops, validation evaluation, metric logging,
and model weight checkpointing.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from visionscore.dataset.ai4mars import AI4MarsDataset, DatasetSplitManifest
from visionscore.models.mars_net import (
    CLASS_NAMES,
    IGNORE_INDEX,
    MarsTerrainCNN,
    ModelCheckpoint,
)
from visionscore.training.metrics import SegmentationMetrics

logger = logging.getLogger(__name__)


class MarsTrainer:
    """Trains and benchmarks MarsTerrainCNN on AI4Mars rover imagery."""

    def __init__(
        self,
        model: Optional[MarsTerrainCNN] = None,
        dataset_root: Union[str, Path] = "data/ai4mars",
        target_size: Tuple[int, int] = (128, 128),
        learning_rate: float = 2e-3,
        weight_decay: float = 1e-4,
        class_weights: Optional[List[float]] = None,
        seed: int = 42,
    ):
        self.dataset_root = Path(dataset_root)
        self.target_size = target_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.seed = seed

        # Default class weights: penalize rare boulder hazards higher
        # [0: SOIL=1.0, 1: BEDROCK=1.0, 2: SAND=1.2, 3: BOULDER=3.0]
        if class_weights is not None:
            self.class_weights = np.array(class_weights, dtype=np.float32)
        else:
            self.class_weights = np.array([1.0, 1.0, 1.2, 3.0], dtype=np.float32)

        self.model = model or MarsTerrainCNN(seed=seed)
        self.metrics = SegmentationMetrics()

    def train(
        self,
        epochs: int = 10,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        output_dir: Union[str, Path] = "outputs/models",
    ) -> Dict[str, Any]:
        """
        Executes end-to-end training and evaluation.

        Returns:
            Dictionary containing final test metrics, training history, and checkpoint path.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Load dataset
        full_ds = AI4MarsDataset(
            root_dir=self.dataset_root,
            target_size=self.target_size,
            require_masks=True,
        )

        manifest = full_ds.split(
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=self.seed,
            group_by_sequence=True,
            output_manifest_path=out_dir / "split_manifest.json",
        )

        train_indices = [i for i, s in enumerate(full_ds.samples) if s.sample_id in manifest.train_ids]
        val_indices = [i for i, s in enumerate(full_ds.samples) if s.sample_id in manifest.val_ids]
        test_indices = [i for i, s in enumerate(full_ds.samples) if s.sample_id in manifest.test_ids]

        # Preload extracted features for fast CPU iteration
        print(f"Preloading and extracting spatial features ({len(full_ds)} samples)...")
        features_cache = []
        for i in range(len(full_ds)):
            sample = full_ds[i]
            feat = self.model.extract_features(sample["image"])
            features_cache.append({
                "features": feat,
                "target": sample["training_mask"],
                "loss_mask": sample["loss_mask"],
            })

        print(f"Dataset split: Train={len(train_indices)}, Val={len(val_indices)}, Test={len(test_indices)}")
        print(f"Starting training on CPU ({epochs} epochs, lr={self.learning_rate})...")

        best_val_loss = float("inf")
        best_weights = self.model.get_weights()
        history: List[Dict[str, Any]] = []

        start_time = time.perf_counter()

        for epoch in range(1, epochs + 1):
            epoch_loss = 0.0
            # Shuffle training indices
            rng = np.random.default_rng(self.seed + epoch)
            shuffled_train = rng.permutation(train_indices)

            for idx in shuffled_train:
                item = features_cache[idx]
                feat = item["features"]
                target = item["target"]
                lmask = item["loss_mask"]

                # Forward
                _, probs, cache = self.model.forward(feat)

                # Loss & backward
                loss, grad_logits = self.model.compute_loss(
                    probs, target, lmask, class_weights=self.class_weights
                )
                grads = self.model.backward(grad_logits, cache)

                # Adam step
                self.model.step_adam(
                    grads,
                    learning_rate=self.learning_rate,
                    weight_decay=self.weight_decay,
                )
                epoch_loss += loss

            avg_train_loss = epoch_loss / max(1, len(train_indices))

            # Validation step
            val_loss = 0.0
            self.metrics.reset()
            for idx in val_indices:
                item = features_cache[idx]
                _, probs, _ = self.model.forward(item["features"])
                vloss, _ = self.model.compute_loss(probs, item["target"], item["loss_mask"])
                val_loss += vloss
                preds = np.argmax(probs, axis=-1)
                self.metrics.update(preds, item["target"])

            avg_val_loss = val_loss / max(1, len(val_indices))
            val_metrics = self.metrics.compute()

            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_weights = self.model.get_weights()

            history.append({
                "epoch": epoch,
                "train_loss": round(avg_train_loss, 4),
                "val_loss": round(avg_val_loss, 4),
                "val_mIoU": val_metrics["mIoU"],
                "val_pixel_acc": val_metrics["pixel_accuracy"],
            })

            print(
                f"  Epoch {epoch:02d}/{epochs:02d} | "
                f"Train Loss: {avg_train_loss:.4f} | "
                f"Val Loss: {avg_val_loss:.4f} | "
                f"Val mIoU: {val_metrics['mIoU']:.4f}"
            )

        total_training_sec = time.perf_counter() - start_time

        # Restore best weights for test evaluation
        self.model.load_weights(best_weights)

        # Held-out Test Evaluation
        print("\nEvaluating on held-out test split...")
        self.metrics.reset()
        latencies = []
        for idx in test_indices:
            raw_sample = full_ds[idx]
            t0 = time.perf_counter()
            pred, _ = self.model.predict(raw_sample["image"])
            latencies.append((time.perf_counter() - t0) * 1000.0)
            self.metrics.update(pred, raw_sample["training_mask"])

        test_metrics = self.metrics.compute()
        avg_latency_ms = float(np.mean(latencies)) if latencies else 0.0

        checkpoint = ModelCheckpoint(
            weights=best_weights,
            hyperparameters={
                "in_channels": self.model.in_channels,
                "hidden_dim1": self.model.hidden_dim1,
                "hidden_dim2": self.model.hidden_dim2,
                "num_classes": self.model.num_classes,
                "class_names": CLASS_NAMES,
                "learning_rate": self.learning_rate,
                "weight_decay": self.weight_decay,
                "epochs": epochs,
                "target_size": list(self.target_size),
            },
            metadata={
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "dataset": "NASA JPL AI4Mars Curated Subset",
                "training_device": "CPU (Optimized Vectorized NumPy)",
                "total_training_time_seconds": round(total_training_sec, 2),
                "avg_inference_latency_ms": round(avg_latency_ms, 2),
                "test_metrics": test_metrics,
            },
        )

        checkpoint_path = out_dir / "mars_cnn_weights.npz"
        checkpoint.save(checkpoint_path)

        metrics_report = {
            "model_name": "MarsTerrainCNN-v1.0 (AI4Mars Trained)",
            "trained_checkpoint": str(checkpoint_path),
            "test_metrics": test_metrics,
            "inference_latency_ms": round(avg_latency_ms, 2),
            "confusion_matrix": self.metrics.get_confusion_matrix().tolist(),
            "training_history": history,
            "metadata": checkpoint.metadata,
        }

        with open(out_dir / "metrics.json", "w") as f:
            json.dump(metrics_report, f, indent=2)

        print(f"\nTraining Complete! Checkpoint saved to: {checkpoint_path}")
        print(f"Test mIoU: {test_metrics['mIoU']:.4f} | Pixel Acc: {test_metrics['pixel_accuracy']:.4f}")
        for cname in CLASS_NAMES:
            print(f"  Class {cname:7s} IoU: {test_metrics.get(f'IoU_{cname}', 0.0):.4f}")
        print(f"Avg Inference Latency: {avg_latency_ms:.2f} ms")

        return metrics_report
