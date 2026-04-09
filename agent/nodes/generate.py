from __future__ import annotations

from agent.state import CodePatch, Hypothesis
from harness.parser.schemas import NodeProfile


def generate_patch(hypothesis: Hypothesis, node: NodeProfile, pattern: dict | None) -> CodePatch:
    if pattern:
        template = pattern["fix"].get("code_template", "").strip()
        summary = pattern["fix"]["description"]
    else:
        template = (
            "# TODO: replace the slow op with a hardware-native equivalent\n"
            f"# Target node: {node.id}\n"
            f"# Observed op: {node.op_type}\n"
        )
        summary = hypothesis.proposed_fix

    diff_text = "\n".join(
        [
            "--- a/model.py",
            "+++ b/model.py",
            "@@",
            f"# Hypothesis: {hypothesis.id}",
            f"# Proposed fix: {summary}",
            template or "# No template available yet.",
        ]
    )
    return CodePatch(
        target_file="model.py",
        patch_summary=summary,
        diff_text=diff_text,
        template_values={"target_node": node.id, "op_type": node.op_type},
    )
