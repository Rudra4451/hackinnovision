"""
Mars Terrain Neural Model Package.
"""

from visionscore.models.mars_net import (
    CLASS_NAMES,
    IGNORE_INDEX,
    NUM_CLASSES,
    MarsTerrainCNN,
    ModelCheckpoint,
)

__all__ = [
    "MarsTerrainCNN",
    "ModelCheckpoint",
    "NUM_CLASSES",
    "CLASS_NAMES",
    "IGNORE_INDEX",
]

