from __future__ import annotations

from pathlib import Path

from agent.state import CodePatch
from harness.parser.schemas import NodeGraph


class ToolRunner:
    def __init__(self, runtime_dir: Path) -> None:
        self.runtime_dir = runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._patch_counter = 0

    def apply_patch(self, patch: CodePatch) -> dict:
        self._patch_counter += 1
        path = self.runtime_dir / f"cycle_{self._patch_counter:02d}_{patch.target_file}.patch"
        path.write_text(patch.diff_text)
        return {"patched_file_path": str(path), "success": True}

    def compile(self, model_path: str, device: str) -> dict:
        binary_path = self.runtime_dir / f"compiled_{device}.bin"
        binary_path.write_text(f"compiled from {model_path} for {device}\n")
        return {"binary_path": str(binary_path), "compile_log": "stub compile ok", "success": True}

    def profile(
        self,
        binary_path: str,
        device: str,
        trace: NodeGraph,
        target_node: str,
        expected_reduction_pct: float,
    ) -> dict:
        reduced_nodes = []
        total_delta = 0.0
        reduction = max(0.0, min(expected_reduction_pct, 85.0)) / 100.0
        for node in trace.nodes:
            updated = node.model_copy(deep=True)
            if node.id == target_node:
                new_latency = round(node.latency_ms * (1.0 - reduction), 4)
                total_delta += node.latency_ms - new_latency
                updated.latency_ms = new_latency
                if "high_latency_outlier" in updated.flags and new_latency < node.latency_ms:
                    updated.flags = [flag for flag in updated.flags if flag != "high_latency_outlier"]
            reduced_nodes.append(updated)
        reduced_nodes.sort(key=lambda item: item.latency_ms, reverse=True)
        for rank, node in enumerate(reduced_nodes, start=1):
            node.latency_rank = rank

        new_trace = trace.model_copy(deep=True)
        new_trace.device = device
        new_trace.nodes = reduced_nodes
        new_trace.total_latency_ms = round(trace.total_latency_ms - total_delta, 4)

        trace_path = self.runtime_dir / f"profile_cycle_{target_node}.json"
        trace_path.write_text(new_trace.model_dump_json(indent=2))
        return {"trace_path": str(trace_path), "raw_metrics": {"binary_path": binary_path}}
