from __future__ import annotations

from harness.parser.schemas import NodeGraph


def rank_bottlenecks(graph: NodeGraph, top_k: int) -> list:
    ranked = sorted(graph.nodes, key=lambda node: node.latency_ms, reverse=True)
    return ranked[:top_k]
