# Vault Runbook: What Broke, Why, and What We Want from ytobs

Single source of truth for operating the YouTube→Obsidian pipeline against the real vault: current vault state, why past runs failed or duplicated, the locked product decisions, and day-to-day procedures.

**Repo**: `~/projetos/hub/ytobs` (pip package `ytobs`, v4.0.0 → v4.1.0)
**Vault**: `$OBSVAULT/youtube/`
**Last updated**: 2026-09-03

---

## The Vault Today (2026-09-03)

| Metric | Value |
|--------|-------|
| Notes in `$OBSVAULT/youtube/` | 148 |
| Frontmatter `status` | All `raw` |
| Notes with filled AI Analysis sections | ~20 |
| Notes with empty pattern headings | ~128 |
| `video_id` duplicate clusters | 8 |

Details:

- **Empty pattern headings**: roughly 128 notes carry pattern section headers with nothing under them. This is failed-run residue. The note template wrote the headings, the fabric calls behind them failed (quota cliffs, template-strict 400s, optimizer JSON breakage), and the note was saved anyway.
- **Duplicate clusters**: 8 distinct `video_id` values map to more than one file. Worst cases: `me_at_the_zoo` ×11, `dario_amodei` ×8. Cause: filename-collision suffixing. When the target filename already existed, the writer created `title (2).md`, `title (3).md`, and so on, each treated as a fresh note for the same video.
- **Unfenced transcripts**: transcripts are stored as plain markdown. Any backtick or heading-like line inside a transcript breaks note rendering and downstream parsing.

---

## Challenge Log

Why runs failed or duplicated. Each entry: symptom → root cause → status.

### 1. Groq 400s: "No user query found in messages" / "last message role must be 'user'"

- **Symptom**: fabric calls against Groq fail with HTTP 400; the API claims no user message exists in the payload.
- **Root cause**: fabric patterns that embed `{{input}}` inside `system.md` suppress the user message entirely. The request arrives system-only, and template-strict models (Qwen, compound) reject it. Upstream fabric issue #2108, unfixed at v1.4.473.
- **Fix**: local patched build `v1.4.473+dirty` at `~/.local/bin/fabric` promotes a lone system message to user role. Rebuild instructions in HELP.md ("Model compatibility: fabric + template-strict models").
- **Status**: ✅ patched 2026-09-01.

### 2. Groq quota cliffs: TPM 8000 and TPD 200K

- **Symptom**: two distinct walls. Packets over 8K tokens get HTTP 413 (Request Entity Too Large); per-model daily buckets drain mid-day (TPD 200K, qwen3.8-27b exhausted during Def Con validation).
- **Root cause**: Groq free-tier limits. `find_logical_fallacies` template alone is ≈6.5K tokens, so template + any chunk exceeds 8K TPM. That pattern is impossible on Groq free tier, period.
- **Status**: ⚠️ known constraint, not fixable client-side. Batch jobs must be quota-aware and prefer off-peak hours. The Lusófona endpoint (amalia-9b) has no such cliff.

### 3. `--force --patterns X` created a new note instead of overwriting

- **Symptom**: re-running a pattern with `--force` produced `filename (2).md` instead of editing the original note.
- **Root cause**: the force path routed through `resolve_collision`, which suffixes instead of overwriting.
- **Status**: ✅ fixed in v4.1.0. `--force` now overwrites the original note in place.

### 4. Cache marked FAILED patterns as "run"

- **Symptom**: after a partially failed run, `--append` reported the failed patterns as "already run" and skipped them.
- **Root cause**: cache recorded attempted patterns, not successful ones.
- **Status**: ✅ fixed in v4.1.0. Only successful non-empty outputs are recorded.

### 5. pattern_optimizer: broken JSON and wrong model

- **Symptom**: optimizer output failed to parse (missing or trailing commas in JSON); the optimizer also ran on fabric's default model instead of the configured one.
- **Root cause**: some models deterministically emit malformed JSON; the optimizer call was not pinned to the ytobs model.
- **Status**: ✅ fixed 2026-09-01 (`_parse_optimizer_json` repair + pinned model).

### 6. Over-patterned notes

- **Symptom**: auto mode ran 10-15 patterns per note. The Def Con validation note ended up with 15 sections and 201KB. User verdict: too much.
- **Status**: ✅ v4.1.0 adds a "curated" mode (`extract_wisdom` + `summarize`) as the template default.

---

## What We Want from ytobs (Locked Decisions, 2026-09-03)

1. **Retro-enrichment of pattern-less notes** with `extract_wisdom` + `summarize`, edited IN PLACE. Never create new files for existing videos.
2. **Model provenance on every pattern section**: a `*Model: X · date*` line under each section heading, plus a `pattern_runs` log in frontmatter.
3. **One canonical note per video.** Duplicates get `status: duplicate` and a `duplicate_of` pointer. Never deleted.
4. **Transcript refinement layer** between raw transcript and patterns. Regex pre-pass always; LLM 2-stage fabric refinement for new runs with validation guards. Both raw and refined kept, both fenced.
5. **Raw transcripts always fenced** in backtick-safe code blocks.
6. **Minimal default pattern footprint**: curated mode (`extract_wisdom` + `summarize`) is the default.

---

## Operating Procedures

### Retro batch (enrich the ~128 pattern-less notes)

```bash
# Always dry-run first: see which notes qualify and what would change
ytobs retro --dry-run --limit 5

# Then run for real, small batches, watching quota
ytobs retro --limit 5
```

- Edits happen in place. No new files.
- Keep batches at 5 notes or fewer per run (see Quota Playbook).
- Runs `extract_wisdom` + `summarize` only, with provenance lines.

### Dedupe (collapse the 8 duplicate clusters)

```bash
ytobs dedupe            # report only: shows clusters and proposed canonical note
# review the report by hand
ytobs dedupe --apply    # mark duplicates: status: duplicate + duplicate_of
```

- Nothing is ever deleted. Losers get `status: duplicate` and `duplicate_of: <canonical>`.
- Review the report before `--apply`. Human approves canonical choice.

### New video (the normal flow)

```bash
ytobs "https://www.youtube.com/watch?v=VIDEO_ID"
```

- Transcript refinement is ON by default (regex pre-pass + fabric 2-stage with validation guards).
- Skip refinement with `--no-refine` if needed.
- Curated pattern set by default; provenance lines and `pattern_runs` frontmatter written automatically.

### Backups and deletion policy

- Backups live under `~/.yt-obsidian/backups/`, outside the vault. Restore from there if a batch edit goes wrong.
- Vault policy: no note deletion without explicit human approval. `dedupe --apply` marks, never deletes.

---

## Quota Playbook

### Model registry (all free, live-tested)

| Role | Model | Notes |
|------|-------|-------|
| `best` | `qwen/qwen3.8-27b` | Default. 131K context. Groq TPM/TPD buckets apply. |
| `fast` | `openai/gpt-oss-20b` | First fallback. |
| `quality` | `openai/gpt-oss-120b` | Second fallback. |
| `compound` | `groq/compound-mini` | Last fallback. Template-strict: requires the patched fabric build. |
| `pt` | `amalia-9b` (Lusófona) | No TPM/TPD cliff. Portuguese and overflow duty. |

**Fallback chain**: `best` → `fast` → `quality` → `compound`.

### The cliffs

| Limit | Effect |
|-------|--------|
| TPM 8000 (Groq) | HTTP 413 for any packet over 8K tokens. Big templates (e.g. `find_logical_fallacies` ≈6.5K) plus any chunk blow past it. |
| TPD 200K per model (Groq) | Per-model daily bucket. Exhausting it mid-batch kills that model until reset. |
| Lusófona (amalia-9b) | No known TPM/TPD cliff. |

### Batch guidance

- **≤5 notes per run.** More than that risks draining a daily bucket mid-batch.
- **Run off-peak** when possible.
- **Shortest transcripts first** in retro batches: cheap wins early, quota stays for the long ones.
- If a model exhausts, let the fallback chain carry the run; do not retry into a 429/413 wall.
