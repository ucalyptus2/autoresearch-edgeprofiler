from __future__ import annotations

import csv
import json
from pathlib import Path

from harness.parser.schemas import NodeGraph, NodeProfile


def parse_trace(path: Path) -> NodeGraph:
    if path.suffix.lower() == ".json":
        return NodeGraph.model_validate(json.loads(path.read_text()))
    if path.suffix.lower() == ".csv":
        return _parse_csv(path)
    raise ValueError(f"Unsupported trace format: {path}")


def _parse_csv(path: Path) -> NodeGraph:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    nodes = []
    for index, row in enumerate(rows, start=1):
        nodes.append(
            NodeProfile(
                id=row["id"],
                op_type=row["op_type"],
                latency_ms=float(row["latency_ms"]),
                latency_rank=index,
                threads_used=int(row.get("threads_used", 1)),
                threads_available=int(row.get("threads_available", 1)),
                flags=[flag for flag in row.get("flags", "").split("|") if flag],
            )
        )
    total_latency_ms = sum(node.latency_ms for node in nodes)
    return NodeGraph(
        model_id=path.stem,
        device="unknown_device",
        total_latency_ms=total_latency_ms,
        nodes=nodes,
    )
