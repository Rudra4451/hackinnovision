"""
Unified Image Input Foundation for ODYSSEY VisionScore (Stage 1).

Provides independent, production-grade adapters for:
1. ImageUploadSource: Uploaded local files, raw byte buffers, or NumPy arrays.
2. CameraFrameSource: Live webcam streams, rover mast cams, and simulated feeds.

Both adapters return a standardized UnifiedImage data model.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import uuid

import numpy as np
from PIL import Image

from visionscore.config import EnvironmentProfile, VisionConfig


class VisionInputError(Exception):
    """Base exception for VisionScore input errors."""
    pass


class InvalidImageError(VisionInputError):
    """Raised when an image file, buffer, or encoding is corrupted or unreadable."""
    pass


class EmptyImageError(VisionInputError):
    """Raised when an input image has zero bytes or zero dimension."""
    pass


class UnsupportedResolutionError(VisionInputError):
    """Raised when an image falls below minimum or exceeds allowed resolution bounds."""
    pass


class CameraUnavailableError(VisionInputError):
    """Raised when the requested camera hardware device is not found or disconnected."""
    pass


class CameraPermissionError(VisionInputError):
    """Raised when the operating system or hardware driver denies access to the camera."""
    pass


@dataclass
class ImageMetadata:
    """Standardized metadata container attached to every ingested image frame."""
    image_id: str
    timestamp_utc: str
    source_type: str
    environment: EnvironmentProfile
    width: int
    height: int
    channels: int
    original_format: str
    file_size_bytes: Optional[int] = None
    camera_model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "timestamp_utc": self.timestamp_utc,
            "source_type": self.source_type,
            "environment": self.environment.value,
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "original_format": self.original_format,
            "file_size_bytes": self.file_size_bytes,
            "camera_model": self.camera_model,
            "extra": self.extra,
        }


@dataclass
class UnifiedImage:
    """
    Common normalized image representation across all VisionScore inputs.

    Attributes:
        image_id: Unique RFC 4122 identifier.
        image: 2D or 3D NumPy array of pixels (H, W, 3) uint8 RGB or (H, W) uint8.
        source: Origin descriptor ('upload', 'live_camera', 'simulated_camera').
        environment: Environmental profile (MARS, EARTH, SIMULATION).
        timestamp: ISO 8601 UTC acquisition timestamp.
        metadata: Detailed image provenance and optical parameters.
    """
    image_id: str
    image: np.ndarray
    source: str
    environment: EnvironmentProfile
    timestamp: str
    metadata: Dict[str, Any]

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.image.shape

    @property
    def height(self) -> int:
        return self.image.shape[0]

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def channels(self) -> int:
        return self.image.shape[2] if self.image.ndim == 3 else 1

    def to_pil(self) -> Image.Image:
        """Converts the internal NumPy buffer to a PIL Image instance."""
        if self.image.ndim == 2:
            return Image.fromarray(self.image, mode="L")
        return Image.fromarray(self.image, mode="RGB")

    def save(self, path: Union[str, Path], format: Optional[str] = None) -> Path:
        """
        Explicitly persists the image buffer to disk.
        Camera frames are kept in-memory by default and only written when called here.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pil_img = self.to_pil()
        pil_img.save(target, format=format)
        return target


def _normalize_image_array(
    pil_img: Image.Image,
    max_dimension: int = 1920,
    min_dimension: int = 16,
) -> Tuple[np.ndarray, Image.Image]:
    """Ensures image is converted to RGB uint8 and downsamples efficiently if exceeding max_dimension."""
    w, h = pil_img.size
    if w < min_dimension or h < min_dimension:
        raise UnsupportedResolutionError(
            f"Image dimensions ({w}x{h}) are below minimum required resolution ({min_dimension}x{min_dimension})."
        )

    # Convert grayscale or RGBA to clean RGB
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # High-performance resizing if exceeding maximum operational dimension
    max_side = max(w, h)
    if max_side > max_dimension:
        scale = max_dimension / float(max_side)
        new_w = max(min_dimension, int(w * scale))
        new_h = max(min_dimension, int(h * scale))
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    arr = np.asarray(pil_img, dtype=np.uint8)
    return arr, pil_img


# ==============================================================================
# Adapter 1: ImageUploadSource
# ==============================================================================

class ImageUploadSource:
    """
    Adapter for processing uploaded terrain images from local paths, byte buffers, or arrays.
    """

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()

    def load_from_path(
        self,
        file_path: Union[str, Path],
        environment: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Loads and validates an image from a filesystem path."""
        path = Path(file_path)
        if not path.exists():
            raise InvalidImageError(f"File not found: '{file_path}'")
        if path.is_dir() or path.stat().st_size == 0:
            raise EmptyImageError(f"Image file is empty or invalid: '{file_path}'")

        try:
            with open(path, "rb") as f:
                raw_bytes = f.read()
            return self.load_from_bytes(
                raw_bytes,
                filename=path.name,
                environment=environment,
                source_descriptor=f"upload_file:{path.name}",
            )
        except (InvalidImageError, EmptyImageError, UnsupportedResolutionError):
            raise
        except Exception as e:
            raise InvalidImageError(f"Failed to read image at '{file_path}': {e}") from e

    def load_from_bytes(
        self,
        data: bytes,
        filename: Optional[str] = None,
        environment: Optional[EnvironmentProfile] = None,
        source_descriptor: str = "upload_bytes",
    ) -> UnifiedImage:
        """Decodes raw byte buffer into UnifiedImage representation."""
        if not data or len(data) == 0:
            raise EmptyImageError("Provided byte buffer is empty (0 bytes).")

        try:
            pil_img = Image.open(io.BytesIO(data))
            pil_img.verify()  # Validate image header integrity
            # Image.open must be reopened after verify()
            pil_img = Image.open(io.BytesIO(data))
            orig_format = pil_img.format or "UNKNOWN"
            orig_size = pil_img.size
        except Exception as e:
            raise InvalidImageError(f"Byte buffer is not a recognized or valid image format: {e}") from e

        arr, pil_img = _normalize_image_array(
            pil_img,
            max_dimension=self.config.max_input_dimension,
            min_dimension=self.config.min_input_dimension,
        )

        active_env = environment or self.config.default_environment
        img_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        meta = ImageMetadata(
            image_id=img_id,
            timestamp_utc=now_utc,
            source_type=source_descriptor,
            environment=active_env,
            width=arr.shape[1],
            height=arr.shape[0],
            channels=arr.shape[2] if arr.ndim == 3 else 1,
            original_format=orig_format,
            file_size_bytes=len(data),
            extra={
                "original_dimensions": list(orig_size),
                "filename": filename or "in_memory_upload",
            },
        )

        return UnifiedImage(
            image_id=img_id,
            image=arr,
            source="upload",
            environment=active_env,
            timestamp=now_utc,
            metadata=meta.to_dict(),
        )

    def load_from_array(
        self,
        array: np.ndarray,
        environment: Optional[EnvironmentProfile] = None,
        source_descriptor: str = "upload_numpy_array",
    ) -> UnifiedImage:
        """Wraps an existing 2D/3D NumPy array into UnifiedImage representation."""
        if not isinstance(array, np.ndarray):
            raise InvalidImageError(f"Expected numpy ndarray, got {type(array).__name__}")
        if array.size == 0 or array.ndim not in (2, 3):
            raise EmptyImageError(f"Invalid array shape for image representation: {array.shape}")

        if array.ndim == 3 and array.shape[2] not in (1, 3, 4):
            raise InvalidImageError(f"Unsupported channel dimension in array: {array.shape}")

        try:
            # Handle float arrays in [0.0, 1.0] or [0.0, 255.0]
            if np.issubdtype(array.dtype, np.floating):
                if np.nanmax(array) <= 1.0:
                    uint_arr = np.clip(array * 255.0, 0, 255).astype(np.uint8)
                else:
                    uint_arr = np.clip(array, 0, 255).astype(np.uint8)
            else:
                uint_arr = np.clip(array, 0, 255).astype(np.uint8)

            pil_img = Image.fromarray(uint_arr)
            arr, _ = _normalize_image_array(
                pil_img,
                max_dimension=self.config.max_input_dimension,
                min_dimension=self.config.min_input_dimension,
            )
        except Exception as e:
            raise InvalidImageError(f"Failed to normalize NumPy array to image: {e}") from e

        active_env = environment or self.config.default_environment
        img_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        meta = ImageMetadata(
            image_id=img_id,
            timestamp_utc=now_utc,
            source_type=source_descriptor,
            environment=active_env,
            width=arr.shape[1],
            height=arr.shape[0],
            channels=arr.shape[2] if arr.ndim == 3 else 1,
            original_format="NUMPY_ARRAY",
            file_size_bytes=arr.nbytes,
            extra={"input_dtype": str(array.dtype), "original_shape": list(array.shape)},
        )

        return UnifiedImage(
            image_id=img_id,
            image=arr,
            source="upload",
            environment=active_env,
            timestamp=now_utc,
            metadata=meta.to_dict(),
        )


# ==============================================================================
# Adapter 2: CameraFrameSource & Streams
# ==============================================================================

class BaseCameraStream(ABC):
    """Abstract base class defining interface contracts for live and simulated camera feeds."""

    @abstractmethod
    def capture_frame(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Captures a single raw frame and camera metadata."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the camera source is reachable and active."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Releases underlying hardware or network stream resources."""
        pass


class SimulatedCameraFeed(BaseCameraStream):
    """
    High-fidelity procedural Martian rover mast camera simulator.

    Generates synthetic frames with customizable terrain features, ferric dust
    albedo, boulder clusters, and horizon geometry.
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (480, 640),
        seed: int = 42,
        environment: EnvironmentProfile = EnvironmentProfile.MARS,
        inject_obstacle: bool = False,
        terrain_mode: str = "MIXED",
    ):
        self.resolution = resolution  # (H, W)
        self.seed = seed
        self.environment = environment
        self.inject_obstacle = inject_obstacle
        self.terrain_mode = terrain_mode.upper()
        self._active = True
        self._frame_count = 0

    def set_obstacle_injection(self, enable: bool = True) -> None:
        """Dynamically enables or disables simulated prominent obstacle injection."""
        self.inject_obstacle = enable

    def set_terrain_mode(self, mode: str = "MIXED") -> None:
        """Sets the simulated terrain profile: 'MIXED', 'SOIL', 'BEDROCK', 'SAND', 'BOULDER'."""
        self.terrain_mode = mode.upper()

    def is_available(self) -> bool:
        return self._active

    def release(self) -> None:
        self._active = False

    def capture_frame(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        if not self._active:
            raise CameraUnavailableError("Simulated camera feed has been released and is inactive.")

        h, w = self.resolution
        rng = np.random.default_rng(self.seed + self._frame_count)
        self._frame_count += 1

        # Coordinate grid for optical perspective projection
        yy, xx = np.meshgrid(np.linspace(0, 1, h), np.linspace(0, 1, w), indexing="ij")

        # Ground plane with distance perspective gradient
        distance = yy  # 0 at horizon, 1 at rover base
        undulation = (
            0.15 * np.sin(xx * 12.0) * np.cos(yy * 8.0)
            + 0.10 * np.sin(xx * 24.0 + 1.0)
            + 0.05 * rng.standard_normal((h, w))
        )

        if self.environment in (EnvironmentProfile.MARS, EnvironmentProfile.SIMULATION_MARS):
            mode = self.terrain_mode

            if mode == "SOIL":
                # Pure Martian ferric oxide cohesive soil plain
                base_r = np.clip(185.0 + 35.0 * undulation, 0, 255)
                base_g = np.clip(95.0 + 25.0 * undulation, 0, 255)
                base_b = np.clip(55.0 + 15.0 * undulation, 0, 255)

            elif mode == "BEDROCK":
                # Solid exposed basaltic/silicate bedrock pavement
                base_r = np.clip(114.0 + 20.0 * undulation, 0, 255)
                base_g = np.clip(116.0 + 20.0 * undulation, 0, 255)
                base_b = np.clip(120.0 + 20.0 * undulation, 0, 255)
                # Planar fractures and joint lines
                fractures = (np.sin(xx * 25.0 + yy * 15.0) > 0.94) | (np.sin(yy * 22.0 - xx * 18.0) > 0.95)
                base_r[fractures] = np.clip(base_r[fractures] - 35.0, 0, 255)
                base_g[fractures] = np.clip(base_g[fractures] - 35.0, 0, 255)
                base_b[fractures] = np.clip(base_b[fractures] - 35.0, 0, 255)

            elif mode == "SAND":
                # Aeolian sand dune field with ripple wave patterns
                ripples = 0.20 * np.sin(xx * 40.0 + yy * 25.0) + 0.10 * np.sin(xx * 80.0)
                base_r = np.clip(205.0 + 25.0 * (undulation + ripples), 0, 255)
                base_g = np.clip(155.0 + 20.0 * (undulation + ripples), 0, 255)
                base_b = np.clip(85.0 + 15.0 * (undulation + ripples), 0, 255)

            elif mode == "BOULDER":
                # Rocky terrain with scattered boulders and scree
                base_r = np.clip(155.0 + 30.0 * undulation, 0, 255)
                base_g = np.clip(100.0 + 25.0 * undulation, 0, 255)
                base_b = np.clip(65.0 + 20.0 * undulation, 0, 255)
                # Multiple boulder clusters with sharp gradient relief
                for c_y, c_x, radius in [(0.65, 0.45, 0.16), (0.75, 0.72, 0.12), (0.50, 0.30, 0.10)]:
                    b_dist = np.hypot(yy - c_y, xx - c_x)
                    b_mask = b_dist < radius
                    b_noise = rng.normal(0, 40.0, (h, w))
                    base_r[b_mask] = np.clip(45.0 + b_noise[b_mask], 0, 255)
                    base_g[b_mask] = np.clip(40.0 + b_noise[b_mask], 0, 255)
                    base_b[b_mask] = np.clip(35.0 + b_noise[b_mask], 0, 255)

            else:
                # MIXED (Default): Composite Mars scene with all 4 AI4Mars classes
                # Base: Ferric Martian soil
                base_r = np.clip(185.0 + 35.0 * undulation, 0, 255)
                base_g = np.clip(95.0 + 25.0 * undulation, 0, 255)
                base_b = np.clip(55.0 + 15.0 * undulation, 0, 255)

                # Bedrock shelf on left: solid gray rock pavement (low redness)
                bedrock_shelf = (xx < 0.42) & (yy > 0.35)
                base_r[bedrock_shelf] = np.clip(114.0 + 18.0 * undulation[bedrock_shelf], 0, 255)
                base_g[bedrock_shelf] = np.clip(116.0 + 18.0 * undulation[bedrock_shelf], 0, 255)
                base_b[bedrock_shelf] = np.clip(120.0 + 18.0 * undulation[bedrock_shelf], 0, 255)

                # Sand ripples on right: golden/ochre aeolian dunes
                sand_patch = (xx > 0.52) & (yy > 0.25) & (yy < 0.75)
                ripples = 0.20 * np.sin(xx * 40.0 + yy * 25.0)
                base_r[sand_patch] = np.clip(205.0 + 25.0 * (undulation[sand_patch] + ripples[sand_patch]), 0, 255)
                base_g[sand_patch] = np.clip(155.0 + 20.0 * (undulation[sand_patch] + ripples[sand_patch]), 0, 255)
                base_b[sand_patch] = np.clip(85.0 + 15.0 * (undulation[sand_patch] + ripples[sand_patch]), 0, 255)

                # Basaltic boulder cluster at bottom right
                boulder_dist = np.hypot(yy - 0.75, xx - 0.70)
                boulder_mask = boulder_dist < 0.13
                b_noise = rng.normal(0, 38.0, (h, w))
                base_r[boulder_mask] = np.clip(48.0 + b_noise[boulder_mask], 0, 255)
                base_g[boulder_mask] = np.clip(42.0 + b_noise[boulder_mask], 0, 255)
                base_b[boulder_mask] = np.clip(38.0 + b_noise[boulder_mask], 0, 255)

        elif self.environment == EnvironmentProfile.EARTH:
            # Earth regolith / gravel mix
            base_r = np.clip(130.0 + 35.0 * undulation, 0, 255)
            base_g = np.clip(125.0 + 35.0 * undulation, 0, 255)
            base_b = np.clip(110.0 + 30.0 * undulation, 0, 255)
        else:
            # Legacy Simulation neutral gray-ochre
            base_r = np.clip(150.0 + 30.0 * undulation, 0, 255)
            base_g = np.clip(140.0 + 30.0 * undulation, 0, 255)
            base_b = np.clip(120.0 + 25.0 * undulation, 0, 255)

        # If prominent obstacle injection is enabled, add a large jagged obstacle formation
        if self.inject_obstacle:
            obs_dist = np.hypot(yy - 0.65, xx - 0.50)
            obs_mask = obs_dist < 0.22
            noise_tex = rng.normal(0, 45.0, (h, w))
            base_r[obs_mask] = np.clip(35.0 + noise_tex[obs_mask], 0, 255)
            base_g[obs_mask] = np.clip(30.0 + noise_tex[obs_mask], 0, 255)
            base_b[obs_mask] = np.clip(25.0 + noise_tex[obs_mask], 0, 255)

        frame = np.stack([base_r, base_g, base_b], axis=-1).astype(np.uint8)

        meta = {
            "camera_model": (
                "MARS09_MastCam_Simulated"
                if self.environment in (EnvironmentProfile.MARS, EnvironmentProfile.SIMULATION_MARS)
                else "Generic_MastCam_Simulated"
            ),
            "frame_index": self._frame_count,
            "simulated": True,
            "environment": self.environment.value,
            "fov_deg": 65.0,
            "exposure_ms": 16.6,
            "obstacle_injected": self.inject_obstacle,
            "terrain_mode": self.terrain_mode,
        }
        return frame, meta


class CameraFrameSource:
    """
    Adapter responsible for querying active live or simulated camera streams
    and constructing ephemeral UnifiedImage instances.

    Frames remain in-memory by default to protect disk space and ensure high throughput.
    """

    def __init__(
        self,
        stream: Optional[BaseCameraStream] = None,
        environment: EnvironmentProfile = EnvironmentProfile.MARS,
        config: Optional[VisionConfig] = None,
    ):
        self.config = config or VisionConfig()
        self.environment = environment
        self.stream = stream or SimulatedCameraFeed(environment=environment)

    def capture(self, environment_override: Optional[EnvironmentProfile] = None) -> UnifiedImage:
        """
        Polls the camera source for the latest frame, validates resolution,
        and constructs a standardized UnifiedImage.
        """
        if not self.stream.is_available():
            raise CameraUnavailableError(
                "Camera feed is unavailable. Hardware device may be disconnected, busy, or uninitialized."
            )

        try:
            raw_frame, stream_meta = self.stream.capture_frame()
        except CameraPermissionError:
            raise
        except CameraUnavailableError:
            raise
        except Exception as e:
            raise CameraUnavailableError(f"Failed to capture frame from camera stream: {e}") from e

        if raw_frame is None or raw_frame.size == 0:
            raise EmptyImageError("Camera driver returned an empty or uninitialized frame.")

        pil_img = Image.fromarray(raw_frame)
        arr, _ = _normalize_image_array(
            pil_img,
            max_dimension=self.config.max_input_dimension,
            min_dimension=self.config.min_input_dimension,
        )

        active_env = environment_override or self.environment
        img_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        meta = ImageMetadata(
            image_id=img_id,
            timestamp_utc=now_utc,
            source_type="camera_frame",
            environment=active_env,
            width=arr.shape[1],
            height=arr.shape[0],
            channels=arr.shape[2] if arr.ndim == 3 else 1,
            original_format="RAW_STREAM_FRAME",
            file_size_bytes=arr.nbytes,
            camera_model=stream_meta.get("camera_model", "Generic_Rover_Camera"),
            extra={"stream_metadata": stream_meta, "ephemeral": True},
        )

        return UnifiedImage(
            image_id=img_id,
            image=arr,
            source="camera_frame",
            environment=active_env,
            timestamp=now_utc,
            metadata=meta.to_dict(),
        )

    def capture_and_detect(
        self,
        detector: Optional[Any] = None,
        environment_override: Optional[EnvironmentProfile] = None,
    ) -> Tuple[UnifiedImage, Optional[Any]]:
        """
        Captures a frame and evaluates it against the ObstacleEventDetector.
        Returns (UnifiedImage, Optional[ObstacleAlert]).
        """
        frame = self.capture(environment_override=environment_override)
        if detector is None:
            from visionscore.obstacle_detector import get_obstacle_detector
            detector = get_obstacle_detector()

        alert = detector.process_frame(frame)
        return frame, alert


class ImageInputHandler:
    """
    Unified high-level facade providing top-level ingestion for both
    ImageUploadSource and CameraFrameSource adapters.
    """

    def __init__(
        self,
        config: Optional[VisionConfig] = None,
        camera_stream: Optional[BaseCameraStream] = None,
    ):
        self.config = config or VisionConfig()
        self.upload_source = ImageUploadSource(self.config)
        self.camera_source = CameraFrameSource(stream=camera_stream, config=self.config)

    def load_from_path(
        self,
        file_path: Union[str, Path],
        environment: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Loads an image from a filesystem path."""
        return self.upload_source.load_from_path(file_path, environment=environment)

    def load_from_bytes(
        self,
        data: bytes,
        filename: Optional[str] = None,
        environment: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Loads an image from raw bytes."""
        return self.upload_source.load_from_bytes(data, filename=filename, environment=environment)

    def load_from_array(
        self,
        array: np.ndarray,
        environment: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Loads an image from a NumPy array."""
        return self.upload_source.load_from_array(array, environment=environment)

    def capture_frame(
        self,
        environment_override: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Captures a frame from the configured camera stream."""
        return self.camera_source.capture(environment_override=environment_override)

    def ingest(
        self,
        source: Union[UnifiedImage, np.ndarray, bytes, str, Path],
        environment: Optional[EnvironmentProfile] = None,
    ) -> UnifiedImage:
        """Universal polymorphic ingestion entrypoint for any supported image input format."""
        if isinstance(source, UnifiedImage):
            return source
        elif isinstance(source, np.ndarray):
            return self.load_from_array(source, environment=environment)
        elif isinstance(source, bytes):
            return self.load_from_bytes(source, environment=environment)
        elif isinstance(source, (str, Path)):
            return self.load_from_path(source, environment=environment)
        else:
            raise InvalidImageError(f"Unsupported image input type: {type(source).__name__}")

    def ingest_and_detect(
        self,
        source: Union[UnifiedImage, np.ndarray, bytes, str, Path],
        detector: Optional[Any] = None,
        environment: Optional[EnvironmentProfile] = None,
    ) -> Tuple[UnifiedImage, Optional[Any]]:
        """Polymorphic ingestion with automatic obstacle detection evaluation."""
        image = self.ingest(source, environment=environment)
        if detector is None:
            from visionscore.obstacle_detector import get_obstacle_detector
            detector = get_obstacle_detector()

        alert = detector.process_frame(image)
        return image, alert

