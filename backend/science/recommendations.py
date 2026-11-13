"""
Evidence-Based Recommendations Module for MARS-09 Odyssey Science Intelligence Engine.

Generates structured mission reports and markdown briefs summarizing science targets,
operational safety trade-offs, and tactical navigation guidance.
"""

from typing import Any, Dict, List, Optional


def generate_mission_recommendation_report(
    evaluated_targets: List[Dict[str, Any]],
    rover_pos: tuple = (2, 2),
    sol: int = 142,
) -> str:
    """
    Synthesize a comprehensive, planetary-science grade Markdown mission briefing.
    """
    accessible = [t for t in evaluated_targets if t["operational_priority"] > 0]
    gated = [t for t in evaluated_targets if t["operational_priority"] == 0]

    lines = [
        f"# MARS-09 ODYSSEY: TACTICAL RECONNAISSANCE REPORT",
        f"**Sol:** {sol} | **Chassis Position:** ({rover_pos[0]}, {rover_pos[1]}) | **Status:** FLIGHT CONTROLLER ACTIVE",
        "",
        "## 1. EXECUTIVE TARGET RECOMMENDATION",
    ]

    if accessible:
        top = accessible[0]
        lines.extend([
            f"**PRIMARY TARGET:** `{top['name']}` (ID: {top['id']})",
            f"- **Classification:** {top['target_type']}",
            f"- **Scientific Value:** {top['scientific_value']:.1f} / 100",
            f"- **Operational Priority:** {top['operational_priority']:.1f} / 100 (Highest Safe Return)",
            f"- **Estimated Traverse Distance:** {top['estimated_distance']:.1f} meters",
            f"- **Estimated Energy Cost:** {top['estimated_energy_cost']:.1f} cost units",
            f"- **Confidence:** {top['confidence_level']*100:.1f}% (Uncertainty: {top['uncertainty_score']:.2f})",
            "",
            f"> **Tactical Assessment:** {top['justification']}",
            "",
        ])
    else:
        lines.extend([
            "**WARNING:** No candidate targets are currently accessible from the current position without entering impassable hazards.",
            "",
        ])

    lines.append("## 2. RECONNAISSANCE TARGET MATRIX")
    lines.append("| Target ID | Name | Type | Sci Value | Op Priority | Status | Distance | Confidence |")
    lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |")

    for t in evaluated_targets:
        status_badge = (
            "✅ OPTIMAL" if t["accessibility_status"] == "OPTIMAL"
            else ("⚠️ CAUTION" if t["accessibility_status"] == "CAUTION" else "🚫 GATED/HAZARD")
        )
        lines.append(
            f"| `{t['id']}` | {t['name']} | {t['target_type'][:18]} | "
            f"{t['scientific_value']:.1f} | **{t['operational_priority']:.1f}** | "
            f"{status_badge} | {t['estimated_distance']:.1f}m | {t['confidence_level']*100:.0f}% |"
        )

    if gated:
        lines.extend([
            "",
            "## 3. HARD SAFETY GATE AUDIT (RULE 2 ENFORCEMENT)",
            "The following targets were rejected by the operational safety gate and assigned Priority 0.0:",
        ])
        for g in gated:
            lines.append(f"- **{g['name']}** (`{g['id']}`): {g['justification']}")

    lines.extend([
        "",
        "## 4. NAVIGATION PROTOCOL GUIDANCE",
        "- **Dual Routing Compliance:** When navigating towards the designated primary target, Mars-09 "
        "strongly advises utilizing the **Safest Route** trajectory to avoid high-slip rocky fields, "
        "even when a slight physical distance penalty is incurred.",
        "- **Chassis Integrity:** Squeeze prevention active; diagonal transitions across hazardous vertex "
        "boundaries are locked to safeguard wheel assemblies.",
    ])

    return "\n".join(lines)
