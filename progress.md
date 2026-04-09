# Progress

## Current State

- The project now has a runnable closed-loop profiler copilot scaffold.
- The loop can parse a trace, rank bottlenecks, retrieve seeded patterns, generate a patch proposal, run stub compile/profile steps, diff traces, score outcomes, and draft KB promotions.
- Runs are now isolated under `runtime/runs/<run_id>/` instead of overwriting a single shared artifact set.

## External Research Sweep

Reviewed ten relevant public repos and harness projects for architecture signals:

1. `karpathy/autoresearch`
2. `assafelovic/gpt-researcher`
3. `tarun7r/deep-research-agent`
4. `SkyworkAI/DeepResearchAgent`
5. `Alibaba-NLP/DeepResearch`
6. `VladPrytula/DeepResearchHybrid`
7. `Agent-Field/af-deep-research`
8. `HKUDS/OpenHarness`
9. `deepklarity/harness-kit`
10. `SethGammon/Citadel`

## What Mattered

- `karpathy/autoresearch`: the key pattern is a tight experiment loop with a real environment and fast evaluation, not a chat-heavy agent.
- `gpt-researcher` and `tarun7r/deep-research-agent`: useful emphasis on explicit workflow graphs, progress reporting, and checkpointable state.
- `Agent-Field/af-deep-research`: useful emphasis on concurrency limits and iterative refinement loops.
- `SkyworkAI/DeepResearchAgent`: strongest argument for explicit lifecycle/state/version boundaries rather than monolithic agent glue.
- `OpenHarness`: relevant for hook execution, tool/runtime boundaries, and CLI-driven harness structure.
- `Citadel` and `harness-kit`: useful engineering patterns around persistence, claimed scope, and cross-session compounding.

## Changes Landed From This Research

- Added per-run directories and run IDs.
- Added markdown optimization report generation.
- Stopped overwriting patch artifacts by cycle.
- Kept the project history in a tracked `progress.md` instead of burying it in runtime output.

## Next High-Value Work

- Replace stub compile/profile calls with real device commands.
- Introduce a typed action/event ledger so every cycle has an auditable action trace.
- Upgrade semantic retrieval from heuristic YAML scoring to embeddings + metadata filters.
- Add a real planner/fallback policy instead of single-pass top-node execution.
- Add rollback and patch application against a source workspace copy, not only patch text artifacts.
