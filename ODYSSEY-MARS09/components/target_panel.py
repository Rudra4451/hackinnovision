"""UI Component: Science Target Registry."""
from typing import List, Dict, Any


def render_target_panel(ranked_targets: List[Dict[str, Any]]):
    import streamlit as st
    st.subheader("Prioritized Science Targets")
    if ranked_targets:
        try:
            import pandas as pd
            df = pd.DataFrame(ranked_targets)
            st.dataframe(df, use_container_width=True)
        except ImportError:
            st.write(ranked_targets)
    else:
        st.info("No active science targets registered.")
