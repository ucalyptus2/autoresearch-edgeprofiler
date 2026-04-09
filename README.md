# autoresearch-edgeprofiler

Runnable scaffold for the profiler copilot in `PLAN.md`.

Current scope:
- Pydantic trace schema and parser
- YAML pattern KB with heuristic retrieval
- SQLite episodic memory
- Stub compile/profile/apply harness
- Closed-loop optimization runner with scoring and reflection
- Per-run artifact directories and markdown optimization reports

Run:

```bash
python3 /mnt/data/autoresearch-edgeprofiler/run.py
```

Artifacts land in `runtime/`.

Each execution now creates `runtime/runs/<run_id>/` with:
- `summary.json`
- `optimization_report.md`
- patch/profile artifacts
- run-local SQLite episodic memory
