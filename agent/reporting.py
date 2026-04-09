from __future__ import annotations

from agent.state import AgentState


def render_markdown_report(state: AgentState) -> str:
    lines = [
        f"# Optimization Report: {state.config.run_id}",
        "",
        f"- Model: `{state.current_trace.model_id}`",
        f"- Device: `{state.current_trace.device}`",
        f"- Stop reason: `{state.stop_reason}`",
        f"- Baseline latency: `{state.baseline_trace.total_latency_ms:.4f} ms`",
        f"- Final latency: `{state.current_trace.total_latency_ms:.4f} ms`",
        f"- Improvement: `{state.current_improvement_pct:.2f}%`",
        "",
        "## Cycle Log",
        "",
        "| Cycle | Node | Pattern | Verdict | Node Delta % | Total Delta % | Score |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for record in state.history:
        lines.append(
            "| {cycle} | {node} | {pattern} | {verdict} | {node_delta:.2f} | {total_delta:.2f} | {score:.4f} |".format(
                cycle=record.cycle,
                node=record.target_node,
                pattern=record.hypothesis.kb_pattern_id or "novel",
                verdict=record.diff.verdict,
                node_delta=record.diff.target_node_delta_pct,
                total_delta=record.diff.total_latency_delta_pct,
                score=record.score,
            )
        )
    lines.extend(
        [
            "",
            "## Node Status",
            "",
            f"- Completed nodes: {', '.join(state.completed_nodes) if state.completed_nodes else 'None'}",
            f"- Escalated nodes: {', '.join(state.escalated_nodes) if state.escalated_nodes else 'None'}",
            "",
            "## Next Actions",
            "",
        ]
    )
    if state.current_improvement_pct < state.config.target_improvement_pct:
        lines.append(
            "- Connect the stub harness to the real compile/profile commands so improvement scores reflect device reality."
        )
        lines.append("- Seed more validated KB patterns before increasing autonomous loop depth.")
    else:
        lines.append("- Promote validated patterns and re-run on a fresh trace to confirm repeatability.")
    return "\n".join(lines) + "\n"
