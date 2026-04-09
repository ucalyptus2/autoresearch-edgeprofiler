from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from harness.parser.schemas import NodeProfile


@dataclass
class PatternMatch:
    score: float
    pattern: dict
    path: Path


class SemanticMemory:
    def __init__(self, pattern_dir: Path) -> None:
        self.pattern_dir = pattern_dir

    def search(self, node: NodeProfile, device: str, limit: int = 3) -> list[PatternMatch]:
        matches: list[PatternMatch] = []
        for path in sorted(self.pattern_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text())
            score = self._score_pattern(node=node, device=device, pattern=data)
            if score > 0:
                matches.append(PatternMatch(score=score, pattern=data, path=path))
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]

    def _score_pattern(self, node: NodeProfile, device: str, pattern: dict) -> float:
        trigger = pattern.get("trigger", {})
        score = 0.0
        op_match = trigger.get("op_type") == node.op_type
        if trigger.get("op_type") == node.op_type:
            score += 3.0
        node_flags = set(node.flags)
        pattern_flags = set(trigger.get("symptoms", []))
        symptom_overlap = len(node_flags & pattern_flags)
        score += symptom_overlap * 1.5
        for device_glob in trigger.get("devices", []):
            if device_glob.endswith("*") and device.startswith(device_glob[:-1]):
                score += 1.0
            elif device_glob == device:
                score += 1.0
        if not op_match and symptom_overlap == 0:
            return 0.0
        return score
