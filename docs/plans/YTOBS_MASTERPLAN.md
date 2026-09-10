# YTOBS Masterplan — Multi-Session Work Plan

**Protocol**: PLAN → SKILL → EXECUTE → HANDOFF → RESUME. Update this file at
the end of every session. Externalize immediately — TodoWrite is ephemeral,
this file is permanent.

**Last updated**: 2026-09-05
**Package**: ytobs v4.1.0 (pip) + 2026-09-05 gas overhaul (uncommitted)
**Ops docs**: [docs/RUNBOOK.md](../RUNBOOK.md) · [docs/AGENTIC_GRAPH.md](../AGENTIC_GRAPH.md) · [docs/MODEL_CONTEXT_LIMITS.md](../MODEL_CONTEXT_LIMITS.md)

---

## Status: where the pipeline stands

- ✅ Gas: `go` = mimo-v2.5 direct API (OpenCode Go), chain
  go → gofree → gofabric → fast → quality. Validated E2E (GTA 6 note).
- ✅ Transports: direct OpenAI-compat adapter + fabric-LiteLLM env wiring.
- ✅ Exact context limits verified and synced into all configs.
- ✅ `ytobs doctor` health check shipped — the standing entry point for
  failure sessions (Failure Session Protocol: docs/AGENTIC_GRAPH.md §0).
  Also covers the Lusófona watchdog + quota-state check.
- ⚠️ 12 modified files uncommitted (session 2026-09-05).
- ⚠️ Vault: 65 retro targets remain; 37 of those have no transcript in cache.

## Work queue (in dependency order)

### Wave 0 — Seal the session (next session should START here)
- [ ] **Commit the 2026-09-05 work** — 12 files: backend_adapter, rate_limiter,
  config, packet_builder, chunker, fabric_orchestrator, metadata_extractor,
  transcript_refiner, cli, incremental_writer, doctor (new) + docs
  (MODEL_CONTEXT_LIMITS, AGENTIC_GRAPH, masterplan, RUNBOOK/START_HERE/README
  refresh).
  Suggested split: (1) transport+chain+doctor, (2) docs+limits, (3) fixes
  (argv pre-parse, pattern_runs on append).
- [ ] Verify fresh-run regression: `ytobs doctor && ytobs --preview <new-video-url>`.
- [ ] Then run every failure session via the Failure Session Protocol
  (docs/AGENTIC_GRAPH.md §0): doctor → classify → fix → write back.

### Wave 1 — Retro backlog on the new gas (~$2 total, minutes per batch)
- [ ] **Re-fetch transcripts for the 37 retro targets without cached
  transcripts** (`--update` backlog). Command: pick IDs from cache report →
  re-run extractor. This unblocks retro for them.
- [ ] **Retro batches on mimo**: `ytobs retro --dry-run --limit 5` →
  `ytobs retro --limit 5`, repeat. ~65 targets ≈ 13 batches ≈ $2 on Go quota.
  Check quota first: `npm run quota:status` (in ~/.config/opencode).
- [ ] After batches: spot-check 3 notes for Model provenance lines +
  `pattern_runs` frontmatter + no new duplicate headings.

### Wave 2 — Pipeline polish
- [ ] **Append fills empty headings**: append path currently adds a fresh
  `### Pattern` next to stale empty ones from old failed runs. Make
  `_insert_into_ai_analysis` detect an existing EMPTY `### {Name}` heading
  and fill it in place (then mark the retro value: those notes self-heal on
  next append).
- [ ] **Wire `--stream` path through the adapter** (fabric_orchestrator.py:497
  Popen is raw subprocess, no env/vendor injection). Low priority: only used
  with explicit `--stream`.
- [ ] **`pt` language runs**: when Lusófona returns, verify amalia-9b again;
  meanwhile `output_language: Portuguese` in config + mimo handles PT content
  (test once on a PT video, e.g. Filipe Grilo #118 needs transcript re-fetch).

### Wave 3 — Watchdogs (passive, now covered by doctor)
- [x] **Lusófona watchdog** — folded into `ytobs doctor` (HTTP status check,
  warning-only when down). 2026-09-05.
- [ ] When Lusófona returns 200: re-validate amalia-9b/ornith/omnicoder,
  update MODEL_CONTEXT_LIMITS.md (pt ctx 32768 is historical, unverified),
  and test a PT video end-to-end.

### Backlog (ideas, not committed)
- [ ] Usage tracking persisted per run (cost ledger in cache) — adapter
  already prints 📊 tokens; store them in `pattern_runs` records too.
- [ ] Vault-wide bulk ops (`yt vault apply PATTERN --all`) from V4.0 spec.
- [ ] Audio download as Opus files linked to notes (README roadmap).
- [ ] Playlist/channel batch processing hardening (channel.py).

## Session log index (full text lives in ../CONTEXT.md)

| Date | What |
|---|---|
| 2026-09-05 | Go-as-gas overhaul: direct adapter, chain rebuild, argv fix, pattern_runs on append, E2E green (GTA 6) |
| 2026-09-05 | Exact context limits verified (bracket-probing + Groq live API), synced to all configs |
| 2026-09-03 | V4.1.0 shipped: retro/dedupe/refinement/provenance; Sprint 2 patterns family; repo sealed |
