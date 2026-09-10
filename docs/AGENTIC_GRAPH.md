# Agentic Graph — ytobs Execution, Routing, and Breakage Traces

**Purpose**: the practical map a future agent needs to operate or debug ytobs
without re-deriving anything. Verified 2026-09-05. Sources of truth:
[MODEL_CONTEXT_LIMITS.md](MODEL_CONTEXT_LIMITS.md) (exact limits),
[RUNBOOK.md](RUNBOOK.md) (vault ops), [../CONTEXT.md](../CONTEXT.md) (history).

---

## 0. Failure Session Protocol (standing rule)

**Every time the tool fails, a session runs here and the learning compounds.**
The loop:

1. **Triage**: `ytobs doctor` (built-in health check: env → config → keys →
   endpoints → fabric patterns → quota → smoke test of the primary model
   through the real adapter). Exit 1 = hard failure; read the ❌ rows first.
2. **Classify**: match the symptom against the breakage tree (§4). If it's a
   NEW failure class, root-cause it (probe recipe in §5 when model-behavior
   is suspected).
3. **Fix** the smallest thing that makes the class impossible to recur:
   - one-off state → fix config
   - repeated diagnosis → add a check to `ytobs/doctor.py`
   - model/provider behavior → add a row to the breakage tree (§4) +
     MODEL_CONTEXT_LIMITS.md if limits are involved
   - code bug → fix + E2E verify
4. **Write back**: update this graph, masterplan checkboxes, CONTEXT.md
   session log. A failure session that doesn't update the structure hasn't
   happened.

The compounding invariant: `ytobs/doctor.py` must always contain a check for
every failure class that has ever been diagnosed manually. New check = the
next failure session starts past it.

---

## 1. Runtime execution graph (one `ytobs URL` run)

```
URL ──► validate_url ──► Phase 0: cache check (CacheManager)
                           │  hit → SKIP (suggest --append/--force)
                           ▼
                     extractor (yt-dlp metadata + transcript)
                           ▼
              ┌─ transcript_refiner ──────────────────┐
              │  regex pre-pass (always)              │
              │  + 2-stage LLM (fabric backend,       │
              │    validation guards, on_fail=fallback)│
              └───────────────┬───────────────────────┘
                              ▼
              Phase 1: MetadataExtractor (3 patterns, ONE call
              each on the FULL transcript — no chunking)
                              ▼
              chunk_transcript (TranscriptChunker)
              chunks = expert.chunk_size tokens (8000)
              + packet preamble (VIDEO CONTEXT, CONTENT CONTEXT,
                CHUNK INFO, OUTPUT REQUIREMENTS: English)
                              ▼
              Phase 2: per pattern × per chunk ──► RateLimitHandler
                              ▼ (primary → fallback chain on 429/5xx)
              join chunks ──► formatter (### sections, *Model:* lines,
              pattern_runs frontmatter) ──► save note + cache entry
```

Key invariants an agent must not break:
- **The 4 request-size gates** (`validate_request_size`, words×1.3+800):
  `fabric_orchestrator.py:401,493`, `metadata_extractor.py:226`,
  `transcript_refiner.py:453`. They gate against `ModelConfig.context_window`
  only for the PRIMARY model.
- **Chunk size knob is `expert.chunk_size`** (live config). The `chunking:`
  YAML block is dead at runtime. This has confused two past sessions.
- **Append/force edit notes in place** — never suffix filenames (locked
  decision #1). Failed patterns must NOT be marked as run (W4).

## 2. Transport routing graph (how a pattern call reaches a model)

```
ModelHandle.from_config(ModelConfig)
        │
        ├─ provider: openai-compat ──► OpenAICompatAdapter
        │      direct streaming POST {base_url}/chat/completions
        │      pattern = ~/.config/fabric/patterns/<p>/system.md
        │      {{input}} present → single user message (strict-safe)
        │      {{input}} absent  → system+user pair
        │      key: api_key_env → OpenCode auth.json[auth_provider]
        │      usage: 📊 tokens in/out printed per call
        │      max_output_tokens cap (config, per model)
        │
        └─ provider: fabric ──► FabricAdapter
               subprocess: fabric -p PATTERN -m MODEL_ID
               ModelConfig.base_url set?
                 yes → + --vendor LiteLLM
                     + env LITELLM_API_BASE_URL / LITELLM_API_KEY
                 no  → fabric's own .env (Groq / Ollama / Lusófona)

config.model (alias) ──► fallback chain = config.fallback_models
   (primary auto-skipped; missing aliases ignored)
```

**Adapter contract**: `run_pattern(pattern, input_text, model_id, timeout) →
AdapterResult(success, output, error)`. Adding a provider = one class in
`backend_adapter.py` + registry entry. No orchestrator changes.

**NOT adapter-wired**: the `--stream` Popen path (`fabric -s`,
`fabric_orchestrator.py:497`) — raw subprocess, no env/vendor injection.
Only used when the user passes `--stream`. Candidate work item.

## 3. Model chain (validated 2026-09-05)

```
PRIMARY: go = mimo-v2.5 (direct API, OpenCode Go)
   │      ~80s/pattern-chunk · 2.4K out-tokens · $0.14/M in / $0.28/M out
   │      ctx 1,048,576 · out 128,000 · EN (guarded by OUTPUT REQUIREMENTS)
   ▼
gofree = nemotron-3-ultra-free (direct API, OpenCode Zen, $0)
   ▼     ~2m20s/pattern-chunk (slow) · EN
gofabric = mimo-v2.5 via fabric-LiteLLM (transport fallback, 54s/pattern)
   ▼
fast = gpt-oss-20b (Groq free) → quality = gpt-oss-120b (Groq free)
         8K TPM cliff + TPD 200K/model buckets apply

Side slots (NOT in the chain):
  goflash = glm-5.3-flash — small-output tasks ONLY (pattern_optimizer,
            metadata). Over-reasons on big extraction: burned 38K reasoning
            tokens → empty content. When good: 3s/call.
  pt      = amalia-9b — DEAD (Lusófona 503 site-wide since ≤2026-09-05)
```

Do NOT chase: muse-spark (Responses-API-only; Meta trains on prompts),
deepseek-v4-flash (China opt-in block), longcat-2.0 (fabric hang),
kimi-k2.7-code (needs -r + hangs), big-pickle/mimo-free (congested free pool),
local Ollama `:cloud` (402), LM Studio (empty).

## 4. Breakage decision tree (error → meaning → action)

| Observed | Meaning | Action |
|---|---|---|
| anything unexpected | unknown class | **run `ytobs doctor` first** — env/keys/endpoints/fabric/smoke triage in one command |
| `fabric -L` prints Lusófona 503 HTML | modelos.ai.ulusofona.pt down site-wide | nothing to fix; chain auto-avoids `pt`. Retry `curl -s https://modelos.ai.ulusofona.pt` periodically |
| `402 Payment Required` on Ollama-named model | fabric matched Ollama vendor (ollama.com) | pass `--vendor LiteLLM` explicitly, or check ModelConfig.base_url wiring |
| `invalid temperature: only 1 is allowed` | model rejects fabric's sampling params (e.g. kimi) | add `-r` (raw) — `raw: true` in ModelConfig |
| `Model exhausted max_output_tokens on reasoning...` (adapter) | reasoning model ate the whole cap with zero visible content | switch task to a non-reasoning model (mimo) or raise cap |
| `Empty response from stream` (fabric path) | reasoning model + fabric SSE stall (glm/longcat/kimi) | use the direct adapter for that model |
| HTTP 000 / hang on >1M-token mimo request | gateway prefill chokes >1M, no clean reject | keep mimo prompts <~900K tokens |
| `413 Request Entity Too Large` (Groq) | packet > 8K TPM on Groq free tier | don't shrink chunks — use `go`/`gofree`/`gofabric` instead |
| `Rate limit exceeded. Please try again later.` (Console) | Zen free pool congested (big-pickle, mimo-free) | fall back to Go models; retry later for free-tier duty |
| `Prompt exceeds max length` [1261] | over the model's context | bisect with `"a " × N` probes; see MODEL_CONTEXT_LIMITS.md |
| Chinese output sections | MiMo language drift | check packet preamble has OUTPUT REQUIREMENTS: English (packet_builder.py) |
| `Only youtube.com and youtu.be links are supported` wrongly | `--patterns VALUES` stolen as URL (fixed 2026-09-05) | update cli.py pre-parse if regression appears |
| Zero analysis in new note, no errors | append path appended nothing / pattern failed silently | check `pattern_runs` frontmatter + cache entry; re-run with `--append --force` |
| Duplicate `### Pattern` headings (one empty) | old failed-run residue + append creates fresh heading | cosmetic; `retro` targets them — fill-don't-duplicate is a planned improvement |

## 5. This session's decision trace (replayable research path)

```
Trigger: Lusófona 503 + two newest vault notes with zero AI analysis
   │
   ├─► Hypothesis: transport layer, not orchestration → NO LangChain
   │    (template-in/text-out; adapter layer was the designed seam)
   │
   ├─► Discovery: OpenCode Go/Zen expose OpenAI-compatible endpoints
   │    (docs/go, docs/zen) + auth.json providers opencode-go/opencode
   │
   ├─► Live validation matrix (curl + fabric --vendor LiteLLM):
   │    mimo ✅ / nemotron-free ✅ / glm hang / kimi -r + hang /
   │    longcat hang / deepseek blocked / muse-spark wrong API shape
   │
   ├─► Build: OpenAICompatAdapter (streaming, strict-safe, usage-capped)
   │    + FabricAdapter env wiring + config-driven fallback chain
   │
   ├─► E2E on GTA 6 note: extract_wisdom 3 chunks ≈2.5min, append green
   │
   ├─► Empirics that changed the plan:
   │    glm-5.3-flash 38K-token reasoning burn → demoted to goflash
   │    mimo ZH drift (non-deterministic) → OUTPUT REQUIREMENTS directive
   │    mimo via DIRECT adapter = the workhorse (fabric path = fallback)
   │
   └─► Limits verification: bracket-probing → 2^20 for glm/nemotron;
        Groq live /models for the free tier; docs/MODEL_CONTEXT_LIMITS.md
```

Probing recipe (reusable): generate `"a " × N` prompts, max_tokens=1, read
the API's own token count from `usage.prompt_tokens`. Over-limit probes are
free when the API rejects with a message; accepted probes bill input tokens
at the model's input rate (probe cost ≈ N × rate).

## 6. Economics (Go quota is shared with your coding agent)

| Operation | Tokens | Cost (mimo-v2.5) |
|---|---|---|
| Curated note (2 patterns, ~3 chunks) | ~90K | ~$0.03 |
| Phase 1 metadata (3 patterns, 1 call each) | ~50K | ~$0.01 |
| Retro note (extract_wisdom + summarize) | ~100K | ~$0.03 |
| Full 65-note retro backlog | ~6.5M | ~$1.5–2.0 |

Go limits: $12/5h rolling, $30/week, $60/month — shared with coding usage.
ytobs batches are noise-level, but poll `npm run quota:status` (in
`~/.config/opencode`) before big batches. The Go quota poller is currently
broken (`opencode-go-usage` can't find meter data); usage is visible in the
console at https://opencode.ai/auth.
