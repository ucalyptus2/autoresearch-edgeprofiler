from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from harness.parser.schemas import NodeGraph, NodeProfile


class Hypothesis(BaseModel):
    id: str
    cycle: int
    target_node: str
    observed_symptom: str
    root_cause_category: Literal[
        "unsupported_op",
        "redundant_compute",
        "memory_bw",
        "quant_mismatch",
        "threading",
        "unknown",
    ]
    proposed_fix: str
    expected_outcome: str
    confidence: float = Field(ge=0.0, le=1.0)
    kb_pattern_id: str | None = None
    fallback: str | None = None
    novel: bool = False


class CodePatch(BaseModel):
    target_file: str
    patch_summary: str
    diff_text: str
    template_values: dict[str, object] = Field(default_factory=dict)


class TraceDiff(BaseModel):
    target_node: str
    target_node_delta_ms: float
    target_node_delta_pct: float
    total_latency_delta_ms: float
    total_latency_delta_pct: float
    new_bottleneck: str
    regression_nodes: list[str] = Field(default_factory=list)
    verdict: Literal["IMPROVED", "REGRESSED", "NEUTRAL"]


class CycleRecord(BaseModel):
    cycle: int
    target_node: str
    hypothesis: Hypothesis
    patch: CodePatch
    diff: TraceDiff
    score: float
    promoted_pattern_path: str | None = None


class AgentConfig(BaseModel):
    model_id: str
    device: str
    trace_path: Path
    target_improvement_pct: float = 20.0
    max_cycles: int = 5
    top_k: int = 3
    max_attempts_per_node: int = 2
    runtime_dir: Path
    run_id: str
    run_dir: Path
    repo_root: Path


class AgentState(BaseModel):
    config: AgentConfig
    current_trace: NodeGraph
    baseline_trace: NodeGraph
    ranked_nodes: list[NodeProfile] = Field(default_factory=list)
    cycle: int = 0
    history: list[CycleRecord] = Field(default_factory=list)
    active_hypothesis: Hypothesis | None = None
    active_patch: CodePatch | None = None
    last_diff: TraceDiff | None = None
    stop_reason: str | None = None
    node_attempts: dict[str, int] = Field(default_factory=dict)
    completed_nodes: list[str] = Field(default_factory=list)
    escalated_nodes: list[str] = Field(default_factory=list)

    @property
    def current_improvement_pct(self) -> float:
        baseline = self.baseline_trace.total_latency_ms
        current = self.current_trace.total_latency_ms
        if baseline <= 0:
            return 0.0
        return ((baseline - current) / baseline) * 100.0
