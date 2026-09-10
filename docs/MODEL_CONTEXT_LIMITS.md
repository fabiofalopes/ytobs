# Exact Model Context Limits — ytobs Model Registry

**Verified: 2026-09-05.** These are the EXACT numbers to trust, with the source
for each. The `context_window` field in `~/.yt-obsidian/config.yml` (and the
Python defaults in `ytobs/config.py`) must match this table — it is a hard
client-side gate at 4 call sites (`validate_request_size`, words×1.3+800
estimate): `fabric_orchestrator.py:401,493`, `metadata_extractor.py:226`,
`transcript_refiner.py:453`.

## How these were measured (methods, in trust order)

1. **Gateway-enforced error message** — the API itself stated the number when
   rejecting an over-limit prompt. Gold standard.
2. **Live API metadata** — `GET /v1/models` `context_window` field returned by
   the serving API (Groq). Gold standard.
3. **Gateway bracket-probing** — prompts sent at increasing sizes until
   accepted/rejected, with usage-confirmed token counts from the API itself.
4. **Vendor-native spec** — models.dev provider entries (xiaomi/zai/nvidia) or
   vendor docs. Authoritative for the raw model, but the gateway may serve a
   different effective value (see glm-5.3-flash note below).

## Context windows (exact)

| alias | model | context window (tokens) | max output (tokens) | source |
|---|---|---|---|---|
| `go`, `gofabric` | mimo-v2.5 (Xiaomi, OpenCode Go) | **1,048,576** native; gateway-verified pass at 300,253 tok; prompts >1M hang without rejection (gateway prefill issue) | 128,000 via gateway / 131,072 Xiaomi native | models.dev `xiaomi/mimo-v2.5` (ctx 1048576) + live probes |
| `goflash` | glm-5.3-flash (Z.ai, OpenCode Go) | **1,048,576** — bracketed live: accepted 1,048,018 tok, rejected 1,050,023 tok; 2^20 is the only clean boundary | 131,072 | live bracket-probes (usage-confirmed) + models.dev `zai/glm-5.3-flash` |
| `gofree` | nemotron-3-ultra-free (NVIDIA, OpenCode Zen) | **1,048,576** — stated verbatim by gateway error: "maximum context length is 1048576 tokens" | 128,000 via Zen / 65,536 NVIDIA native | gateway-enforced error + models.dev `nvidia/nemotron-3-ultra-550b-a55b` |
| `best` | qwen/qwen3.8-27b (Groq free tier) | **131,042** | **16,384** | Groq API `/openai/v1/models` `context_window` field (live) |
| `fast` | openai/gpt-oss-20b (Groq) | **131,072** | **65,536** | Groq API `/openai/v1/models` (live) |
| `quality` | openai/gpt-oss-120b (Groq) | **131,072** | **65,536** | Groq API `/openai/v1/models` (live) |
| `compound` | groq/compound-mini (Groq) | **131,072** | **8,192** | Groq API `/openai/v1/models` (live) |
| `pt` | amalia-9b (Lusófona) | 32,768 (historical value) | — | **endpoint 503 site-wide since ≤2026-09-05 — unverifiable** |
| `ornith` | ornith-9b (Lusófona) | 32,768 (historical value) | — | same |
| `omnicoder` | omnicoder-9b (Lusófona) | 32,768 (historical value) | — | same |

## Notes and gotchas

- **glm-5.3-flash gateway vs vendor spec disagree.** models.dev's z.ai entry
  says 1,000,000 ctx; the OpenCode Go gateway actually served 1,048,018 tokens
  and rejected 1,050,023 → effective gateway limit is 2^20 = 1,048,576. Trust
  the gateway number for runtime config.
- **mimo-v2.5 >1M-token prompts hang** (HTTP 000, no error body) instead of
  returning a clean limit error — the gateway's prefill path chokes above
  ~1M tokens. Practical guidance: keep mimo requests under ~900K tokens even
  though the spec says 1,048,576.
- **mimo-v2.5 is a hybrid reasoning model**: small prompts emit
  `reasoning_content` before any `content` (doctor smoke showed a 5-token
  budget producing "Hmm, the user" with null content). Pattern work at
  real budgets is unaffected; don't judge endpoint health from
  token-starved probes.
- **Prompt caching is live on the Go gateway**: the 300K-token mimo probe
  showed 287,744 `cached_tokens` — repeated big prompts bill cached-read
  pricing ($0.0028/M for mimo).
- **`max_output_tokens` in ytobs config (8,000)** is our own burn cap — far
  below every model's real output limit. Exception to watch: if you ever use
  `compound` (Groq compound-mini, 8,192 max completion) the cap nearly
  saturates it.
- **glm-5.3-flash over-reasons**: with big extraction patterns it can burn
  its entire completion budget on `reasoning_content` and emit zero visible
  content (observed: 8K-token budget → empty output; uncapped: 38,339
  reasoning tokens). Keep it on small-output tasks only.
- The 4 gate sites validate against the **primary** model's window only;
  fallback models are not re-validated (e.g. a packet that fits `go`'s 1M
  would still be rejected by Groq's 131K if `go` fails over — the gateway/API
  returns its own error in that case).
- Chunk sizing does NOT use context_window: runtime knob is
  `expert.chunk_size` (currently 8,000 tokens — all windows above are ≥16x
  that).

## Unprobed registry extras (for completeness)

| model | context | max output | source |
|---|---|---|---|
| glm-5.2 (Go) | 1,000,000 native (models.dev zai) — NOT gateway-probed | 131,072 | models.dev |
| kimi-k2.7-code (Go) | not probed | 262,144 | models.dev |
| deepseek-v4-flash (Go) | not probed — **blocked**: China-hosting opt-in required | 384,000 | models.dev |
| minimax-m2.7 / m3 (Go) | Anthropic-style `/messages` endpoint — not fabric/adapter-usable | — | OpenCode Go docs |
| muse-spark-1.3-contributor (Go/Zen) | **/responses endpoint only** — not chat-completions-usable; Meta trains on prompts (Contributor tier) | — | OpenCode Go docs |
