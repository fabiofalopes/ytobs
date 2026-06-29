# 02 — OpenCode vs Fabric: Comparison & Experiment Plan

**Question answered**: Should txrefine use Fabric CLI or OpenCode headless? How do we find out?

---

## A. Side-by-Side Comparison

| Dimension | Fabric CLI | OpenCode Headless |
|-----------|-----------|-------------------|
| **Invocation** | `fabric-ai -p <pattern> < input` | `opencode run "prompt"` or `cat input \| opencode run "instruction"` |
| **Prompt passing** | Stdin (pattern is a file on disk) | Positional args, stdin, or `--file` |
| **Prompt source** | Pattern files in `~/.config/fabric/patterns/` | Inline, or skills/agents from `.opencode/` |
| **Output** | Plain text to stdout | Plain text OR `--format json` (raw JSON events) |
| **Structured output** | ❌ None — you parse text | ✅ JSON Schema validation (`format: json_schema`) |
| **Agentic loop** | ❌ Single LLM call, no tools | ✅ Full tools (bash, read, edit, grep, webfetch, MCP) |
| **Cold boot** | ~1s | 5-15s first run (use `opencode serve` to eliminate) |
| **Session continuity** | ❌ Stateless | ✅ `--continue` / `--session` for multi-turn |
| **Model selection** | `--model <alias>` | `--model provider/model` (more explicit) |
| **Predictability** | ✅ High — same input → same call shape | 🟡 Variable — agent may take different paths |
| **Controllability** | 🟡 Low — pattern is a fixed file | ✅ High — inline prompts, skills, agents, tools |
| **Maturity for this use** | ✅ Battle-tested (ytobs uses it everywhere) | 🟡 Newer, less proven in pipelines |
| **Cost** | LLM tokens only | LLM tokens + (optional tool calls) |
| **Python integration** | `subprocess.run(["fabric-ai", ...])` — clean | `subprocess.run("opencode run ...", shell=True)` — ⚠️ MUST use `shell=True` (v1.15 execvp bug) |
| **Batch processing** | Spawn process per call | `opencode serve` daemon + HTTP API — zero cold boot per call |

### The Core Tradeoff

**Fabric** = **static, predictable, simple**. A pattern file on disk + stdin → stdout. No surprises, no agentic drift, fast cold-start. But: no structured output validation, no tool use, hard to do multi-stage logic in-process.

**OpenCode** = **robust, structured, controllable**. Structured JSON output (kills the regurgitation bug via schema validation), tool use (could verify terms against the video description), session continuity (multi-turn refinement). But: cold-boot latency, agentic unpredictability, Python integration gotcha.

---

## B. The Decisive Factor: The Regurgitation Bug

The existing txrefine is broken because the refiner outputs example text instead of processing input (see `01-current-state.md` §B). **This bug is fundamentally a validation problem** — nothing checks that the output resembles the input.

OpenCode's structured output is the single biggest differentiator:

```python
# OpenCode with JSON Schema — STRUCTURALLY IMPOSSIBLE to regurgitate
response = opencode_run(
    prompt=refine_prompt,
    input_text=transcript,
    format={
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "refined_text": {"type": "string"},
                "changes_made": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"}
            },
            "required": ["refined_text", "changes_made"]
        }
    }
)
# Then validate: len(response.refined_text) >= 0.7 * len(transcript)
```

With Fabric, you'd have to add a separate validation step (diff check, length guard) in Python — doable, but bolted-on rather than native.

---

## C. The Hybrid Option (Likely Best)

You don't have to choose globally. The txrefine step is **independent** of the rest of the pipeline. Recommended architecture:

```
ytobs pipeline
 ├─ Pattern optimizer:    Fabric (keep — works fine, fast)
 ├─ Phase 1 metadata:     Fabric (keep — works fine)
 ├─ ★ txrefine layer:    OpenCode (NEW — structured output fixes the bug)
 └─ Phase 2 patterns:     Fabric (keep — works fine, 70+ patterns ready)
```

**Why hybrid wins:**
- Keeps the 70+ existing Fabric patterns untouched (zero migration risk)
- Uses OpenCode only where its strengths matter (structured refinement output)
- txrefine becomes a **swappable backend** — `refine_transcript(backend="fabric"|"opencode"|"api")`
- You can A/B test backends on the same transcripts

---

## D. The Experiment Plan

### Goal
Determine whether OpenCode headless produces **more reliable** transcript refinement than Fabric CLI, specifically measuring the regurgitation failure rate.

### Hypothesis
OpenCode with JSON Schema structured output + length-validation guardrail will achieve <5% failure rate on the regurgitation bug, vs Fabric's current ~40-60% failure rate (estimated from dev notes).

### Test Corpus

Use these transcripts (already cached in ytobs or easily fetchable):

| ID | Type | Length | Why |
|----|------|--------|-----|
| `jNQXAC9IVRw` | Short, clean speech | 19s | Baseline — should always work |
| `RB8vjn1QPeM` | Your example video | TBD | Real-world test |
| `ugvHCXCOmm4` | Long (5h+), technical | 5h15m | Stress test — chunking + context |
| A voice note | Casual, fillers, STT errors | ~30s | The original txrefine use case |

### Test Harness

Create a script `experiments/txrefine_compare.sh` (NOT in the pipeline — pure test):

```bash
#!/bin/bash
# experiments/txrefine_compare.sh
# Runs the same transcript through Fabric txrefine AND OpenCode txrefine, saves both outputs

set -e
TRANSCRIPT_FILE="$1"
LABEL="$2"
OUTDIR="experiments/results/$LABEL"
mkdir -p "$OUTDIR"

echo "=== Fabric backend ==="
cat "$TRANSCRIPT_FILE" | txrefine > "$OUTDIR/fabric_output.txt" 2>"$OUTDIR/fabric_stderr.log" || echo "FABRIC FAILED" > "$OUTDIR/fabric_output.txt"

echo "=== OpenCode backend ==="
# (Requires the opencode txrefine skill/agent — see 04-integration-design.md)
cat "$TRANSCRIPT_FILE" | opencode run --agent txrefine --format json "Refine this transcript" \
  > "$OUTDIR/opencode_output.json" 2>"$OUTDIR/opencode_stderr.log" \
  || echo "OPENCODE FAILED" > "$OUTDIR/opencode_output.json"

echo "=== Metrics ==="
python3 experiments/metrics.py "$TRANSCRIPT_FILE" "$OUTDIR/fabric_output.txt" "$OUTDIR/opencode_output.json" > "$OUTDIR/metrics.json"
cat "$OUTDIR/metrics.json"
```

### Metrics (what "better" means)

For each (transcript × backend) pair, measure:

| Metric | How | Pass Threshold |
|--------|-----|----------------|
| **Regurgitation rate** | Does output contain >50% of any prompt example? | 0% (hard fail otherwise) |
| **Length preservation** | `len(output) / len(input)` | 0.70 - 1.15 |
| **Content preservation** | % of input bigrams present in output | > 85% |
| **Error correction rate** | # of obvious ASR errors fixed (manual spot-check on sample) | Subjective, track over time |
| **Latency** | Wall-clock time | Record, no threshold |
| **Cold-boot overhead** | First-call vs warm-call latency | Record |

### Decision Framework

After running the experiment on all 4 test transcripts:

| Result | Action |
|--------|--------|
| OpenCode: 0% regurgitation, >85% bigram preservation, acceptable latency | ✅ Adopt OpenCode as txrefine backend (hybrid architecture) |
| OpenCode: fixes regurgitation but latency >30s per chunk | 🟡 Use OpenCode only for short transcripts; Fabric or skip-refine for long |
| OpenCode: also regurgitates | 🔴 The bug is prompt-side, not backend-side. Redesign prompts (see Doc 03). Re-test. |
| Fabric with validation guardrail: 0% regurgitation | 🟡 Keep Fabric (simpler), add Python-side length/content validation |

---

## E. OpenCode Invocation Patterns for txrefine

### Pattern 1: One-shot subprocess (simplest, has cold-boot)

```python
import subprocess, shlex

def refine_with_opencode_oneshot(transcript: str, video_context: dict = None) -> str:
    ctx_str = _format_context(video_context)  # channel, tags, description
    prompt = f"{REFINE_SYSTEM_PROMPT}\n\n{ctx_str}\n\n---\n\nTRANSCRIPT TO REFINE:\n{transcript}"
    # ⚠️ MUST use shell=True — OpenCode v1.15 execvp bug returns empty output otherwise
    result = subprocess.run(
        f'opencode run --agent txrefine --format json {shlex.quote("Refine the transcript below.")}',
        shell=True,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"opencode failed: {result.stderr}")
    return _parse_opencode_json(result.stdout)
```

### Pattern 2: Persistent server (best for batch — zero cold boot)

```bash
# Start once (daemon):
opencode serve --port 4096 &
```

```python
import requests

BASE = "http://localhost:4096"

def refine_with_opencode_server(transcript: str, video_context: dict = None) -> str:
    # Create session
    sid = requests.post(f"{BASE}/session", json={"title": "txrefine"}).json()["id"]
    # Send refinement prompt with structured output
    resp = requests.post(f"{BASE}/session/{sid}/message", json={
        "parts": [{"type": "text", "text": _build_prompt(transcript, video_context)}],
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "refined_text": {"type": "string"},
                    "changes_made": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["refined_text"]
            }
        }
    })
    return resp.json()["info"]["structured_output"]["refined_text"]
```

### Pattern 3: TypeScript SDK bridge (most robust, most setup)

Use `@opencode-ai/sdk` from a small Node script called via subprocess. Overkill for txrefine unless you're already in JS-land. See OpenCode SDK docs.

---

## F. The Cold-Boot Problem (And the Fix)

OpenCode's 5-15s cold boot is the main downside vs Fabric's ~1s. For **interactive ytobs use** (one video at a time), this is tolerable. For **batch processing** (channels, playlists), it's fatal.

**Solution**: `opencode serve` as a daemon.

```bash
# Add to your shell startup (~/.zshrc):
# Start opencode server if not running (for txrefine batch use)
if ! pgrep -f "opencode serve" > /dev/null; then
  (opencode serve --port 4096 > /tmp/opencode-serve.log 2>&1 &)
fi
```

Then all txrefine calls hit the warm server: ~1-2s per call, same as Fabric.

---

## G. Recommendation

**Go hybrid. Start with the experiment.**

1. Build the test harness (§D) — 1 hour.
2. Port the two existing Fabric patterns to OpenCode inline prompts — 30 min.
3. Run the experiment on the 4 test transcripts — 15 min.
4. Decide based on the metrics — use the framework in §D.

If OpenCode wins (likely, given structured output kills the regurgitation bug), wire it in per Doc 04. If Fabric-with-validation wins, even better — less new infrastructure.

**Don't** do a full Fabric→OpenCode migration of ytobs. The 70+ Fabric patterns work. Only swap where OpenCode's strengths matter (structured output, tool use, multi-turn).
