from __future__ import annotations

from agent.memory.semantic import PatternMatch
from agent.state import Hypothesis
from harness.parser.schemas import NodeProfile


def build_hypothesis(
    cycle: int,
    node: NodeProfile,
    match: PatternMatch | None,
) -> Hypothesis:
    observed = (
        f"latency {node.latency_ms:.2f}ms, rank {node.latency_rank}, "
        f"threads {node.threads_used}/{node.threads_available}, flags={','.join(node.flags)}"
    )
    if match is not None:
        fix = match.pattern["fix"]["description"]
        expected_pct = match.pattern["validation"].get("expected_latency_reduction_pct", 35)
        confidence = min(0.95, 0.45 + (match.score * 0.08))
        return Hypothesis(
            id=f"hyp_{cycle:03d}",
            cycle=cycle,
            target_node=node.id,
            observed_symptom=observed,
            root_cause_category="unsupported_op" if "unsupported" in match.pattern.get("root_cause", "").lower() else "threading",
            proposed_fix=fix,
            expected_outcome=f"Reduce {node.id} latency by about {expected_pct}%",
            confidence=round(confidence, 2),
            kb_pattern_id=match.pattern["id"],
            fallback=f"hyp_{cycle + 1:03d}",
            novel=False,
        )

    return Hypothesis(
        id=f"hyp_{cycle:03d}",
        cycle=cycle,
        target_node=node.id,
        observed_symptom=observed,
        root_cause_category="unknown",
        proposed_fix=f"Investigate a fused replacement or rewrite for {node.op_type}",
        expected_outcome=f"Reduce {node.id} latency by 15-25%",
        confidence=0.35,
        kb_pattern_id=None,
        fallback=f"hyp_{cycle + 1:03d}",
        novel=True,
    )
