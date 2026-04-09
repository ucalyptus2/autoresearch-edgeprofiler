from __future__ import annotations

import json
from pathlib import Path

from agent.memory.episodic import EpisodicMemory
from agent.memory.semantic import SemanticMemory
from agent.memory.working import build_working_memory
from agent.nodes.evaluate import score_cycle
from agent.nodes.generate import generate_patch
from agent.nodes.hypothesize import build_hypothesis
from agent.nodes.observe import rank_bottlenecks
from agent.nodes.reflect import promote_pattern
from agent.reporting import render_markdown_report
from agent.state import AgentConfig, AgentState, CycleRecord
from harness.parser.schemas import NodeGraph
from harness.parser.trace_parser import parse_trace
from harness.tools.compile import ToolRunner
from harness.tools.diff import diff_traces


class ProfilerCopilot:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.episodic = EpisodicMemory(config.run_dir / "episodic.sqlite3")
        self.semantic = SemanticMemory(config.repo_root / "knowledge_base" / "patterns")
        self.tool_runner = ToolRunner(config.run_dir)

    def _init_state(self) -> AgentState:
        graph = parse_trace(self.config.trace_path)
        return AgentState(
            config=self.config,
            current_trace=graph,
            baseline_trace=NodeGraph.model_validate_json(graph.model_dump_json()),
        )

    def run(self) -> AgentState:
        state = self._init_state()

        while state.cycle < self.config.max_cycles:
            state.ranked_nodes = rank_bottlenecks(state.current_trace, self.config.top_k)
            if not state.ranked_nodes:
                state.stop_reason = "no_nodes"
                break

            node = self._select_candidate(state)
            if node is None:
                state.stop_reason = "no_actionable_nodes"
                break

            state.cycle += 1
            state.node_attempts[node.id] = state.node_attempts.get(node.id, 0) + 1
            kb_matches = self.semantic.search(node=node, device=state.current_trace.device, limit=1)
            kb_match = kb_matches[0] if kb_matches else None
            state.active_hypothesis = build_hypothesis(state.cycle, node=node, match=kb_match)
            state.active_patch = generate_patch(
                hypothesis=state.active_hypothesis,
                node=node,
                pattern=kb_match.pattern if kb_match else None,
            )

            patch_result = self.tool_runner.apply_patch(state.active_patch)
            compile_result = self.tool_runner.compile(
                model_path=patch_result["patched_file_path"],
                device=state.current_trace.device,
            )
            profile_result = self.tool_runner.profile(
                binary_path=compile_result["binary_path"],
                device=state.current_trace.device,
                trace=state.current_trace,
                target_node=node.id,
                expected_reduction_pct=(
                    kb_match.pattern["validation"].get("expected_latency_reduction_pct", 20)
                    if kb_match
                    else 12
                ),
            )

            new_trace = parse_trace(Path(profile_result["trace_path"]))
            state.last_diff = diff_traces(
                before=state.current_trace,
                after=new_trace,
                target_node=node.id,
            )
            cycle_score = score_cycle(state.last_diff, state.active_hypothesis)
            record = CycleRecord(
                cycle=state.cycle,
                target_node=node.id,
                hypothesis=state.active_hypothesis,
                patch=state.active_patch,
                diff=state.last_diff,
                score=cycle_score,
            )
            promoted = promote_pattern(state, record, self.config.runtime_dir / "review_queue")
            record.promoted_pattern_path = str(promoted) if promoted else None
            self.episodic.append(record)
            state.history.append(record)
            state.current_trace = new_trace
            self._update_node_status(state, node_id=node.id, kb_match=kb_match is not None)

            self._write_summary(state)

            if state.current_improvement_pct >= self.config.target_improvement_pct:
                state.stop_reason = "target_reached"
                break
            if state.last_diff.verdict == "NEUTRAL" and not kb_match:
                state.stop_reason = "stuck"
                break

        if state.stop_reason is None:
            state.stop_reason = "max_cycles"
        self._write_summary(state)
        return state

    def _write_summary(self, state: AgentState) -> None:
        payload = {
            "run_id": state.config.run_id,
            "working_memory": build_working_memory(state, self.episodic),
            "stop_reason": state.stop_reason,
            "node_attempts": state.node_attempts,
            "completed_nodes": state.completed_nodes,
            "escalated_nodes": state.escalated_nodes,
            "history": [record.model_dump() for record in state.history],
        }
        run_summary_path = self.config.run_dir / "summary.json"
        run_summary_path.write_text(json.dumps(payload, indent=2))
        latest_summary_path = self.config.runtime_dir / "last_run_summary.json"
        latest_summary_path.write_text(json.dumps(payload, indent=2))
        report_path = self.config.run_dir / "optimization_report.md"
        report_path.write_text(render_markdown_report(state))
        latest_report_path = self.config.runtime_dir / "last_optimization_report.md"
        latest_report_path.write_text(render_markdown_report(state))

    def _select_candidate(self, state: AgentState):
        for node in state.ranked_nodes:
            if node.id in state.completed_nodes or node.id in state.escalated_nodes:
                continue
            attempts = state.node_attempts.get(node.id, 0)
            if attempts >= self.config.max_attempts_per_node:
                state.escalated_nodes.append(node.id)
                continue
            return node
        return None

    def _update_node_status(self, state: AgentState, node_id: str, kb_match: bool) -> None:
        if state.last_diff is None:
            return
        if state.last_diff.verdict == "IMPROVED":
            if node_id not in state.completed_nodes:
                state.completed_nodes.append(node_id)
            return
        if state.node_attempts.get(node_id, 0) >= self.config.max_attempts_per_node or not kb_match:
            if node_id not in state.escalated_nodes:
                state.escalated_nodes.append(node_id)
