# PLAN.md — Profiler Copilot
### An Agentic System for On-Device ML Model Optimization

**Status:** Pre-Alpha / Design  
**Authors:** Redacted  
**Date:** 2026-04-08  
**Revision:** 2 — Extended with Agent Harness + AutoResearch Loop

---

## 1. The Core Insight

The current optimization workflow is a **manual research loop**:

```
observe bottleneck → hypothesize fix → implement → re-profile → evaluate → repeat
```

This is identical in structure to what Karpathy's **AutoResearch** automates — an agent
that can form hypotheses, run experiments, observe outcomes, and iterate without human
intervention between cycles.

The profiler copilot is not just a chatbot. It is a **closed-loop optimization agent**
whose environment is the device profiler, whose actions are code transformations, and
whose reward signal is latency reduction on the target node.

---

## 2. Problem Statement

ML engineers in hardware-focused deployment teams spend the bulk of their optimization time in a
manual, knowledge-intensive loop:

1. Compile model → run on device → generate trace
2. Load trace into profiler dashboard → manually identify slow node
3. Reason about root cause using domain knowledge accumulated over years
4. Propose a fix (op substitution, quantization range change, kernel rewrite)
5. Implement patch → recompile → re-run → compare traces
6. Repeat — often 10–20 cycles per model

**Pain points:**
- Domain knowledge is tacit, not systematized
- Each cycle requires engineer-in-the-loop even for obvious fixes
- No memory across sessions — same patterns re-discovered repeatedly
- Profiler tooling is not LLM-friendly (proprietary dashboard, not CLI-native)

**Core claim:** 80% of bottleneck-fix cycles follow a small number of known patterns.
An agent that knows these patterns and can execute the cycle autonomously would
dramatically shorten the time-to-optimized-model.

---

## 3. System Overview

The system has three interlocking parts:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PROFILER COPILOT                             │
│                                                                      │
│   ┌──────────────┐    ┌──────────────────────────────────────────┐  │
│   │              │    │              AGENT CORE                  │  │
│   │   HARNESS    │───▶│  Planner → Executor → Evaluator → Mem   │  │
│   │              │◀───│                                          │  │
│   └──────────────┘    └──────────────────────────────────────────┘  │
│          │                              │                            │
│          │            ┌─────────────────▼──────────────────────┐    │
│          │            │         AUTORESEARCH LOOP               │    │
│          │            │  Hypothesis → Experiment → Score →      │    │
│          │            │  Reflect → Promote to KB → Repeat       │    │
│          │            └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Part 1 — The Agent

### 4.1 Agent Design Philosophy

The agent follows a **ReAct-style** (Reason + Act) loop, extended with persistent memory
and a structured hypothesis mechanism borrowed from AutoResearch.

Each agent cycle:

```
OBSERVE    → read trace, identify candidate nodes
THINK      → form hypothesis about root cause
PLAN       → select action from action space
ACT        → execute action (generate patch, trigger recompile, etc.)
OBSERVE    → read new trace
EVALUATE   → did the metric improve?
REFLECT    → update memory, promote pattern to KB if successful
```

### 4.2 Agent Inputs

| Input | Format | Source |
|-------|--------|--------|
| Profiler trace file | Proprietary → parsed JSON | Device toolchain |
| Model source code | Python / C++ | Engineer's repo |
| Device context | YAML config per device | Static config |
| Op pattern KB | YAML + vector index | Local ChromaDB |
| Previous session memory | JSON | Local persistent store |

### 4.3 Agent Action Space

The agent can take the following typed actions:

```python
class Action(Enum):
    INSPECT_NODE       # drill into a specific node's profile data
    RETRIEVE_PATTERN   # semantic search KB for matching patterns
    GENERATE_PATCH     # produce code diff for a proposed substitution
    APPLY_PATCH        # write patch to source file
    TRIGGER_COMPILE    # invoke build system (subprocess / shell tool)
    TRIGGER_PROFILE    # run model on device, collect new trace
    DIFF_TRACES        # compare before/after traces at node level
    PROMOTE_TO_KB      # add successful fix to knowledge base
    ESCALATE           # flag to human: "agent stuck, needs domain input"
    HALT               # optimization target reached, stop loop
```

### 4.4 Agent Memory

Three memory tiers:

```
┌─────────────────────────────────────────────┐
│  WORKING MEMORY (in-context)                │
│  Current trace, active hypothesis,          │
│  last 3 cycle results                       │
├─────────────────────────────────────────────┤
│  EPISODIC MEMORY (session store, SQLite)    │
│  Full history of this optimization run:     │
│  hypotheses tried, outcomes, dead ends      │
├─────────────────────────────────────────────┤
│  SEMANTIC MEMORY (KB, ChromaDB)             │
│  Curated op patterns, device quirks,        │
│  validated fixes across all past sessions   │
└─────────────────────────────────────────────┘
```

Working memory is rebuilt each cycle from episodic + current trace.
Successful fixes are promoted from episodic → semantic (KB) at session end.

### 4.5 Hypothesis Structure

Every agent cycle begins with a structured hypothesis — not a freeform guess:

```yaml
hypothesis:
  id: "hyp_003"
  cycle: 3
  target_node: "unfold_0"
  observed_symptom: "latency 42ms vs median 3ms; single thread; maps to gather op on NPU"
  root_cause_category: "unsupported_op"   # unsupported_op | redundant_compute |
                                           # memory_bw | quant_mismatch | threading
  proposed_fix: "replace torch.unfold with conv2d + custom 3x3 kernel (stride=patch_size)"
  expected_outcome: "latency < 5ms; multi-thread utilization"
  confidence: 0.72
  kb_pattern_id: "pat_011"   # retrieved from KB, or null if novel
  fallback: "hyp_004"        # next hypothesis if this fails
```

This structure is the key difference from a naive chatbot — it forces the agent to commit
to a falsifiable prediction before acting.

---

## 5. Part 2 — The Harness

The harness is the scaffolding that lets the agent act in the real world. Without the
harness, the agent can only talk. With it, the agent can compile, profile, and evaluate.

### 5.1 Harness Components

```
┌──────────────────────────────────────────────────────────┐
│                      AGENT HARNESS                       │
│                                                          │
│  ┌────────────────┐   ┌──────────────┐  ┌────────────┐  │
│  │  Trace Parser  │   │  Tool Runner │  │  Diff Eng  │  │
│  │                │   │              │  │            │  │
│  │ trace.bin ───▶ │   │ compile()    │  │ trace_A vs │  │
│  │ node_graph.json│   │ profile()    │  │ trace_B →  │  │
│  └────────────────┘   │ patch()      │  │ delta_json │  │
│                        └──────────────┘  └────────────┘  │
│  ┌────────────────┐   ┌──────────────┐  ┌────────────┐  │
│  │  KB Manager    │   │  Memory Mgr  │  │  Notifier  │  │
│  │                │   │              │  │            │  │
│  │ YAML ◀▶ Chroma │   │ session.json │  │ email /    │  │
│  │ embed + search │   │ + retrieval  │  │ slack hook │  │
│  └────────────────┘   └──────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Trace Parser

The most critical harness component. Must handle the proprietary trace format.

**Strategy (progressive):**

- **Step 1:** Manually export one trace to text/CSV — build a rule-based parser
- **Step 2:** If format is semi-structured, use LLM to parse → structured JSON
- **Step 3:** If format is binary, write a format reverse-engineering script

**Target output schema:**

```json
{
  "model_id": "deformable_detr_v2",
  "device": "qualcomm_soc_x",
  "total_latency_ms": 284.3,
  "nodes": [
    {
      "id": "unfold_0",
      "op_type": "Unfold",
      "latency_ms": 42.1,
      "latency_rank": 1,
      "threads_used": 1,
      "threads_available": 8,
      "input_shapes": [[1, 64, 56, 56]],
      "output_shapes": [[1, 576, 784]],
      "neighbors": ["conv_3", "reshape_1"],
      "flags": ["single_threaded", "high_latency_outlier"]
    }
  ]
}
```

### 5.3 Tool Runner

Thin Python wrappers around the existing build/profile commands:

```python
class ToolRunner:
    def compile(self, model_path: str, device: str) -> CompileResult:
        # subprocess call to the internal build system
        # returns: binary_path, compile_log, success/fail

    def profile(self, binary_path: str, device: str) -> ProfileResult:
        # runs binary on device, collects trace file
        # returns: trace_path, raw_metrics

    def apply_patch(self, patch: CodePatch) -> PatchResult:
        # writes diff to source copy, runs basic syntax check
        # returns: patched_file_path, success/fail
```

These run locally — no external calls. The agent invokes them via tool-use.

### 5.4 Trace Diff Engine

Compares two traces at the node level after a patch cycle:

```python
def diff_traces(trace_before: NodeGraph, trace_after: NodeGraph) -> TraceDiff:
    return {
        "target_node_delta_ms": before.latency - after.latency,
        "target_node_delta_pct": ...,
        "new_bottleneck": find_new_top_node(trace_after),
        "total_latency_delta_ms": ...,
        "regression_nodes": nodes_that_got_worse(before, after),
        "verdict": "IMPROVED" | "REGRESSED" | "NEUTRAL"
    }
```

The verdict feeds directly into the agent's evaluate step.

### 5.5 KB Manager

```
knowledge_base/
├── patterns/
│   ├── pat_001_unfold_to_conv2d.yaml
│   ├── pat_002_rope_compact.yaml
│   ├── pat_003_mha_split_head.yaml
│   └── ...
├── device_profiles/
│   ├── qualcomm_soc.yaml        # known quirks, thread counts, supported ops
│   ├── tenstorrent_grayskull.yaml
│   └── renesas_rcar.yaml
└── index/
    └── chroma/                  # local vector index for semantic retrieval
```

Each pattern file:

```yaml
id: pat_001
name: unfold_to_conv2d
trigger:
  op_type: Unfold
  symptoms: [single_threaded, high_latency_outlier]
  devices: [qualcomm_*]
root_cause: >
  torch.unfold maps to a gather operation on the NPU which is single-threaded.
  Conv2d with equivalent kernel achieves the same result with native multi-thread support.
fix:
  description: Replace torch.unfold with conv2d + custom kernel
  code_template: |
    # Before:
    x = x.unfold(-1, {kernel_size}, {stride}).unfold(-2, {kernel_size}, {stride})
    # After:
    weight = torch.eye({kernel_size}**2).reshape({kernel_size}**2, 1, {kernel_size}, {kernel_size})
    x = F.conv2d(x, weight.expand(-1, C, -1, -1), stride={stride}, groups=C)
validation:
  expected_latency_reduction_pct: 70
  expected_threads: 8
provenance:
  author: anonymized_operator
  date: 2026-04-08
  validated_on: [qualcomm_soc_x]
  success_count: 3
```

---

## 6. Part 3 — The AutoResearch Loop

This is the key architectural upgrade over a simple RAG chatbot. Inspired by Karpathy's
AutoResearch concept: the agent doesn't wait for human intervention between cycles. It
forms a hypothesis, runs the experiment, scores the result, reflects, and loops.

### 6.1 The Loop

```
┌─────────────────────────────────────────────────────────┐
│                   AUTORESEARCH LOOP                     │
│                                                         │
│   ┌──────────┐                                          │
│   │  START   │ ← trace_file + optimization_target       │
│   └────┬─────┘                                          │
│        ▼                                                │
│   ┌──────────┐                                          │
│   │  PARSE   │ → node_graph.json                        │
│   └────┬─────┘                                          │
│        ▼                                                │
│   ┌──────────┐                                          │
│   │  RANK    │ → top_k bottleneck nodes                 │
│   └────┬─────┘                                          │
│        ▼                                                │
│   ┌──────────────┐                                      │
│   │ HYPOTHESIZE  │ LLM forms structured hypothesis      │
│   │              │ + retrieves KB pattern if match      │
│   └────┬─────────┘                                      │
│        ▼                                                │
│   ┌──────────────┐                                      │
│   │   GENERATE   │ LLM writes code patch                │
│   │    PATCH     │ using hypothesis + KB template       │
│   └────┬─────────┘                                      │
│        ▼                                                │
│   ┌──────────────┐                                      │
│   │  APPLY +     │ patch → compile → profile            │
│   │  EXECUTE     │ (harness tool calls)                 │
│   └────┬─────────┘                                      │
│        ▼                                                │
│   ┌──────────────┐                                      │
│   │   EVALUATE   │ diff_traces → verdict + score        │
│   └────┬─────────┘                                      │
│        │                                                │
│        ├─ IMPROVED ──────────────────────────────────┐  │
│        │                                             │  │
│        │  ┌──────────┐                               │  │
│        │  │ REFLECT  │ update episodic memory        │  │
│        │  │          │ promote to KB if novel        │  │
│        │  └────┬─────┘                               │  │
│        │       └──── next bottleneck node ◀──────────┘  │
│        │                                                │
│        ├─ REGRESSED ─────────────────────────────────┐  │
│        │  rollback patch → try fallback hypothesis    │  │
│        │                                        │     │  │
│        ├─ STUCK (N attempts) ◀──────────────────┘     │  │
│        │  ESCALATE → notify engineer                   │  │
│        │  log unknown pattern for future KB seed       │  │
│        │                                              │  │
│        └─ TARGET REACHED ───────────────────────────┘  │
│           HALT → generate optimization report           │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Hypothesis Generation Strategy

The agent generates hypotheses in priority order:

**Tier 1 — KB Match (high confidence)**
Node op_type + symptoms match a known KB pattern → directly use the fix template.
Confidence = pattern's historical success rate from past cycles.

**Tier 2 — KB Analogical (medium confidence)**
No exact match but similar op family or similar symptom profile → adapt nearest pattern.
Agent explicitly reasons about the adaptation and reduces confidence accordingly.

**Tier 3 — Novel Hypothesis (low confidence)**
No KB match. Agent reasons from first principles using device context and op semantics.
This is expensive — LLM uses extended reasoning budget. Tagged `novel=true` for human
review before KB promotion.

**Tier 4 — Escalate**
After 3 failed hypotheses on the same node → flag to human with full context.

### 6.3 Reward Signal Design

The agent needs a scalar score per cycle to guide the loop and update KB confidence:

```python
def score_cycle(diff: TraceDiff, hypothesis: Hypothesis) -> float:
    # Primary: did the target node improve?
    node_improvement = max(0, diff.target_node_delta_pct / 100)

    # Penalty: did we create new bottlenecks?
    regression_penalty = 0.3 * len(diff.regression_nodes)

    # Bonus: did total model latency improve?
    total_improvement = max(0, diff.total_latency_delta_pct / 100) * 0.5

    # Calibration: was agent's confidence well-calibrated to outcome?
    calibration = 1.0 if (hypothesis.confidence > 0.6 and node_improvement > 0.3) else 0.8

    return (node_improvement + total_improvement - regression_penalty) * calibration
```

This score is stored in episodic memory and used in the reflection step to update KB
pattern confidence weights over time. This is the AutoResearch key insight: **the agent
learns from its own experiments and the KB gets smarter automatically**.

### 6.4 Reflection and KB Promotion

After a successful fix:

```
REFLECT prompt to LLM:
  "Given this trace diff and the patch applied, write a KB pattern entry.
   Include: trigger conditions, root cause explanation, fix template,
   expected latency reduction, and any device-specific caveats observed."

Output: YAML draft → engineer review queue → merged to KB
```

After a failed fix:

```
REFLECT prompt to LLM:
  "This hypothesis failed. What did we learn? Update the episodic memory
   with: why it failed, what the actual root cause might be, what to try next."
```

Over time, the KB grows from the agent's own experiments — this is the compounding
effect that makes the system more valuable the longer it runs. Engineers stop being
the sole source of pattern knowledge.

### 6.5 Multi-Agent Extension (Future)

Once the single-agent loop is stable, parallelize across nodes:

```
Orchestrator
├── Agent_A → works on node: unfold_0
├── Agent_B → works on node: rope_embed_1
└── Agent_C → works on node: mha_proj_2
```

Each agent runs its own hypothesis-experiment-evaluate loop independently. The
orchestrator ensures patches don't conflict (file-level locking), aggregates results,
and re-ranks nodes after each round to avoid wasted work if one fix changes the profile.

This is the "3–4 agents taking one task each" multi-agent extension — now with a principled
coordination model.

---

## 7. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| LLM runtime | Ollama | Local, no data egress, device-safe |
| Primary model | Gemma 3 12B / Llama 3.3 70B Q4 | Strong reasoning; fits on available GPU |
| Embeddings | nomic-embed-text (Ollama) | Local, ChromaDB compatible |
| Agent framework | **LangGraph** | Native cyclic graph support — perfect for the loop |
| KB storage | YAML + ChromaDB (local) | Human-editable + semantic search |
| Trace parser | Python (custom) | Format-specific, needs real exported trace files |
| Harness tools | Python subprocess wrappers | Thin layer over the existing internal toolchain |
| UI | Chainlit | Chat-native, shows agent reasoning steps live |
| Memory store | SQLite via LangGraph checkpointer | Simple, local, persistent across sessions |

**Why LangGraph over plain LangChain?**
The optimization loop is a cyclic state machine — evaluate → branch (improved/regressed/stuck)
→ loop. LangGraph's graph primitives map directly to this. LangChain is linear; this isn't.

---

## 8. Directory Structure

```
profiler-copilot/
├── agent/
│   ├── graph.py                # LangGraph state machine definition
│   ├── state.py                # AgentState dataclass
│   ├── nodes/
│   │   ├── observe.py          # parse + rank bottleneck nodes
│   │   ├── hypothesize.py      # form structured hypothesis (LLM)
│   │   ├── generate.py         # code patch generator (LLM)
│   │   ├── evaluate.py         # diff traces + score
│   │   └── reflect.py          # update memory + draft KB entry
│   ├── memory/
│   │   ├── working.py          # in-context state builder
│   │   ├── episodic.py         # session store (SQLite)
│   │   └── semantic.py         # KB retrieval (ChromaDB)
│   └── prompts/
│       ├── hypothesize.md
│       ├── generate_patch.md
│       └── reflect.md
├── harness/
│   ├── parser/
│   │   ├── trace_parser.py     # proprietary format → node_graph.json
│   │   └── schemas.py          # Pydantic models for node graph
│   ├── tools/
│   │   ├── compile.py
│   │   ├── profile.py
│   │   ├── patch.py
│   │   └── diff.py
│   └── devices/
│       ├── qualcomm.yaml
│       ├── tenstorrent.yaml
│       └── renesas.yaml
├── knowledge_base/
│   ├── patterns/
│   │   ├── pat_001_unfold_to_conv2d.yaml
│   │   ├── pat_002_rope_compact.yaml
│   │   └── pat_003_mha_split_head.yaml
│   └── index/chroma/
├── ui/
│   └── app.py                  # Chainlit frontend
├── config.yaml                 # device, model, thresholds
├── run.py                      # entry point
└── PLAN.md
```

---

## 9. Phased Roadmap

### Phase 0 — Ground Truth (Week 1–2)
**Goal:** Can we parse a trace and retrieve a KB pattern?

- [ ] Gather 2–3 anonymized trace files (any export format)
- [ ] Build `trace_parser.py` → validated node_graph JSON
- [ ] Seed KB with 10 patterns (unfold→conv2d, RoPE compact, MHA split-head, etc.)
- [ ] Validate ChromaDB retrieval: given a node description, does the right pattern surface?
- [ ] **Exit criterion:** Retrieval precision > 80% on seeded patterns

### Phase 1 — Single Agent Loop (Week 3–4)
**Goal:** Agent completes one full cycle without human intervention

- [ ] Implement LangGraph state machine: observe → hypothesize → generate → evaluate
- [ ] Build tool wrappers (compile, profile, diff) — stub-able if device not present
- [ ] Test with one known bottleneck + known fix (ground truth validation)
- [ ] Implement structured hypothesis schema + prompts
- [ ] **Exit criterion:** Agent correctly diagnoses and patches one known bottleneck end-to-end

### Phase 2 — The Loop (Week 5–6)
**Goal:** Agent loops autonomously until target is met or it escalates

- [ ] Add episodic memory (SQLite via LangGraph checkpointer)
- [ ] Implement reflect node + KB promotion draft
- [ ] Add fallback hypothesis logic + escalation trigger after N failures
- [ ] Validate reward function on 5 real cases
- [ ] **Exit criterion:** Agent runs 5 consecutive cycles on a real model without crashing

### Phase 3 — AutoResearch Mode (Week 7–8)
**Goal:** KB grows automatically from agent experiments

- [ ] Reflect node generates YAML pattern drafts for engineer review queue
- [ ] Implement confidence weight updates on KB patterns from cycle scores
- [ ] Track KB growth: patterns added, retrieval hit rate over time
- [ ] **Exit criterion:** 3 novel patterns promoted to KB from agent-discovered fixes

### Phase 4 — Multi-Agent + UI (Week 9–10)
**Goal:** Parallel agents + usable interface for the optimization team

- [ ] Orchestrator: assigns nodes to agents, manages patch conflicts
- [ ] Parallel agent execution (asyncio)
- [ ] Chainlit UI: agent reasoning steps live, hypothesis queue, KB browser
- [ ] Optimization report generator per model run
- [ ] **Exit criterion:** Two agents running in parallel on different nodes of same model

---

## 10. Key Design Decisions

**Why structured hypotheses instead of freeform LLM output?**
A freeform agent hallucinates and is hard to evaluate. A structured hypothesis forces a
falsifiable prediction (expected latency reduction, expected thread count) before acting.
This makes evaluation clean and episodic memory actually useful for learning.

**Why local-only?**
The target workflow involves proprietary customer models (QC, Tenstorrent, Renesas). Any cloud
call is a data leak risk. Ollama + local ChromaDB = zero egress.

**Why LangGraph?**
The loop is not a chain — it branches (IMPROVED / REGRESSED / STUCK), cycles, and has
persistent state across steps. LangGraph's graph model maps directly to this structure.

**Why KB-first hypothesis generation?**
Novel LLM reasoning is expensive and unreliable for hardware-specific patterns. The KB
encodes hard-won domain knowledge the LLM doesn't have. LLM handles adaptation and novel
cases — not as primary source of truth.

**Why score cycles?**
Scoring creates a feedback signal that updates KB pattern confidence over time. This is
what separates the system from a static RAG — it actually improves from experience.

---

## 11. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Trace format is binary / undocumented | Export manually first; parse iteratively |
| Compile/profile cycle is slow (10+ min) | Agent queues next hypothesis while waiting; async |
| Agent proposes bad patch → breaks model | Patch applied to copy only; compile failure = auto-rollback |
| KB too small to be useful initially | Seed 15–20 patterns from memory before first run |
| LLM generates invalid code | Syntax check step before compile; auto-retry with error in context |
| Multi-agent patch conflicts | File-level locking in orchestrator; serialize writes |

---

## 12. Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Cycles per bottleneck fix (manual) | ~10 | — |
| Cycles per bottleneck fix (agent) | — | ≤ 3 |
| KB retrieval hit rate | — | > 75% |
| Novel patterns promoted per month | 0 | > 5 |
| Agent escalation rate | — | < 20% |
| Total model latency reduction per run | — | > 20% |

---

## 13. Immediate Next Steps

| Owner | Action | When |
|-------|--------|------|
| Domain expert | Share 2–3 anonymized trace files | Week 1 |
| Domain expert | List 10 op patterns from memory in plain English | Week 1 |
| Implementation owner | Build trace parser scaffold + Pydantic node graph schema | Week 1 |
| Implementation owner | Set up Ollama + LangGraph + ChromaDB local env | Week 1 |
| Team | 1hr seed session: convert patterns to YAML KB entries | Week 2 |
| Implementation owner | Send a working agent demo (stub tools ok) | Week 2 |

---

## 14. Open Questions

- What is the exact profiler trace file format? (binary, XML, JSON, custom text?)
- Does the profiler dashboard have any export button, CLI flag, or API surface?
- Which Ollama model fits comfortably on the target 16GB GPU variant?
- Are there existing internal documents on known patterns that can seed the KB?
- What is the compile + profile cycle time? (determines max loop frequency)
- For multi-agent: does the internal build system support parallel compilation?
- Is there appetite to productize this internally, or is it meant for personal productivity only for now?

---

*This is a living document. Update as unknowns resolve and phases complete.*
