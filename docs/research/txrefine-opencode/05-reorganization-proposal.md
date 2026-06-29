# 05 — ytobs Project Reorganization Proposal

**Question answered**: How should the ytobs folder be reorganized?
**Principle**: Archive, never delete. Every idea is preserved.

---

## A. Current State Diagnosis

| Issue | Severity | Detail |
|-------|----------|--------|
| `CONTEXT.md` is a 28KB monolith | 🔴 High | Mixes project context + every session log. Hard to find current state. |
| Zero tests | 🔴 High | 20 modules, no test directory. |
| `extropics-yt.html` (48KB) in root | 🟡 Medium | Foreign web clipping, nothing to do with ytobs. |
| 3 overlapping help files | 🟡 Medium | `HELP.md` (23KB) + `HELP_SHORT.txt` (3.5KB) + `HELP_SUMMARY.txt` (3.8KB meta-note). |
| `requirements.txt` duplicates `pyproject.toml` | 🟢 Low | Superseded but harmless. |
| Empty placeholder dirs | 🟢 Low | `docs/design/`, `archive/deprecated/` exist but are empty. |
| Spec proliferation | 🟡 Medium | `DEEP_RESEARCH_REPORT.md` and `THREE_COMPONENT_ARCHITECTURE_SPEC.md` overlap heavily. |
| Session logs split between root and archive | 🟡 Medium | Some session logs in `CONTEXT.md`, some in `archive/sessions/`. |

---

## B. Proposed Structure

```
ytobs/
├── README.md                          # User-facing (keep, refresh)
├── START_HERE.md                      # AI agent entry (keep, refresh to V4.0+txrefine)
├── SETUP.md                           # Installation (keep as-is)
├── CONTRIBUTING.md                    # (keep)
├── LICENSE                            # (keep)
├── pyproject.toml                     # (keep — single source of deps)
├── config.yaml                        # (keep — template)
├── .gitignore                         # (update)
│
├── ytobs/                             # 🐍 Python package (UNCHANGED)
│   ├── __init__.py
│   ├── cli.py
│   ├── fabric_orchestrator.py
│   ├── transcript_refiner.py          # 🆕 (when txrefine lands)
│   ├── packet_builder.py
│   ├── chunker.py
│   ├── transcript.py
│   ├── extractor.py
│   ├── formatter.py
│   ├── cache_manager.py
│   ├── incremental_writer.py
│   ├── metadata_extractor.py
│   ├── rate_limiter.py
│   ├── token_counter.py
│   ├── status_display.py
│   ├── channel.py
│   ├── config.py
│   ├── validator.py
│   ├── filesystem.py
│   ├── markdown_utils.py
│   └── exceptions.py
│
├── help/                              # 🆕 Consolidated help (was 3 files at root)
│   ├── HELP.md                        # Full reference (moved from root)
│   └── HELP_SHORT.txt                 # Concise (moved from root)
│   # HELP_SUMMARY.txt → archived (was just a meta-note)
│
├── docs/                              # 📚 Curated documentation
│   ├── README.md                      # 🆕 Docs index + navigation
│   │
│   ├── architecture/                  # System design by version
│   │   ├── current.md                 # 🆕 V4.0 current-state summary
│   │   ├── v2.1-multi-model-fallback.md   # (keep)
│   │   ├── v3.0-smart-cache-vision.md     # (keep)
│   │   └── future-multi-provider.md       # (keep)
│   │
│   ├── development/                   # Developer guides + specs
│   │   ├── PACKET_ENRICHMENT_SPEC.md      # (keep — V4.0 master spec)
│   │   ├── developer-guide.md             # 🆕 Merged from v2.1 + v3.0 guides
│   │   ├── EXTRACT_PATTERNS_ENGINE_SPEC.md # (keep)
│   │   └── THREE_COMPONENT_ARCHITECTURE_SPEC.md # (keep)
│   │
│   ├── design/                        # Design decisions + research
│   │   ├── ARCHITECTURE.md                # (moved from docs/ root)
│   │   ├── OBSIDIAN_SCHEMA.md             # (moved from docs/ root)
│   │   ├── TECHNOLOGY_DECISION.md         # (moved from docs/ root)
│   │   ├── FABRIC_ORCHESTRATION_FRAMEWORK.md # (moved from docs/ root)
│   │   └── PROMPT_INJECTION_STRATEGY.md   # (moved from docs/ root)
│   │
│   └── research/                      # 🆕 Research folders (like this one)
│       └── txrefine-opencode/         # ← You are here
│           ├── README.md
│           ├── 01-current-state.md
│           ├── 02-opencode-vs-fabric.md
│           ├── 03-research-findings.md
│           ├── 04-integration-design.md
│           └── 05-reorganization-proposal.md
│
├── reference/                         # External reference material
│   ├── yt-dlp-practical-command-reference.md  # (keep)
│   ├── ideia-original.md              # 🆕 Renamed from ideia-dot-myscripts-...
│   └── extropics-yt-article.html      # 🆕 Moved from root (foreign artifact)
│
├── experiments/                       # 🆕 Test scripts for txrefine A/B
│   ├── txrefine_compare.sh            # (from Doc 02)
│   ├── metrics.py                     # (from Doc 02)
│   └── results/                       # gitignored
│
├── tests/                             # 🆕 (CRITICAL GAP — zero tests today)
│   ├── __init__.py
│   ├── test_transcript_refiner.py     # txrefine unit tests
│   ├── test_chunker.py
│   ├── test_packet_builder.py
│   └── test_cache_manager.py
│
└── archive/                           # 📦 Historical (never delete, rarely visit)
    ├── CONTEXT_HISTORY.md             # 🆕 Session logs extracted from CONTEXT.md
    ├── HANDOFF_ytobs_extraction.md    # (keep)
    ├── md-html.py                     # (keep — unrelated utility)
    ├── HELP_SUMMARY.txt               # (moved from root)
    ├── requirements.txt               # (moved from root — pyproject.toml supersedes)
    ├── AUDIT_REPORT.md                # (moved from root — one-off audit)
    │
    └── sessions/                      # (keep all existing)
        ├── BUGFIX_LONG_VIDEOS.md
        ├── HANDOFF.md
        ├── NEXT_PHASE_REQUIREMENTS.md
        ├── RATE_LIMIT_ANALYSIS.md
        ├── README_REPO_HEADER.md
        ├── REPO_READY.md
        ├── SESSION_COMPLETE.md
        ├── DEEP_RESEARCH_REPORT.md   # 🆕 Moved here (superseded by THREE_COMPONENT)
        ├── PHASE1_IMPLEMENTATION_PLAN.md # 🆕 Moved from docs/ (completed phase)
        ├── PHASE1C_FABRIC_INTEGRATION.md # 🆕 Moved from docs/ (completed phase)
        ├── TRANSCRIPT_IMPLEMENTATION_PLAN.md # 🆕 Moved from docs/ (completed)
        └── TRANSCRIPT_RESEARCH.md    # 🆕 Moved from docs/ (yt-dlp API ref, stable)
```

---

## C. The CONTEXT.md Split (Most Important Change)

`CONTEXT.md` currently does two jobs badly:
1. **Project context** (what is this, current state, architecture) — should be lean
2. **Session history** (every session log ever) — should be archived

### Proposed Split

**Keep `CONTEXT.md` lean (~3-5KB)** — project identity, current version, architecture summary, links to docs. No session logs. Like a `PROJECT.md` you'd hand to a new contributor.

**Move all session logs to `archive/CONTEXT_HISTORY.md`** — the existing session log content, preserved verbatim. Append future session logs there.

This means:
- `START_HERE.md` → quick orientation (unchanged role)
- `CONTEXT.md` → lean current-state (dieted from 28KB to ~5KB)
- `archive/CONTEXT_HISTORY.md` → full history (the 23KB of session logs)

---

## D. Migration Script (Safe, Reversible)

**Don't do this manually.** Use git so every move is reversible.

```bash
#!/bin/bash
# reorganize.sh — PROPOSED, review before running
# Run from ytobs root. All moves via git mv for traceability.

set -e

# 1. Consolidate help
mkdir -p help
git mv HELP.md help/HELP.md
git mv HELP_SHORT.txt help/HELP_SHORT.txt
git mv HELP_SUMMARY.txt archive/HELP_SUMMARY.txt

# 2. Move foreign artifact
git mv extropics-yt.html reference/extropics-yt-article.html

# 3. Move completed-phase docs to archive
git mv docs/PHASE1_IMPLEMENTATION_PLAN.md archive/sessions/
git mv docs/PHASE1C_FABRIC_INTEGRATION.md archive/sessions/
git mv docs/TRANSCRIPT_IMPLEMENTATION_PLAN.md archive/sessions/
git mv docs/TRANSCRIPT_RESEARCH.md archive/sessions/
git mv docs/development/DEEP_RESEARCH_REPORT.md archive/sessions/

# 4. Reorganize docs/ root into design/
# (ARCHITECTURE.md, OBSIDIAN_SCHEMA.md, TECHNOLOGY_DECISION.md,
#  FABRIC_ORCHESTRATION_FRAMEWORK.md, PROMPT_INJECTION_STRATEGY.md)
# → docs/design/

# 5. Move superseded files
git mv requirements.txt archive/
git mv AUDIT_REPORT.md archive/

# 6. Remove empty placeholder dirs
rmdir docs/design 2>/dev/null || true  # will be repopulated
rmdir archive/deprecated 2>/dev/null || true

# 7. Split CONTEXT.md (MANUAL — requires judgment)
echo "TODO: Manually split CONTEXT.md"
echo "  - Lean context → CONTEXT.md (~5KB)"
echo "  - Session logs → archive/CONTEXT_HISTORY.md (~23KB)"

# 8. Update internal links
echo "TODO: Update markdown links in START_HERE.md, README.md, docs/README.md"

echo "Done. Review with: git status && git diff --stat"
```

---

## E. What NOT to Change

| Keep As-Is | Reason |
|------------|--------|
| `ytobs/` package code | Working, don't touch during reorg |
| `config.yaml` | Template, working |
| `pyproject.toml` | Source of truth for deps |
| `archive/sessions/*` | Historical, preserved |
| `reference/yt-dlp-practical-command-reference.md` | Useful reference |
| `docs/development/PACKET_ENRICHMENT_SPEC.md` | Master spec, still active |
| `docs/research/txrefine-opencode/` | (This folder — just created) |

---

## F. Priority Order

If you only do 3 things:

1. **Move `extropics-yt.html` out of root** (1 min, zero risk)
2. **Create `tests/` directory** (the real gap — start with `test_transcript_refiner.py`)
3. **Split `CONTEXT.md`** (30 min, biggest navigability win)

The rest is nice-to-have tidying. Don't let reorganization block the actual txrefine work.

---

## G. Long-Term Vision: ytobs as a Content Refinement Platform

The folder reorganization isn't just tidying — it sets up ytobs to be the **home for a general content-refinement primitive**, not just a YouTube tool. Consider:

```
ytobs/                          # Today: YouTube → Obsidian
  └── (current structure)

# Future (same refine() primitive, new frontends):
podobs/                         # Podcast → Obsidian (same ytobs internals, different source)
filmobs/                        # Film/lecture → Obsidian
voiceobs/                       # Voice note → Obsidian (already partially exists as voice_note.sh)

# Or: one tool, many sources
mediaobs/
  ├── sources/
  │   ├── youtube.py            # (current ytobs extractor)
  │   ├── podcast.py            # RSS → audio → whisper
  │   ├── film.py               # subtitle extraction
  │   └── voice.py              # local audio → whisper
  ├── refine/                   # ← txrefine lives HERE (shared)
  │   ├── transcript_refiner.py
  │   ├── patterns/
  │   └── prompts/
  └── analyze/                  # Fabric/OpenCode patterns (shared)
```

The txrefine module you build today becomes the **shared refinement layer** across all future content sources. Build it clean, backend-agnostic, and well-tested — it'll outlive ytobs itself.

This is why the reorganization matters: it creates the structural space for txrefine to be a first-class citizen, not buried inside a YouTube-specific tool.
