"""
Mars AI Model Training Script.

Executes training on the curated AI4Mars dataset and persists model weights
and validation metrics to outputs/models/.
"""

import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from visionscore.training.trainer import MarsTrainer


def main():
    print("=" * 60)
    print("ODYSSEY VisionScore — Mars Terrain AI Model Training")
    print("=" * 60)

    trainer = MarsTrainer(
        dataset_root=REPO_ROOT / "data" / "ai4mars",
        target_size=(128, 128),
        learning_rate=3e-3,
        weight_decay=1e-4,
        seed=42,
    )

    results = trainer.train(
        epochs=12,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        output_dir=REPO_ROOT / "outputs" / "models",
    )

    print("\nTraining run successfully finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
