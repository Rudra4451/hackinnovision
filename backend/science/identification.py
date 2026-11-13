"""
Target Identification Module for MARS-09 Odyssey Science Intelligence Engine.

Classifies geological planetary targets using simulated multi-band spectral data,
morphological attributes, and astrobiological significance.
"""

from typing import Any, Dict, List, Tuple


GEOLOGICAL_CLASSES = {
    "HYDRATED_CLAYS": {
        "name": "Hydrated Phyllosilicates (Smectite/Nontronite)",
        "astrobiology_rating": 95.0,
        "spectral_marker": "2.2_um_absorption",
        "description": "Indicates ancient standing neutral pH water; prime candidate for biosignature preservation.",
    },
    "MARGINAL_CARBONATES": {
        "name": "Marginal Lacustrine Carbonates",
        "astrobiology_rating": 92.0,
        "spectral_marker": "2.3_um_co3_band",
        "description": "Precipitated along paleolake shoreline; high microfossil and organic preservation capability.",
    },
    "HYDROTHERMAL_SILICA": {
        "name": "Hydrated Opalline Silica Deposits",
        "astrobiology_rating": 88.0,
        "spectral_marker": "1.4_um_1.9_um_doublet",
        "description": "Analog to terrestrial hot springs; exceptional preservation of microbial textures.",
    },
    "SULFATE_EVAPORITES": {
        "name": "Magnesium/Iron Sulfate Evaporites",
        "astrobiology_rating": 72.0,
        "spectral_marker": "2.4_um_so4_absorption",
        "description": "Marks late-stage drying and evaporation of Martian lakes under acidic conditions.",
    },
    "IMPACT_MELT_BRECCIA": {
        "name": "Crater Impact Melt & Polymict Breccia",
        "astrobiology_rating": 55.0,
        "spectral_marker": "shock_glass_luminescence",
        "description": "Exhumed deep Noachian basement material; vital for planetary geochronology and crater dating.",
    },
    "BASALTIC_BEDROCK": {
        "name": "Olivine-Pyroxene Basaltic Lava Outcrop",
        "astrobiology_rating": 40.0,
        "spectral_marker": "1.0_um_fe_silicate_peak",
        "description": "Primary igneous crust; establishes baseline magma composition and magnetic field history.",
    },
    "AEOLIAN_DUNE_FIELD": {
        "name": "Active Basaltic Sand Ripple / Dune",
        "astrobiology_rating": 25.0,
        "spectral_marker": "low_albedo_uniform",
        "description": "Modern atmospheric-surface interaction study, but low paleobiology preservation.",
    },
}


def calculate_scientific_value(
    target_type: str,
    spectral_signature: Dict[str, float],
    rarity_factor: float = 1.0,
) -> float:
    """
    Compute intrinsic Scientific Value (0.0 to 100.0) based on astrobiological merit,
    spectral signal clarity, and geological rarity.
    
    This is independent of operational safety and distance (Rule 2).
    """
    category = GEOLOGICAL_CLASSES.get(target_type)
    if not category:
        base_merit = 50.0
    else:
        base_merit = category["astrobiology_rating"]

    # Spectral purity score: peak-to-noise ratio in key bands
    signal_strength = spectral_signature.get("signal_to_noise", 1.0)
    hydration_index = spectral_signature.get("hydration_index", 0.5)
    mineral_diversity = spectral_signature.get("mineral_diversity", 0.5)

    spectral_bonus = (hydration_index * 15.0) + (mineral_diversity * 10.0)
    clarity_multiplier = min(1.2, max(0.7, signal_strength / 10.0))

    raw_value = (base_merit + spectral_bonus) * clarity_multiplier * rarity_factor
    return round(float(min(100.0, max(5.0, raw_value))), 2)
