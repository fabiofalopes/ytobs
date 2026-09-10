# YouTube-Obsidian - Quick Start for AI Agents

**Version:** V4.1.0 + 2026-09-05 Gas Overhaul (direct OpenCode Go transport)
**Status:** ✅ Operational on mimo-v2.5 chain — 10 files uncommitted (see masterplan)
**Location:** `~/projetos/hub/ytobs/`
**Command:** `ytobs "YOUTUBE_URL"`

---

## 🎯 What Is This?

A production-ready CLI tool that extracts YouTube videos into AI-enhanced Obsidian notes with intelligent pattern selection, smart caching, and incremental updates.

**One command does everything:**
```bash
ytobs "https://youtube.com/watch?v=VIDEO_ID"
```

---

## ⚡ Quick Verification (30 seconds)

```bash
# Test with short video (19 seconds)
ytobs --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Run again - should SKIP instantly (cache working)
ytobs "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# Expected: ⏭️ SKIPPED: Note already exists
```

---

## 📚 Navigation (Where to Look)

| Task | Document |
|------|----------|
| **Understand full context** | [CONTEXT.md](CONTEXT.md) - Complete history, decisions, current state |
| **Run/debug the pipeline** | [docs/AGENTIC_GRAPH.md](docs/AGENTIC_GRAPH.md) - Execution graph, model routing, breakage tree |
| **Exact model limits** | [docs/MODEL_CONTEXT_LIMITS.md](docs/MODEL_CONTEXT_LIMITS.md) - Verified context windows + sources |
| **Vault operations** | [docs/RUNBOOK.md](docs/RUNBOOK.md) - Retro/dedupe procedures, quota playbook |
| **What's next / resume work** | [docs/plans/YTOBS_MASTERPLAN.md](docs/plans/YTOBS_MASTERPLAN.md) - Work queue with checkboxes |
| **User documentation** | [README.md](README.md) - How to use the tool |
| **Installation** | [SETUP.md](SETUP.md) - Setup instructions |

---

## 🚀 Current State (V4.1.0 + Gas Overhaul 2026-09-05)

**Model chain (the gas):**
- `go` (default) = mimo-v2.5 via **direct OpenAI-compatible API** to OpenCode
  Go — ~$0.03/curated note, 1M ctx, English-guarded
- Fallbacks: `gofree` (nemotron-3-ultra-free, $0) → `gofabric` (mimo via
  fabric-LiteLLM) → `fast`/`quality` (Groq, 8K TPM cliff)
- `goflash` = glm-5.3-flash, small-output tasks ONLY (over-reasons on big
  extraction patterns)
- Lusófona (`pt` amalia-9b): DEAD (endpoint 503)

**Implemented & Working:**
- ✅ Direct streaming adapter (`OpenAICompatAdapter`) + fabric pattern library
- ✅ Smart cache prevents duplicate processing
- ✅ Incremental pattern addition (`--append`) with `pattern_runs` provenance
- ✅ Curated default mode (`extract_wisdom` + `summarize`)
- ✅ Model provenance per pattern section (`*Model: X · date*` lines)
- ✅ Fenced transcripts + refinement layer
- ✅ `ytobs retro` / `ytobs dedupe` / `ytobs patterns` / `ytobs status` / `ytobs vault`

**Key Commands:**
```bash
ytobs "URL"                              # Smart analysis (default)
ytobs --quick "URL"                      # Fast (5 patterns, ~25s)
ytobs --deep "URL"                       # Complete (all patterns, ~70s)
ytobs "URL" --append --patterns X Y      # Add patterns to existing note
ytobs "URL" --force                      # Re-run (ignore cache)
ytobs --list-processed                   # Show all cached videos
```

**Cache Location:**
- `$OBSVAULT/youtube/.cache/`
- Per-video JSON files with processing history
- Instant skip on re-run (0.1s, 0 API calls)

---

## 🎓 Project Evolution

| Version | Date | Key Feature |
|---------|------|-------------|
| V1.0 | 2025-12-08 | Initial: Metadata + transcript extraction |
| V1.5 | 2025-12-08 | Fabric AI integration (2-phase orchestration) |
| V2.0 | 2025-12-09 | Simplified interface (unified `yt` command) |
| V2.1 | 2025-12-09 | Rate limiting + multi-model fallback |
| V3.0 | 2025-12-09 | Smart cache + incremental updates |
| V4.0 | 2025-12-17 | VideoContext packet enrichment, status/vault commands |
| V4.0 pkg | 2026 | Extracted to hub/ytobs as pip-installable package |
| V4.1.0 | 2026-09-03 | Curation layer: retro, dedupe, refinement, provenance |
| **Gas overhaul** | **2026-09-05** | **Direct OpenCode Go transport, mimo-v2.5 chain, verified limits** |

---

## 🔧 Common Development Tasks

### Fixing Bugs
1. Read CONTEXT.md → Find "Known Issues" or relevant section
2. Check recent session logs at end of CONTEXT.md
3. Review relevant architecture doc in docs/architecture/
4. Make changes, test with short video

### Adding Features
1. Check docs/architecture/future-multi-provider.md for roadmap
2. Review the V4.1.0 session entry in CONTEXT.md as example
3. Create new docs/architecture/v3.X-feature-name.md if major
4. Update CONTEXT.md session log when complete

### Testing
```bash
# Short video (fast iteration)
ytobs --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Long video (stress test)
ytobs --quick "https://www.youtube.com/watch?v=ugvHCXCOmm4"

# Cache behavior
ytobs "URL"          # First run
ytobs "URL"          # Should skip
ytobs "URL" --force  # Should re-run
```

---

## 📊 Project Statistics

**Code:**
- ~20 Python modules in the `ytobs/` package (pip-installable)
- Curation layer (V4.1): `retro.py`, `dedupe.py`, `frontmatter_editor.py`, `transcript_refiner.py`

**Performance:**
- First run: 50 API calls, ~50s
- Cache skip: 0 calls, 0.1s ✅ 500x faster!
- Incremental append: ~10s vs 50s full re-run

**Documentation:**
- 10+ architecture/design docs
- 3 developer guides
- Complete session history in CONTEXT.md

---

## 🧠 Multi-Session Context Strategy

**This project uses a 3-tier documentation system:**

1. **START_HERE.md** (this file) - Quick orientation
2. **CONTEXT.md** - Complete historical record
3. **docs/** - Reference documentation by category

**For new AI agent sessions:**
- Start here for overview
- Read CONTEXT.md for full context
- Check docs/ for specific technical details
- Update CONTEXT.md when work is complete

---

## 🚨 Critical Files (Never Delete)

- `CONTEXT.md` - Project memory
- `ytobs/cli.py` - Main CLI interface
- `ytobs/backend_adapter.py` - Transport layer (direct API + fabric adapters)
- `ytobs/cache_manager.py` - Cache core
- `ytobs/fabric_orchestrator.py` - AI analysis engine
- `ytobs/frontmatter_editor.py` - Safe note editing core (V4.1)
- `config.yaml` - Configuration reference template (runtime: ~/.yt-obsidian/config.yml)

---

## 🔜 Next Steps

**Start from [docs/plans/YTOBS_MASTERPLAN.md](docs/plans/YTOBS_MASTERPLAN.md)** — the live work queue. Headline items:

1. Commit the 2026-09-05 gas overhaul (10 modified files)
2. Retro backlog on mimo: 65 targets (~$2 total); 37 need transcript re-fetch first
3. Append-fill-empty-headings improvement
4. Lusófona watchdog (passive)

See: docs/RUNBOOK.md (ops) and docs/AGENTIC_GRAPH.md (debug maps)

---

## 💡 Pro Tips

1. **Always test cache:** Run same video twice to verify skip
2. **Check cache contents:** `cat $OBSVAULT/youtube/.cache/index.json`
3. **Debug mode:** Add `--debug` flag to any command
4. **Clean slate:** `rm -rf $OBSVAULT/youtube/.cache` to reset
5. **Update this file:** When adding major features, update the "Current State" section

---

**Last Updated:** 2026-09-05  
**Maintained By:** AI-assisted development sessions  
**License:** MIT
