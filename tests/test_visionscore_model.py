"""
Unit Test Suite for Trained Mars Neural Model and Segmentation Pipeline.
"""

from pathlib import Path
import numpy as np
import pytest

from visionscore.config import EnvironmentProfile, SemanticClass, VisionConfig
from visionscore.image_input import UnifiedImage
from visionscore.models.mars_net import (
    CLASS_NAMES,
    IGNORE_INDEX,
    NUM_CLASSES,
    MarsTerrainCNN,
    ModelCheckpoint,
)
from visionscore.semantic import (
    DemoSemanticSegmentationModel,
    TrainedSemanticSegmentationModel,
    segment_terrain,
)
from visionscore.training.metrics import SegmentationMetrics


def test_mars_terrain_cnn_initialization():
    """Verify weight shapes and layer dimensions."""
    net = MarsTerrainCNN(in_channels=8, hidden_dim1=32, hidden_dim2=16, num_classes=4, seed=42)
    assert net.W1.shape == (8, 32)
    assert net.b1.shape == (32,)
    assert net.W2.shape == (32, 16)
    assert net.b2.shape == (16,)
    assert net.W3.shape == (16, 4)
    assert net.b3.shape == (4,)


def test_mars_terrain_cnn_forward():
    """Verify forward pass output dimensions and probability normalization."""
    net = MarsTerrainCNN(seed=42)
    dummy_feat = np.random.randn(32, 32, 8).astype(np.float32)
    logits, probs, cache = net.forward(dummy_feat)

    assert logits.shape == (32, 32, 4)
    assert probs.shape == (32, 32, 4)
    # Probabilities sum to 1.0 per pixel
    sums = np.sum(probs, axis=-1)
    np.testing.assert_allclose(sums, np.ones_like(sums), atol=1e-5)


def test_mars_terrain_cnn_loss_with_ignore_index():
    """Verify that ignore_index=255 pixels produce zero loss and zero gradient."""
    net = MarsTerrainCNN(seed=42)
    dummy_feat = np.random.randn(16, 16, 8).astype(np.float32)
    _, probs, _ = net.forward(dummy_feat)

    target_mask = np.full((16, 16), 255, dtype=np.int32)
    loss_mask = np.zeros((16, 16), dtype=bool)

    # 1. Purely ignored target
    loss_ignored, grad_ignored = net.compute_loss(probs, target_mask, loss_mask)
    assert loss_ignored == 0.0
    assert np.all(grad_ignored == 0.0)

    # 2. Mixed target with 1 valid pixel
    target_mask[0, 0] = 0  # SOIL
    loss_mask[0, 0] = True
    loss_mixed, grad_mixed = net.compute_loss(probs, target_mask, loss_mask)
    assert loss_mixed > 0.0
    assert not np.all(grad_mixed[0, 0] == 0.0)
    assert np.all(grad_mixed[1:, 1:] == 0.0)


def test_mars_terrain_cnn_backward_and_adam():
    """Verify backpropagation produces valid parameter gradients and updates weights."""
    net = MarsTerrainCNN(seed=42)
    dummy_feat = np.random.randn(16, 16, 8).astype(np.float32)
    target_mask = np.random.randint(0, 4, size=(16, 16), dtype=np.int32)
    loss_mask = np.ones((16, 16), dtype=bool)

    _, probs, cache = net.forward(dummy_feat)
    loss, grad_logits = net.compute_loss(probs, target_mask, loss_mask)
    grads = net.backward(grad_logits, cache)

    assert grads["W1"].shape == net.W1.shape
    assert grads["W2"].shape == net.W2.shape
    assert grads["W3"].shape == net.W3.shape

    w1_before = net.W1.copy()
    net.step_adam(grads, learning_rate=1e-2)
    assert not np.array_equal(net.W1, w1_before)


def test_model_checkpoint_save_and_load(tmp_path: Path):
    """Verify ModelCheckpoint serialization and restoration."""
    net = MarsTerrainCNN(seed=42)
    weights = net.get_weights()
    ckpt = ModelCheckpoint(
        weights=weights,
        hyperparameters={"in_channels": 8, "num_classes": 4},
        metadata={"author": "ODYSSEY AI Team"},
    )

    ckpt_path = tmp_path / "test_weights.npz"
    ckpt.save(ckpt_path)
    assert ckpt_path.exists()

    loaded = ModelCheckpoint.load(ckpt_path)
    assert loaded.hyperparameters["num_classes"] == 4
    assert loaded.metadata["author"] == "ODYSSEY AI Team"
    np.testing.assert_allclose(loaded.weights["W1"], weights["W1"])


def test_trained_semantic_segmentation_model_inference():
    """Verify TrainedSemanticSegmentationModel executes neural inference and adheres to schema."""
    ckpt_path = Path("outputs/models/mars_cnn_weights.npz")
    if not ckpt_path.exists():
        pytest.skip("Trained checkpoint not found on disk.")

    model = TrainedSemanticSegmentationModel(checkpoint_path=ckpt_path)
    assert model.is_real_ai_model is True
    assert model.is_loaded is True

    from visionscore.image_input import ImageInputHandler
    test_rgb = np.full((100, 100, 3), 150, dtype=np.uint8)
    uimg = ImageInputHandler().ingest(test_rgb, environment=EnvironmentProfile.MARS)
    config = VisionConfig()

    result = model.segment(uimg, config)
    assert result.segmentation_mask.shape == (100, 100)
    assert result.color_map.shape == (100, 100, 3)
    assert result.overlay_image.shape == (100, 100, 3)
    assert result.model_status["is_real_ai_model"] is True
    assert "TRAINED_NEURAL_NETWORK_CNN" in result.model_status["model_type"]

    # Dominant class must be one of the 4 AI4Mars classes
    assert result.dominant_class in ["SOIL", "BEDROCK", "SAND", "BOULDER"]


def test_segment_terrain_hot_swap_model():
    """Verify segment_terrain accepts custom trained model and retains navigation contract."""
    ckpt_path = Path("outputs/models/mars_cnn_weights.npz")
    if not ckpt_path.exists():
        pytest.skip("Trained checkpoint not found on disk.")

    model = TrainedSemanticSegmentationModel(checkpoint_path=ckpt_path)
    test_rgb = np.random.randint(50, 200, size=(128, 128, 3), dtype=np.uint8)

    result = segment_terrain(test_rgb, environment=EnvironmentProfile.MARS, model=model)
    assert result.model_status["is_real_ai_model"] is True

    # Traversability summary percentages sum to 100.0%
    total_pct = sum(result.traversability_summary.values())
    assert pytest.approx(total_pct, abs=1e-2) == 100.0
