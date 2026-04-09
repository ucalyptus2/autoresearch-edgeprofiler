from __future__ import annotations

from pydantic import BaseModel, Field


class NodeProfile(BaseModel):
    id: str
    op_type: str
    latency_ms: float
    latency_rank: int
    threads_used: int = 1
    threads_available: int = 1
    input_shapes: list[list[int]] = Field(default_factory=list)
    output_shapes: list[list[int]] = Field(default_factory=list)
    neighbors: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class NodeGraph(BaseModel):
    model_id: str
    device: str
    total_latency_ms: float
    nodes: list[NodeProfile]
