from __future__ import annotations

from agent.memory.episodic import EpisodicMemory
from agent.state import AgentState


def build_working_memory(state: AgentState, episodic: EpisodicMemory) -> dict:
    return {
        "model_id": state.current_trace.model_id,
        "device": state.current_trace.device,
        "current_total_latency_ms": state.current_trace.total_latency_ms,
        "baseline_total_latency_ms": state.baseline_trace.total_latency_ms,
        "current_improvement_pct": round(state.current_improvement_pct, 2),
        "ranked_nodes": [node.model_dump() for node in state.ranked_nodes[:3]],
        "recent_cycles": [record.model_dump() for record in state.history[-3:]],
    }
