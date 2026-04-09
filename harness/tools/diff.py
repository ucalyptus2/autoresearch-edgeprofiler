from __future__ import annotations

from agent.state import TraceDiff
from harness.parser.schemas import NodeGraph


def diff_traces(before: NodeGraph, after: NodeGraph, target_node: str) -> TraceDiff:
    before_nodes = {node.id: node for node in before.nodes}
    after_nodes = {node.id: node for node in after.nodes}
    before_target = before_nodes[target_node]
    after_target = after_nodes[target_node]

    target_node_delta_ms = before_target.latency_ms - after_target.latency_ms
    target_node_delta_pct = (
        (target_node_delta_ms / before_target.latency_ms) * 100.0 if before_target.latency_ms else 0.0
    )
    total_latency_delta_ms = before.total_latency_ms - after.total_latency_ms
    total_latency_delta_pct = (
        (total_latency_delta_ms / before.total_latency_ms) * 100.0 if before.total_latency_ms else 0.0
    )

    regression_nodes = []
    for node_id, after_node in after_nodes.items():
        before_node = before_nodes[node_id]
        if after_node.latency_ms > before_node.latency_ms:
            regression_nodes.append(node_id)

    verdict = "NEUTRAL"
    if target_node_delta_ms > 0 and total_latency_delta_ms >= 0:
        verdict = "IMPROVED"
    elif target_node_delta_ms < 0 or total_latency_delta_ms < 0:
        verdict = "REGRESSED"

    new_bottleneck = max(after.nodes, key=lambda node: node.latency_ms).id if after.nodes else target_node
    return TraceDiff(
        target_node=target_node,
        target_node_delta_ms=round(target_node_delta_ms, 4),
        target_node_delta_pct=round(target_node_delta_pct, 2),
        total_latency_delta_ms=round(total_latency_delta_ms, 4),
        total_latency_delta_pct=round(total_latency_delta_pct, 2),
        new_bottleneck=new_bottleneck,
        regression_nodes=regression_nodes,
        verdict=verdict,
    )
