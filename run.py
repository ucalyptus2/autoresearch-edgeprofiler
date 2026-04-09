from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

import yaml

from agent.graph import ProfilerCopilot
from agent.state import AgentConfig


def load_config(repo_root: Path) -> AgentConfig:
    raw = yaml.safe_load((repo_root / "config.yaml").read_text())
    runtime_dir = repo_root / "runtime"
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runtime_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return AgentConfig(
        model_id=raw["model_id"],
        device=raw["device"],
        trace_path=repo_root / raw["trace_path"],
        target_improvement_pct=raw.get("target_improvement_pct", 20),
        max_cycles=raw.get("max_cycles", 5),
        top_k=raw.get("top_k", 3),
        max_attempts_per_node=raw.get("max_attempts_per_node", 2),
        runtime_dir=runtime_dir,
        run_id=run_id,
        run_dir=run_dir,
        repo_root=repo_root,
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    config = load_config(repo_root)
    copilot = ProfilerCopilot(config)
    state = copilot.run()
    summary = {
        "run_id": state.config.run_id,
        "stop_reason": state.stop_reason,
        "cycles": len(state.history),
        "baseline_latency_ms": state.baseline_trace.total_latency_ms,
        "final_latency_ms": state.current_trace.total_latency_ms,
        "improvement_pct": round(state.current_improvement_pct, 2),
        "history": [
            {
                "cycle": record.cycle,
                "target_node": record.target_node,
                "pattern": record.hypothesis.kb_pattern_id,
                "verdict": record.diff.verdict,
                "target_delta_pct": record.diff.target_node_delta_pct,
                "total_delta_pct": record.diff.total_latency_delta_pct,
                "score": record.score,
            }
            for record in state.history
        ],
        "completed_nodes": state.completed_nodes,
        "escalated_nodes": state.escalated_nodes,
        "run_dir": str(state.config.run_dir),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
