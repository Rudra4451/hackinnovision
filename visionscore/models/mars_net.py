"""
Mars Terrain Neural Segmentation Architecture.

Lightweight, fully differentiable multi-scale convolutional neural network (MarsTerrainCNN)
engineered for CPU-based training and embedded rover inference.

Characteristics:
- Multi-scale spatial feature integration (RGB, local luminance context, spatial texture gradients).
- Fully connected non-linear projection bottleneck (LeakyReLU activation).
- Native ignore_index (255) exclusion during loss and backpropagation.
- Zero external DLL / heavy-framework dependencies; runs with accelerated vectorization on NumPy/SciPy.
- Full provenance serialization (weights, hyperparameters, metadata, metrics).
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from scipy import ndimage

logger = logging.getLogger(__name__)

NUM_CLASSES = 4
CLASS_NAMES = ["SOIL", "BEDROCK", "SAND", "BOULDER"]
IGNORE_INDEX = 255


@dataclass
class ModelCheckpoint:
    """Container for serializing and restoring neural model weights and provenance."""
    weights: Dict[str, np.ndarray]
    hyperparameters: Dict[str, Any]
    metadata: Dict[str, Any]

    def save(self, path: Union[str, Path]) -> Path:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Save weights in compressed npz format
        np.savez_compressed(
            out_path,
            **self.weights,
            __hyperparameters__=json.dumps(self.hyperparameters),
            __metadata__=json.dumps(self.metadata),
        )
        return out_path

    @classmethod
    def load(cls, path: Union[str, Path]) -> "ModelCheckpoint":
        in_path = Path(path)
        if not in_path.exists():
            raise FileNotFoundError(f"Checkpoint file does not exist: {in_path}")
        
        data = np.load(in_path, allow_pickle=True)
        hyperparameters = json.loads(str(data["__hyperparameters__"]))
        metadata = json.loads(str(data["__metadata__"]))

        weights = {k: data[k] for k in data.files if not k.startswith("__")}
        return cls(weights=weights, hyperparameters=hyperparameters, metadata=metadata)


class MarsTerrainCNN:
    """
    Differentiable Multi-Scale Convolutional Feature Network for Mars Terrain Segmentation.

    Input: (H, W, 3) Mars RGB image in [0, 255] or [0.0, 1.0].
    Output: (H, W, 4) Logits for [0: SOIL, 1: BEDROCK, 2: SAND, 3: BOULDER].
    """

    def __init__(
        self,
        in_channels: int = 8,
        hidden_dim1: int = 32,
        hidden_dim2: int = 16,
        num_classes: int = NUM_CLASSES,
        seed: int = 42,
    ):
        self.in_channels = in_channels
        self.hidden_dim1 = hidden_dim1
        self.hidden_dim2 = hidden_dim2
        self.num_classes = num_classes

        # Initialize weights with He (Kaiming) normal initialization
        rng = np.random.default_rng(seed)
        self.W1 = (rng.standard_normal((in_channels, hidden_dim1), dtype=np.float32) *
                   np.sqrt(2.0 / in_channels).astype(np.float32))
        self.b1 = np.zeros((hidden_dim1,), dtype=np.float32)

        self.W2 = (rng.standard_normal((hidden_dim1, hidden_dim2), dtype=np.float32) *
                   np.sqrt(2.0 / hidden_dim1).astype(np.float32))
        self.b2 = np.zeros((hidden_dim2,), dtype=np.float32)

        self.W3 = (rng.standard_normal((hidden_dim2, num_classes), dtype=np.float32) *
                   np.sqrt(2.0 / hidden_dim2).astype(np.float32))
        self.b3 = np.zeros((num_classes,), dtype=np.float32)

        # Adam optimizer state
        self.m = {k: np.zeros_like(getattr(self, k)) for k in ["W1", "b1", "W2", "b2", "W3", "b3"]}
        self.v = {k: np.zeros_like(getattr(self, k)) for k in ["W1", "b1", "W2", "b2", "W3", "b3"]}
        self.t = 0

    def extract_features(self, rgb: np.ndarray) -> np.ndarray:
        """
        Extracts multi-scale photometric and texture features from raw Mars RGB frame.
        Features per pixel:
        - 0, 1, 2: Normalized RGB channels (color balance)
        - 3: Standard luminance (Y)
        - 4: Redness ratio (Martian ferric regolith indicator)
        - 5: Local spatial blur (low-frequency context)
        - 6: Horizontal/vertical gradient magnitude (texture/edges)
        - 7: High-pass Laplacian (fine rock grain)
        """
        arr = rgb.astype(np.float32)
        if arr.max() > 1.0:
            arr /= 255.0

        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        redness = (r - b) / (r + b + 1e-4)

        # Spatial multi-scale filtering via SciPy ndimage
        blur = ndimage.gaussian_filter(luma, sigma=1.5)
        sobel_x = ndimage.sobel(luma, axis=1) / 8.0
        sobel_y = ndimage.sobel(luma, axis=0) / 8.0
        grad_mag = np.hypot(sobel_x, sobel_y)
        laplacian = ndimage.laplace(luma) / 8.0

        features = np.stack(
            [r, g, b, luma, redness, blur, grad_mag, laplacian],
            axis=-1,
        ).astype(np.float32)
        return features

    def forward(
        self,
        features: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
        """
        Forward pass through the neural network.
        
        Args:
            features: (H, W, in_channels) float32 feature tensor.
            
        Returns:
            Tuple of (logits, probabilities, cache)
        """
        h, w, _ = features.shape

        # Layer 1: Linear + LeakyReLU
        z1 = np.dot(features, self.W1) + self.b1
        a1 = np.where(z1 > 0, z1, 0.1 * z1)

        # Layer 2: Linear + LeakyReLU
        z2 = np.dot(a1, self.W2) + self.b2
        a2 = np.where(z2 > 0, z2, 0.1 * z2)

        # Layer 3: Linear Logits
        logits = np.dot(a2, self.W3) + self.b3

        # Softmax (numerically stable)
        shift_logits = logits - np.max(logits, axis=-1, keepdims=True)
        exp_logits = np.exp(shift_logits)
        probs = exp_logits / (np.sum(exp_logits, axis=-1, keepdims=True) + 1e-7)

        cache = {
            "features": features,
            "z1": z1,
            "a1": a1,
            "z2": z2,
            "a2": a2,
            "logits": logits,
            "probs": probs,
        }
        return logits, probs, cache

    def compute_loss(
        self,
        probs: np.ndarray,
        target_mask: np.ndarray,
        loss_mask: np.ndarray,
        class_weights: Optional[np.ndarray] = None,
    ) -> Tuple[float, np.ndarray]:
        """
        Computes masked cross-entropy loss and gradient with respect to logits.
        Pixels where loss_mask == 0 (e.g. ignore_index=255) contribute 0 loss and 0 gradient.
        """
        h, w = target_mask.shape
        active_count = float(np.sum(loss_mask))
        if active_count == 0:
            return 0.0, np.zeros_like(probs)

        # One-hot encoding for active targets
        clamped_target = np.clip(target_mask, 0, self.num_classes - 1)
        one_hot = np.eye(self.num_classes, dtype=np.float32)[clamped_target]  # (H, W, 4)

        # Cross-entropy: -sum(y * log(p))
        log_probs = np.log(np.clip(probs, 1e-7, 1.0))
        nll = -np.sum(one_hot * log_probs, axis=-1)  # (H, W)

        if class_weights is not None:
            weights_per_pixel = class_weights[clamped_target]
            nll *= weights_per_pixel

        masked_nll = nll * loss_mask
        loss = float(np.sum(masked_nll) / active_count)

        # Gradient dL/d(logits) = (probs - one_hot) * loss_mask / active_count
        grad_logits = (probs - one_hot) * loss_mask[..., np.newaxis]
        if class_weights is not None:
            grad_logits *= weights_per_pixel[..., np.newaxis]
        grad_logits /= active_count

        return loss, grad_logits

    def backward(
        self,
        grad_logits: np.ndarray,
        cache: Dict[str, np.ndarray],
    ) -> Dict[str, np.ndarray]:
        """
        Analytical backpropagation computing gradients for all parameters.
        """
        features = cache["features"]
        z1 = cache["z1"]
        a1 = cache["a1"]
        z2 = cache["z2"]
        a2 = cache["a2"]

        # Gradients for Layer 3 (logits)
        # grad_logits: (H, W, num_classes)
        # a2: (H, W, hidden_dim2)
        dW3 = np.tensordot(a2, grad_logits, axes=([0, 1], [0, 1]))
        db3 = np.sum(grad_logits, axis=(0, 1))

        # Backprop into a2
        da2 = np.dot(grad_logits, self.W3.T)
        dz2 = np.where(z2 > 0, da2, 0.1 * da2)

        # Gradients for Layer 2
        dW2 = np.tensordot(a1, dz2, axes=([0, 1], [0, 1]))
        db2 = np.sum(dz2, axis=(0, 1))

        # Backprop into a1
        da1 = np.dot(dz2, self.W2.T)
        dz1 = np.where(z1 > 0, da1, 0.1 * da1)

        # Gradients for Layer 1
        dW1 = np.tensordot(features, dz1, axes=([0, 1], [0, 1]))
        db1 = np.sum(dz1, axis=(0, 1))

        return {
            "W1": dW1, "b1": db1,
            "W2": dW2, "b2": db2,
            "W3": dW3, "b3": db3,
        }

    def step_adam(
        self,
        grads: Dict[str, np.ndarray],
        learning_rate: float = 1e-3,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
        weight_decay: float = 1e-4,
    ) -> None:
        """Applies Adam optimizer step with L2 weight decay."""
        self.t += 1
        for param_name in ["W1", "b1", "W2", "b2", "W3", "b3"]:
            g = grads[param_name]
            p = getattr(self, param_name)

            if weight_decay > 0 and "W" in param_name:
                g = g + weight_decay * p

            # First and second moment updates
            self.m[param_name] = beta1 * self.m[param_name] + (1.0 - beta1) * g
            self.v[param_name] = beta2 * self.v[param_name] + (1.0 - beta2) * (g ** 2)

            # Bias correction
            m_hat = self.m[param_name] / (1.0 - beta1 ** self.t)
            v_hat = self.v[param_name] / (1.0 - beta2 ** self.t)

            # Parameter update
            new_p = p - learning_rate * m_hat / (np.sqrt(v_hat) + eps)
            setattr(self, param_name, new_p.astype(np.float32))

    def predict(self, rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Inference method returning discrete class mask (H, W) and confidence map (H, W).
        """
        features = self.extract_features(rgb)
        _, probs, _ = self.forward(features)
        pred_mask = np.argmax(probs, axis=-1).astype(np.uint8)
        confidence = np.max(probs, axis=-1).astype(np.float32)
        return pred_mask, confidence

    def get_weights(self) -> Dict[str, np.ndarray]:
        return {
            "W1": self.W1.copy(), "b1": self.b1.copy(),
            "W2": self.W2.copy(), "b2": self.b2.copy(),
            "W3": self.W3.copy(), "b3": self.b3.copy(),
        }

    def load_weights(self, weights: Dict[str, np.ndarray]) -> None:
        for k in ["W1", "b1", "W2", "b2", "W3", "b3"]:
            if k in weights:
                setattr(self, k, weights[k].astype(np.float32))
