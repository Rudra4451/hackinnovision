"""
UI Component: Science Target Prioritization Queue
"""

from typing import List, Dict, Any


def render_target_panel(ranked_targets: List[Dict[str, Any]]):
    import streamlit as st

    st.subheader("🔬 Prioritized Geological Targets")
    if not ranked_targets:
        st.info("No active science targets registered in current ROI.")
        return

    try:
        import pandas as pd
        df = pd.DataFrame(ranked_targets)
        # Select and format display columns
        cols_to_show = [
            col for col in ["id", "type", "composite_score", "scientific_value", "distance_m", "status", "confidence"]
            if col in df.columns
        ]
        st.dataframe(
            df[cols_to_show].style.format({
                "composite_score": "{:.3f}",
                "distance_m": "{:.1f} m",
                "confidence": "{:.1%}"
            }),
            use_container_width=True
        )
    except ImportError:
        st.write(ranked_targets)
