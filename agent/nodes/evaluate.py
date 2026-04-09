from __future__ import annotations

from agent.state import Hypothesis, TraceDiff


def score_cycle(diff: TraceDiff, hypothesis: Hypothesis) -> float:
    node_improvement = max(0.0, diff.target_node_delta_pct / 100.0)
    regression_penalty = 0.3 * len(diff.regression_nodes)
    total_improvement = max(0.0, diff.total_latency_delta_pct / 100.0) * 0.5
    calibration = 1.0 if (hypothesis.confidence > 0.6 and node_improvement > 0.3) else 0.8
    return round((node_improvement + total_improvement - regression_penalty) * calibration, 4)
