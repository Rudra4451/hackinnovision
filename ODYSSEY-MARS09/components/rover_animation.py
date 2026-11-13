"""UI Component: Rover Step-by-Step Traversal Animator."""
import time
from typing import List, Tuple


def animate_traversal(path: List[Tuple[int, int]], speed: float = 0.05):
    import streamlit as st
    placeholder = st.empty()
    for idx, step in enumerate(path):
        placeholder.markdown(f"**Rover moving...** Step `{idx + 1}/{len(path)}` at coordinate `{step}`")
        time.sleep(speed)
    placeholder.success("Traversal Completed.")
