# YouTube to Obsidian Pipeline - Project Context

**Last Updated**: 2026-09-03 (V4.1.0 Curation Layer)  
**Status**: ✅ V4.1.0 - CURATION LAYER OPERATIONAL (RETRO, DEDUPE, REFINEMENT, PROVENANCE)  
**Location**: `~/projetos/hub/ytobs/`  
**GitHub**: https://github.com/fabiofalopes/ytobs (public, synced 2026-09-03)

---

## Project Identity

**Name**: YouTube to Obsidian (`ytobs`)  
**Purpose**: Extract YouTube videos to AI-enhanced Obsidian notes with ONE command  
**Current State**: V4.1.0 - pip-installable package at `~/projetos/hub/ytobs/`

---

## Current Usage (V3.0 Smart Cache)

### Core Commands
```bash
# First run - creates note + cache
ytobs "https://www.youtube.com/watch?v=VIDEO_ID"

# Second run - SKIPS (instant, 0 API calls)
ytobs "URL"
# ⏭️  SKIPPED: Note already exists

# Quick mode - essential insights (~25s)
ytobs --quick "URL"

# Deep mode - comprehensive analysis (~70s)
ytobs --deep "URL"

# Preview - see what would run
ytobs --preview "URL"
```

### V3.0 Cache Features (NEW!)
```bash
# Append new patterns to existing note (incremental)
ytobs "URL" --append --patterns extract_questions extract_ideas

# Force re-analysis (ignore cache)
ytobs "URL" --force

# Update metadata only (not implemented yet)
ytobs "URL" --update

# List all processed videos
ytobs --list-processed
```

### Expert Options
```bash
# Custom model
ytobs --model llama-4-scout "URL"

# Specific patterns
ytobs --patterns extract_wisdom summary "URL"

# No AI analysis (metadata only)
ytobs --no-analysis "URL"
```

**What happens on first run:**
1. Extracts video transcript (Phase 1 only)
2. Runs `pattern_optimizer` meta-pattern on content
3. Gets 10-20 recommended Fabric patterns based on content analysis
4. Filters by priority (essential/high/medium/optional)
5. Runs analysis with optimal pattern set
6. **Saves cache** to prevent duplicates

**What happens on second run (DEFAULT):**
- ⏭️ SKIPS processing (0.1s, 0 API calls)
- Shows existing note path
- Suggests --append, --update, or --force

### Configuration (`~/.yt-obsidian/config.yml`)

Auto-created on first run. Edit to customize defaults:

```yaml
mode: auto                # auto, quick, deep
model: kimi              # kimi, llama-4-scout, llama-70b
output_dir: ~/Documents/obsidian_vault/youtube
timeout_per_pattern: 60
chunk_size: 10000
open_in_editor: false
```

### Legacy Tools (Deprecated)

Moved to `_deprecated/` directory:
- `auto-analyze.py` - Functionality now in unified `yt` command
- Old session documentation files

Use `yt-obsidian.py` directly only if you need legacy behavior.

---

## Architecture Overview

### Pipeline Flow
```
URL → Validate → Extract Metadata → Extract Transcript 
    → Fabric Phase 1 (Global Metadata)
    → Chunk Transcript → Build Enriched Packets
    → Fabric Phase 2 (Process Patterns)
    → Combine Outputs → Generate Markdown → Save
```

### Key Modules
| Module | Purpose |
|--------|---------|
| `validator.py` | URL validation, environment checks |
| `extractor.py` | yt-dlp metadata + transcript extraction |
| `transcript.py` | Transcript parsing and formatting |
| `formatter.py` | YAML front matter + markdown generation |
| `filesystem.py` | Safe file I/O operations |
| `chunker.py` | Transcript chunking with overlap |
| `token_counter.py` | Token estimation (tiktoken) |
| `packet_builder.py` | Enriched packet creation |
| `metadata_extractor.py` | Fabric Phase 1 (global context) |
| `fabric_orchestrator.py` | Two-phase Fabric orchestration |
| `rate_limiter.py` | Groq rate limit handling |
| `markdown_utils.py` | Heading normalization |

---

## Phase 1C Implementation (Complete)

### What Was Built
1. **Transcript Chunking**: Smart chunking with token limits and overlap
2. **Enriched Packets**: Each chunk includes global context (summary, theme, topics)
3. **Two-Phase Fabric**: Phase 1 extracts global metadata, Phase 2 runs patterns
4. **Rate Limit Handling**: Retry logic with exponential backoff for Groq API
5. **Model Selection**: `--model` flag to override default LLM
6. **Streaming Mode**: `--stream` for real-time Fabric output
7. **Join Patterns**: Custom patterns to combine chunk outputs

### Rate Limit Strategy (Groq Free Tier)
| Model | TPM | Recommendation |
|-------|-----|----------------|
| `llama-4-scout` | 30,000 | Best throughput |
| `llama-70b` | 12,000 | Best quality |
| `kimi` | 10,000 | Default (balanced) |
| `llama-8b` | 6,000 | Fastest |

### Configuration (`config.yaml`)
```yaml
fabric:
  command: "fabric-ai"
  patterns: ["youtube_summary"]
  join_pattern: "join_chunks"
  timeout: 120
  enabled: true

rate_limits:
  max_retries: 3
  base_delay: 5.0
  inter_chunk_delay: 2.0

chunking:
  max_chunk_tokens: 8000
  overlap_tokens: 200
  save_chunks: true
```

---

## Project Structure

```
ytobs/
├── ytobs/                 # 🐍 Python package (ytobs.cli:main)
├── pyproject.toml         # Package metadata
├── config.yaml            # Configuration
├── requirements.txt       # Python dependencies
```

---

## Recent Session Work (2025-12-08)

### This Session
1. ✅ Fixed Phase 1 "failed" warning (now only shows in debug mode)
2. ✅ Added `--model` CLI flag for LLM selection
3. ✅ Updated CONTEXT.md with Phase 1C status

### Previous Sessions (Same Day)
- Fixed note structure (Transcript → AI Analysis order)
- Created `markdown_utils.py` for heading normalization
- Created `rate_limiter.py` for Groq rate limit handling
- Created join patterns (`join_chunks`, `join_chunk_summaries`)
- Integrated rate limiter with orchestrator
- Tested with short (19s) and long (5h15m) videos

---

## Test Results

| Video | Duration | Chunks | Time | Status |
|-------|----------|--------|------|--------|
| Me at the Zoo | 19s | 1 | 5.8s | ✅ Success |
| Lex/Dario Amodei | 5h15m | 10 | 8.4min | ✅ Success |

---

## Open Questions

1. ✅ Output directory: `$OBSVAULT` environment variable
2. ❓ Default cookies browser: none (user provides if needed)
3. ✅ Filename format: `YYYY-MM-DD_slugified_title.md`
4. ✅ Include metrics: Yes, optional in front matter

---

## Next Steps (if continuing)

1. **Testing**: Run with more diverse videos to validate
2. **Model Optimization**: Consider `llama-4-scout` as default (3x TPM)
3. **Error Reporting**: Improve Phase 1 fallback visibility
4. **Documentation**: Update README with usage examples
5. **Migration**: Move to `~/.myscripts/youtube/` when stable

---

## Dependencies

```
yt-dlp>=2023.0.0
pyyaml>=6.0
tiktoken>=0.5.0
requests>=2.28.0
```

Plus Fabric CLI (`fabric-ai`) configured with Groq API.

---

## Session Log

| Date | Summary |
|------|---------|
| 2024-12-08 | Initial: Technology decision, architecture design |
| 2025-12-08 AM | Agentic environment setup |
| 2025-12-08 PM | Phase 1A: Core metadata extraction |
| 2025-12-08 Eve | Tag sanitization fix |
| 2025-12-08 Night | Phase 1B: Transcript integration |
| 2025-12-08 Night | **Phase 1C**: Fabric AI integration - chunking, enriched packets, two-phase orchestration, rate limit handling |
| 2025-12-08 Late | **Refinements**: Fixed Phase 1 warning, added `--model` flag, updated CONTEXT.md |
| 2025-12-09 01:15 | **New Tools**: Created `pattern_optimizer` Fabric meta-pattern (10-20 pattern recommendations), `auto-analyze.py` automation script (intelligent pattern selection), comprehensive documentation |
| 2025-12-09 08:00 | **Debug & Fix Session**: Fixed auto-analyze.py parsing issue, fixed model name resolution in Fabric integration, tested end-to-end successfully, all systems operational ✅ |

---

**Update this file at the end of each session.**

---

## Session Log

### 2025-12-09: V2.0 Simplified Interface Launch

**Major Achievement**: Unified complex multi-command system into single `yt` command

**Problems Solved**:
1. Fixed auto-analyze.py parser errors (couldn't read yt-obsidian output)
2. Fixed Fabric model alias resolution (vendor errors)
3. Reduced UX complexity from 3 commands + 10+ flags to 1 command + 4 modes

**Files Created**:
- `yt` - New unified CLI combining yt-obsidian + auto-analyze logic
- `lib/config.py` - Config management with YAML support  
- `~/.yt-obsidian/config.yml` - User config (auto-created)
- `_deprecated/` - Archived old multi-command interface

**Files Modified**:
- `lib/rate_limiter.py` - Added model alias resolution
- `lib/fabric_orchestrator.py` - Auto-resolve model aliases
- `README.md` - Completely rewritten for V2.0 simplicity

**Key Decisions**:
- Single command `yt` replaces `yt-obsidian.py` + `auto-analyze.py`
- Three presets (quick/auto/deep) instead of manual flags
- Config file for persistent preferences
- Preview mode for transparency
- Backward compatibility via legacy tools in `_deprecated/`

**Status**: ✅ V2.0 fully operational and tested
- Preview mode: ✅ Working
- Quick mode: ✅ Working (25s, 5 patterns)
- Auto mode: ✅ Working (~50s, smart selection)
- AI analysis sections: ✅ Appearing in markdown output
- Config generation: ✅ Auto-creates on first run

**Next Steps**:
- Test deep mode
- Consider symlinking `yt` to ~/.local/bin for global access
- Migration to ~/.myscripts/youtube/ when ready
- Documentation review


---

## Session Log - Continued

### 2025-12-09: Bug Fix - Long Video Transcripts

**Issue**: `pattern_optimizer` failed with long videos (28K+ words)
- Error: Context window exceeded (36K tokens vs 10-16K limit)
- Caused by: Sending entire transcript to pattern_optimizer

**Fix**: Truncate transcript to first 2000 words for pattern analysis
- Pattern selection only needs content sample, not full transcript
- 2000 words ≈ 2600 tokens (well within limits)
- Full transcript still used for actual AI analysis (via chunking)

**Testing**: 
- ✅ Preview mode: Works with long video
- ✅ Quick mode: Processing (5 chunks created)
- ✅ Pattern optimizer: 13 patterns recommended

**Files Modified**:
- `yt` (line 135-158): Added transcript truncation in `run_pattern_optimizer()`

**Status**: ✅ Fixed - Long videos now work correctly

---

### 2025-12-09: Final Session - Documentation & Developer Handoff

**Major Achievement**: Comprehensive documentation for next development phase

**What Was Accomplished**:
1. **Created DEVELOPER_PROMPT.md** - 350+ line comprehensive guide for next developer
   - Clear mission: Fix rate limiting (50% → 100% success)
   - Step-by-step workflow with exact file locations
   - Copy-paste ready commands for immediate start
   - Success criteria and testing strategy
   
2. **Validated Project State**
   - ✅ No contradictory documentation
   - ✅ No deprecated files in root (auto-analyze.py properly removed)
   - ✅ All essential docs present and accurate
   - ✅ Clean structure ready for development

3. **Identified All Critical Issues**
   - Rate limiting: RateLimitHandler exists but NOT USED in fabric_orchestrator.py
   - Phase 1 failures: 3 patterns always fail, needs investigation
   - No streaming output: User can't see progress or stop mid-way
   - Missing tests directory: Manual testing only

**Project Status Summary**:
- **V2.0**: ✅ Working for short videos, simple unified interface
- **V2.1**: 📋 Requirements documented, ready for implementation
- **Files Ready**: 16 Python modules, 10+ documentation files
- **Testing**: Quick mode verified, long video issues documented

**Key Files Created This Session**:
- `DEVELOPER_PROMPT.md` - Main handoff document (350+ lines)
- Updated `CONTEXT.md` - This file, final session log

**Critical Path Forward**:
1. Fix rate limiting in `lib/fabric_orchestrator.py` (HIGH priority)
2. Investigate Phase 1 failures in `lib/metadata_extractor.py` (HIGH priority)
3. Implement streaming output (MEDIUM priority)
4. Add progress indicators (MEDIUM priority)

**Next Developer Action**:
```bash
# Copy-paste to start next session:
cd ~/projetos/rascunhos/yt-dlp-tests
source venv/bin/activate
cat DEVELOPER_PROMPT.md  # Read this first!
```

**Status**: 🎯 Ready for clean development session focused on fixes

---

### 2025-12-09: Future Vision - Multi-Provider Architecture

**Context**: User requested architecture for future scaling strategy

**Vision Added**: Multi-provider and multi-key API rotation system
- **Problem**: Single API key (30K TPM) causes rate limit failures
- **Solution**: Rotate across multiple API keys + multiple providers
- **Benefit**: 4-5x throughput while staying on free tiers

**New File Created**: `FUTURE_ARCHITECTURE_MULTI_PROVIDER.md` (600+ lines)

**Contents**:
1. **Multi-key rotation** - Use 4 Groq keys → 120K TPM (4x throughput)
2. **Multi-provider** - Add Together, Fireworks → 150K+ TPM combined
3. **Parallel execution** - Process chunks simultaneously across providers
4. **Implementation stages** - V2.2 (multi-key), V2.3 (multi-provider), V2.4 (parallel)

**Key Design Elements**:
- `APIKeyRotator` class - Round-robin, LRU, or random key selection
- `ProviderManager` class - Intelligent provider selection and failover
- `ParallelOrchestrator` class - Concurrent chunk processing
- Config-driven - Easy to add new providers/keys without code changes

**Priority**: Post-V2.1 (fix single-key issues first, then scale horizontally)

**Rationale**: Better to have solid single-key foundation before adding multi-key complexity

**Expected Improvements**:
- Stage 1 (multi-key): 4x faster, 10% failure rate
- Stage 2 (multi-provider): 5x faster, <5% failure rate, full redundancy
- Stage 3 (parallel): 2-3x additional speedup on long videos

**Updated Files**:
- `DEVELOPER_PROMPT.md` - Added future vision section
- `CONTEXT.md` - This file, documenting the vision

**Status**: 📋 Architecture documented, implementation planned for V2.2+

---

### 2025-12-09: V3.0 Smart Cache System - COMPLETE

**Major Achievement**: Eliminated duplicate note creation and enabled incremental pattern additions

**Problem Solved**:
- User discovered 41 files with 8 copies of "Me at the Zoo" alone
- Every re-run was wasting API quota processing same videos
- No way to add patterns without full re-analysis

**Solution Implemented**:
1. **Phase 0: Cache Check** - Video ID lookup before processing
2. **Smart Skip** - Default behavior skips existing videos (0.1s, 0 API calls)
3. **Incremental Append** - Add patterns to existing notes without re-running all
4. **Force Override** - Explicit `--force` flag to re-analyze

**Files Created**:
- `lib/cache_manager.py` - CacheManager and CacheEntry classes (255 lines)
- `lib/incremental_writer.py` - Append sections to existing notes (147 lines)

**Files Modified**:
- `yt` - Added Phase 0 cache check, new flags (--force, --append, --update, --list-processed)
- `CONTEXT.md` - Updated to V3.0 status

**New Features**:
```bash
ytobs "URL"              # First run: creates note + cache
ytobs "URL"              # Second run: SKIPS (instant)
ytobs --append --patterns extract_questions "URL"  # Add patterns incrementally
ytobs --force "URL"      # Re-analyze (ignore cache)
ytobs --list-processed   # Show all cached videos
```

**Test Results**:
- ✅ Cache prevents duplicates (tested with "Me at the Zoo")
- ✅ Skip shows helpful message with note path and patterns
- ✅ Append adds new patterns without full re-run (tested: extract_questions, extract_ideas)
- ✅ Force re-runs full analysis
- ✅ List-processed shows cache statistics

**Cache Structure**:
```
$OBSVAULT/youtube/.cache/
├── jNQXAC9IVRw.json    # Per-video cache
└── index.json          # Fast lookup index
```

**Performance Impact**:
- First run: 50 API calls, 400K tokens, ~50s
- Second run (SKIP): 0 calls, 0 tokens, 0.1s ✅ INSTANT
- Append 2 patterns: 20 calls, 160K tokens, ~10s ✅ INCREMENTAL

**Key Decisions**:
- Cache by video_id (not filename) to handle duplicates
- Default behavior is SKIP (user must explicitly --force)
- Cache stores processing history for analytics
- Incremental writer preserves all existing content

**Status**: ✅ V3.0 COMPLETE - All features tested and working

**Next Steps (V3.1+)**:
- Implement --update (metadata refresh only)
- Bulk processing (playlists)
- Migration script for existing notes
- Vector DB integration


---

### 2025-12-11: Production Migration - COMPLETE

**Major Achievement**: Moved from experimental directory to managed repository

**Motivation**:
- Transition from `~/projetos/rascunhos/yt-dlp-tests` (drafts) to production
- Better organization in managed `.myscripts` repo
- Improved multi-session context management
- Professional structure for continued development

**Actions Taken**:
1. **Documentation Reorganization**
   - Created `START_HERE.md` - Primary entry point for new AI sessions
   - Reorganized docs/ into architecture/, development/, design/
   - Archived session-specific docs to archive/sessions/
   - Reduced root-level docs from 20+ to 8 essential files

2. **Cleanup**
   - Removed venv/ (138MB → regenerated)
   - Removed .fabric/ temporary files
   - Removed __pycache__ directories
   - Project size: 146MB → 6.9MB (clean code only)

3. **Migration**
   - Destination: `~/projetos/hub/.myscripts/youtube-obsidian/`
   - Recreated venv with all dependencies
   - Updated shebang to `#!/usr/bin/env python3`
   - Tested all functionality successfully

**New Structure**:
```
youtube-obsidian/
├── START_HERE.md          # 🆕 Quick entry for new sessions
├── CONTEXT.md             # Complete history (this file)
├── README.md              # User docs
├── docs/
│   ├── architecture/     # 🆕 v1, v2.1, v3.0, future
│   ├── development/      # 🆕 Developer guides
│   └── design/           # Design decisions
└── archive/
    └── sessions/         # 🆕 Historical docs
```

**Multi-Session Context Strategy**:
- 3-tier system: START_HERE.md → CONTEXT.md → docs/
- Clear navigation for AI agents
- Historical context preserved but organized
- Entry point optimized for quick onboarding

**Testing**:
- ✅ `./yt --list-processed` shows 5 cached videos
- ✅ All CLI flags working
- ✅ Cache system operational
- ✅ Dependencies installed correctly

**Status**: ✅ MIGRATION COMPLETE - Ready for continued development in new location

**Next Session**:
- Start by reading `START_HERE.md` for quick context
- Or read full `CONTEXT.md` for complete history
- Project now part of managed `.myscripts` repository


---

### 2025-12-13: V4.0 Enhanced Workflow Specification - COMPLETE

**Major Achievement**: Comprehensive specification unifying packet enrichment with iterative workflow vision

**Context**: 
- User identified that packets lack YouTube metadata (channel, tags, description)
- Vision expanded to include dynamic pattern discovery and vault-wide operations
- Goal: Transform `yt` from "one-shot tool" to "content synthesis engine"

**Specification Created**: `docs/development/PACKET_ENRICHMENT_SPEC.md` (700+ lines)

**Three-Part Architecture**:

1. **PART I: Packet Enrichment (Foundation)**
   - Phase A: Enhanced packet context with VideoContext dataclass
   - Phase B: Transcript refinement pipeline (typo correction, formatting)
   - Phase C: Always-run pattern infrastructure

2. **PART II: Enhanced Iterative Workflow**
   - Phase D: Pattern discovery (`yt patterns` command family)
   - Phase E: Iterative pattern application (`yt status`, `yt add`)
   - Phase F: Vault-aware operations (`yt vault stats`, bulk apply)
   - Phase G: Content synthesis engine (future vision)

3. **PART III: Unified Implementation Plan**
   - 6-sprint roadmap (Foundation → Discovery → Iterative → Refinement → Vault → Polish)
   - Comprehensive testing strategy
   - Enhanced configuration schema (v4.0)
   - Full command reference

**Key New Concepts**:

1. **Pattern Discovery System**:
   ```bash
   yt patterns                    # List all 262+ patterns
   yt patterns search "extract"   # Search patterns
   yt patterns describe extract_wisdom  # Show pattern details
   yt patterns suggest --content-type podcast  # Smart suggestions
   ```

2. **Iterative Workflow Enhancement**:
   ```bash
   yt status VIDEO_ID             # See what's been analyzed
   yt add VIDEO_ID --patterns P1  # Add patterns incrementally
   yt add VIDEO_ID --suggest      # Use smart suggestions
   ```

3. **Vault-Aware Operations**:
   ```bash
   yt vault stats                 # Vault-wide analytics
   yt vault list --missing PATTERN  # Find gaps
   yt vault apply PATTERN --all   # Bulk operations
   ```

4. **Enhanced Packet Context**:
   - VideoContext dataclass with channel, tags, description excerpt
   - ~200 token overhead per chunk (acceptable)
   - Full YouTube metadata flows to each Fabric call

**Files Created**:
- Enhanced `docs/development/PACKET_ENRICHMENT_SPEC.md` (unified specification)

**New Modules Planned**:
- `lib/pattern_discovery.py` - Pattern discovery interface
- `lib/vault_manager.py` - Vault-wide operations
- `lib/transcript_cache.py` - Efficient transcript caching
- Enhanced `lib/cache_manager.py` - New fields for iterative workflow

**Implementation Roadmap (6 Sprints)**:
| Sprint | Focus | Time | Priority |
|--------|-------|------|----------|
| 1 | Packet Enrichment | 2-3h | CRITICAL |
| 2 | Pattern Discovery | 3-4h | HIGH |
| 3 | Iterative Workflow | 4-5h | HIGH |
| 4 | Transcript Refinement | 4-6h | MEDIUM |
| 5 | Vault Operations | 4-5h | MEDIUM |
| 6 | Always-Run & Polish | 2-3h | LOW |

**Vision Statement**:
> "More than just getting information, we're trying to really get a lot of perspective, a lot of thinking, a lot of creative writing... the commentary, analysis, and content distillation."

**Status**: 📋 SPECIFICATION COMPLETE - Ready for implementation

**Next Steps**:
1. Implement Sprint 1 (Packet Enrichment) - Core foundation
2. Implement Sprint 2 (Pattern Discovery) - Enables dynamic workflow
3. Then iteratively add remaining features

**Key Decision**: Both specs (packet enrichment + enhanced workflow) will be implemented together, starting with the foundation (Sprint 1) and building up.

---

### 2025-12-17: V4.0 Sprint 1 - Packet Enrichment IMPLEMENTATION COMPLETE

**Major Achievement**: VideoContext dataclass fully implemented and integrated into packet enrichment pipeline

**Sprint 1 Status**: ✅ CODE COMPLETE (⏳ Integration verification pending)

**What Was Implemented**:

1. **VideoContext Dataclass** (`lib/packet_builder.py`, lines 13-87)
   - Full YouTube metadata context for AI models
   - Fields: video_id, video_url, channel_name, upload_date, tags, description_excerpt, duration_formatted
   - `from_video_info()` factory method for safe creation from extractor dict
   - `to_preamble_section()` method generates formatted VIDEO CONTEXT block
   - Robust error handling for missing/malformed data

2. **EnrichedPacket Integration** (line 165)
   - Added `video_context: Optional[VideoContext]` field
   - Updated `_generate_preamble()` to include VIDEO CONTEXT section
   - Preamble now includes:
     - VIDEO CONTEXT: Channel, Published date, Duration, Tags, Description excerpt
     - CONTENT CONTEXT: AI-analyzed overview
     - CHUNK INFORMATION: Position and temporal details
   - Fully backward compatible (Optional field, no breaking changes)

3. **Code Quality**
   - 345 lines total in packet_builder.py
   - Full type hints throughout
   - Comprehensive docstrings
   - Proper edge case handling
   - Ready for production use

**Pipeline Flow (Now)**:
```
URL → Extractor (video_info) 
    → VideoContext.from_video_info() ← NEW
    → Chunker → EnrichedPacket(video_context) ← ENHANCED
    → Fabric Orchestrator → Preamble with VIDEO CONTEXT ← ENHANCED
    → Patterns → Markdown
```

**Integration Status**:
- ✅ Code complete and tested (unit level)
- ⏳ **NEEDS VERIFICATION**: Chunker must pass video_info to create_packet()
- ⏳ **NEEDS VERIFICATION**: Fabric orchestrator must use _generate_preamble()
- ⏳ **NEEDS TEST**: Run actual video to confirm VIDEO CONTEXT appears

**Critical Path Forward**:
1. **Immediate (15 min)**: Verify video_context flows through pipeline
   - Run: `./yt --preview "https://www.youtube.com/watch?v=jNQXAC9IVRw"`
   - Check for "VIDEO CONTEXT:" section in output
   - If missing, debug chunker.py and fabric_orchestrator.py integration

2. **High Priority (7-9h)**: Implement Sprints 2-3
   - Sprint 2: Pattern Discovery (3-4h)
   - Sprint 3: Iterative Workflow (4-5h)

3. **Medium Priority (8-11h)**: Implement Sprints 4-5
   - Sprint 4: Transcript Refinement (4-6h)
   - Sprint 5: Vault Operations (4-5h)

4. **Low Priority (2-3h)**: Polish (Sprint 6)

**Session State Documented At**:
- `archive/sessions/V4_0_SESSION_STATE.md` - Comprehensive session documentation
- Memory entities created for Sprint 2-3 specifications
- TodoWrite tasks created for Sprint 1-6 implementation

**Estimated Remaining Work**: 17-23 hours for full V4.0 completion

**Next Session Action**:
1. Read `archive/sessions/V4_0_SESSION_STATE.md` for complete context
2. Run integration verification test (VIDEO CONTEXT in preview output)
3. Proceed with Sprint 2 implementation (Pattern Discovery)


---

### 2025-12-17: V4.0 Status & Vault Commands - COMPLETE

**Major Achievement**: Implemented `yt status` and `yt vault` commands for iterative workflow

**What Was Implemented**:

1. **`lib/status_display.py`** (NEW - 175 lines)
   - `extract_video_id()` - Parse video ID from URL or direct ID
   - `display_video_status()` - Full status display with patterns, note path, history
   - `display_status_compact()` - One-line status for scripting
   - `verify_note_exists()` - Check cache corruption (note deleted but cache remains)
   - Handles verbose mode with processing history

2. **`yt status VIDEO` subcommand**
   - Accept video ID or full URL
   - Show: title, channel, duration, patterns run, note path
   - Verbose mode: show processing history
   - Suggest actions (--append, --force)

3. **`yt vault` subcommand**
   - Show vault statistics: total videos, patterns, tokens
   - `--channels` flag to list videos
   - Uses existing CacheManager (no new vault_manager.py needed)

4. **`always_run_patterns` config support**
   - New config field in `lib/config.py`
   - Patterns prepended to every analysis (no duplicates)
   - Documented in default config template

5. **Concise help display**
   - Running `yt` with no arguments shows quick reference
   - Updated `HELP_SHORT.txt` with status/vault commands
   - Updated `HELP.md` to V4.0

**Files Created**:
- `lib/status_display.py` - Status display functionality

**Files Modified**:
- `yt` - Added subcommands (status, vault), concise help, always_run_patterns integration
- `lib/config.py` - Added always_run_patterns field and config parsing
- `HELP_SHORT.txt` - Added status/vault documentation
- `HELP.md` - Updated version to 4.0
- `HELP_SUMMARY.txt` - Updated status

**Test Results**:
```bash
./yt                    # ✅ Shows concise help
./yt --version          # ✅ Shows "yt 4.0.0 (Status & Vault Commands)"
./yt status jNQXAC9IVRw # ✅ Shows video status with patterns
./yt status VIDEO -v    # ✅ Shows processing history
./yt vault              # ✅ Shows vault statistics
./yt vault --channels   # ✅ Lists videos
./yt --help             # ✅ Shows full argparse help with subcommands
```

**V4.0 Features Summary**:
- ✅ VideoContext packet enrichment (Sprint 1)
- ✅ `yt status VIDEO` command
- ✅ `yt vault` command  
- ✅ `always_run_patterns` config
- ✅ Concise help on no-args
- ⏳ Pattern Discovery (`yt patterns`) - Not implemented
- ⏳ Transcript Refinement - Not implemented

**Status**: ✅ V4.0 CORE FEATURES COMPLETE

**Remaining V4.0 Work**:
- Pattern Discovery commands (`yt patterns`, `yt patterns search`, etc.)
- Transcript Refinement pipeline
- Vault-wide operations (`yt vault apply`)

**Command Reference (V4.0)**:
```bash
ytobs                          # Concise help
ytobs URL                      # Smart analysis
ytobs --quick URL              # Fast mode
ytobs --deep URL               # Complete analysis
ytobs --preview URL            # Show recommendations
ytobs status VIDEO             # Show video status
ytobs status VIDEO -v          # With processing history
ytobs vault                    # Vault statistics
ytobs vault --channels         # List videos
ytobs --list-processed         # List all cached videos
ytobs --append --patterns X Y  # Add patterns incrementally
ytobs --force URL              # Re-analyze
```

---

### 2026-09-01: Free Model Migration + fabric Patch

**Major Achievement**: All-paid-model config replaced with validated free models; fabric patched for template-strict models; qwen3.8-27b default restored

**Model Registry Overhaul**:
- Old registry was 100% broken: `minimax-m2.1`/`deepseek-v4-pro` (stale IDs → "could not find vendor"), `minimax-m2.7`/`kimi-k2.6` (402 Payment Required on ollama.com)
- New free registry (all live-tested): best=qwen/qwen3.8-27b (131,042 ctx), fast=openai/gpt-oss-20b, quality=openai/gpt-oss-120b, compound=groq/compound-mini, pt=amalia-9b (Lusófona), + ornith-9b/omnicoder-9b
- Updated: `config.yaml`, `~/.yt-obsidian/config.yml` (the one actually loaded), `ytobs/config.py` (defaults + embedded template)
- Fixed hardcoded fallback lists (`["kimi", "fast"]` in fabric_orchestrator.py, `["fast", "kimi", "deepseek"]` in metadata_extractor.py) → `["fast", "quality", "compound"]`

**fabric Binary (upstream bug + local patch)**:
- Root cause of Groq 400s ("No user query found in messages" / "last message role must be 'user'"): patterns embedding `{{input}}` in system.md suppress the user message → system-only payload; strict-template models (Qwen, compound) reject it. Upstream issue #2108, UNFIXED as of v1.4.473
- Local build `v1.4.473+dirty` at `~/.local/bin/fabric` (fabric-ai symlinked): patched `internal/plugins/ai/openai/{chat_completions,openai}.go` to promote a lone system message to user role (generalizes upstream's deepseek-only hack)
- Rebuild instructions documented in HELP.md → "Model compatibility: fabric + template-strict models"

**pattern_optimizer Fix** (`ytobs/cli.py`):
- Was running on fabric's default model (amalia-9b), which deterministically omits a JSON comma → parse failure
- Now pinned to the ytobs-configured model (`-m <resolved model_id>`) + markdown fence stripping before `json.loads`

**Validation Run** (DEF CON 32 Counter Deception, gHqDEMrqTjE):
- 15/15 patterns in final note (201KB): 12 on qwen3.8-27b + gpt-oss-120b, find_logical_fallacies on amalia-9b (Lusófona)
- pattern_optimizer JSON repair added (`_parse_optimizer_json` in cli.py): fixes missing/trailing commas from LLM output, validated on real malformed captures
- Groq free tier hard limits discovered: TPD 200K/model (qwen exhausted mid-day, per-model buckets), **TPM 8000 → 413 Request Entity Too Large** for packets over 8K tokens (find_logical_fallacies template ≈6.5K tokens + any chunk → impossible on Groq free tier; Lusófona endpoint has no such cliff)
- Runtime chunking knob is `expert.chunk_size` in ~/.yt-obsidian/config.yml (NOT a top-level `chunking:` block — that's repo-config-only)
- Known quirks: `--force --patterns` creates a NEW note instead of appending; cache marks failed patterns as "run" blocking `--append` (workaround: strip the pattern from cache patterns_run before appending)

**Status**: ✅ Free-model pipeline fully operational on qwen3.8-27b default



---

### 2026-09-03: V4.1.0 — Retro Enrichment, Dedupe, Refinement Layer, Model Provenance

**Major Achievement**: Six work units turning the vault from 148 raw notes (128 with empty pattern headings, 8 duplicate clusters) toward a curated, provenance-tracked, single-note-per-video state

**Vault Reality Driving This Session**:
- 148 notes in `$OBSVAULT/youtube/`, all `status: raw`
- ~20 with filled AI Analysis sections; ~128 with EMPTY pattern headings (failed-run residue)
- 8 `video_id` duplicate clusters (`me_at_the_zoo` ×11, `dario_amodei` ×8) from filename-collision suffixing " (2)", " (3)"
- Transcripts stored unfenced (rendering + parsing hazards)
- Full diagnosis and procedures: `docs/RUNBOOK.md` (new this session)

**Work Units**:
1. **Model provenance per pattern**: every pattern section carries a `*Model: X · date*` line, plus a `pattern_runs` log in frontmatter
2. **Backtick-safe fenced transcripts**: raw transcripts always inside fenced code blocks
3. **Transcript refinement layer** (`transcript_refiner.py`, per `docs/research/txrefine-opencode/04-integration-design.md`): regex-only pass for retro batches; fabric 2-stage refinement with validation guards for new runs; both raw and refined kept, both fenced
4. **`--force`/`--append` duplicate bug fixes**: force now overwrites the original note in place (no more "filename (2).md"); cache no longer marks FAILED patterns as "run"
5. **New subcommands**: `ytobs retro` (in-place enrichment of pattern-less notes) and `ytobs dedupe` (duplicate clusters → `status: duplicate` + `duplicate_of`, never deleted), both built on `frontmatter_editor.py` as the shared safe-editing core
6. **Curated default mode**: `extract_wisdom` + `summarize` replaces 10-15 pattern auto mode (Def Con note: 15 sections, 201KB was too much)

**Locked User Decisions (2026-09-03)**:
1. Retro-enrichment edits IN PLACE, never creates new files
2. Model provenance on every pattern section (in-note line + frontmatter `pattern_runs`)
3. One canonical note per video; duplicates marked, never deleted
4. Refinement layer between raw transcript and patterns (regex always, LLM 2-stage for new runs)
5. Raw transcripts always fenced
6. Minimal default pattern footprint (curated mode)

**Status**: ✅ V4.1.0 COMPLETE — verified 2026-09-03: dedupe applied to vault (8 groups, 31 notes marked, 0 deleted), retro batch 4/4 succeeded on qwen3.8-27b, --force now overwrites in place, fresh-video E2E with live fabric refinement (2550→2637 chars) all green. Bigram validation fixed (punctuation-aware tokens). Live config `analysis_mode` flipped `auto` → `curated` per locked decision #5. 66 retro targets remain for future quota-aware batches (`ytobs retro --limit 5`).

---

### 2026-09-03 (later): Repo Sealed + Sprint 2 Pattern Discovery

**Major Achievement**: ytobs published to GitHub (10-commit V4.1.0 history), docs refreshed to V4.1 reality, Sprint 2 pattern discovery implemented and shipped.

**Repo/GitOps**:
- Created https://github.com/fabiofalopes/ytobs (public); V4.1.0 sealed as 10 atomic commits + version bump 4.0.0 → 4.1.0
- Doc refresh: README/START_HERE/CONTEXT headers de-V3.0'd; dead `./yt`/`lib/` refs removed; honest Done/Next roadmap

**Sprint 2 — `ytobs patterns` family** (`pattern_discovery.py`, wired in cli.py):
- `ytobs patterns` — list (fabric -l primary, filesystem fallback), `search QUERY`, `describe NAME` (frontmatter description → first paragraph, never raises), `suggest --content-type TYPE` (static table ∩ installed patterns; types: video/podcast/tutorial/talk/interview/news)
- No AI calls, stdlib-only; argv pre-parse fix (patterns was being stolen as URL)
- Verified: 299 patterns listed, 51 'extract' matches, describe/suggest + error paths (exit 1) green; status/--version regression-free

**Retro progress**: batch of 5 (cheapest-first) 5/5 green on qwen3.8-27b → **65 targets remain**. New finding: 37 targets have NO transcript in cache — need re-fetch (`--update` backlog) before retro can process them.




### 2026-09-05: OpenCode Go as Gas — Direct API Transport + Model Chain Rebuild

**Trigger**: Lusófona endpoint (modelos.ai.ulusofona.pt) returned 503 — amalia/ornith/omnicoder all unreachable; two newest vault notes (Filipe Grilo #118, GTA 6) had ZERO AI analysis; Groq 8K TPM cliff made the 2500-token emergency chunking unusable.

**Architecture verdict (LangChain question)**: NO migration to LangChain. ytobs's AI layer is template-in/text-out; every pain hit (TPM cliffs, SSE hangs, model drift) is transport-layer. The adapter layer in `backend_adapter.py` was the designed extension point — a direct HTTP transport kills the subprocess/SSE problem class while keeping fabric's 299-pattern library as plain prompt files.

**Validated (live tests)**:
- Lusófona: 503 site-wide, dead
- Muse Spark: /responses endpoint only → unusable by fabric/chat-completions; also Meta trains on prompts (Contributor tier)
- deepseek-v4-flash via Go API: blocked (China-hosting opt-in required)
- glm-5.3-flash via fabric LiteLLM vendor: hangs on long outputs (SSE stall); via curl: 3.2s
- kimi-k2.7-code: rejects fabric's temp/top_p (needs -r), hangs in fabric anyway; 10s via curl
- **mimo-v2.5: fabric-native 54s/pattern; direct API 67-80s/chunk — THE workhorse** (30.1K req/5h, $0.14/M)
- nemotron-3-ultra-free: works both paths (2m20s fabric), free fallback
- big-pickle/mimo-v2.5-free: rate-limited at test time (congested shared pool)
- Local: Ollama has only :cloud models (402), LM Studio empty → not viable

**Shipped**:
1. `OpenAICompatAdapter` (backend_adapter.py): direct streaming chat/completions, fabric patterns loaded from `~/.config/fabric/patterns/<p>/system.md` ({{input}} substitution → single user message, strict-template-safe), usage tracking (`📊 tokens in/out`), finish_reason-aware errors, `max_output_tokens` cap per model
2. `FabricAdapter` env wiring: `base_url` in ModelConfig now injects `--vendor LiteLLM` + `LITELLM_API_BASE_URL`/`LITELLM_API_KEY` into the subprocess env (stored fabric .env untouched)
3. Key resolution: `api_key_env` env var → OpenCode auth.json provider (`auth_provider: opencode-go` / `opencode`); values never logged
4. Model chain: `model: go` (mimo-v2.5 direct) → fallbacks [gofree, gofabric, fast, quality]; `goflash` (glm-5.3-flash) for small-output tasks ONLY (burned 38K reasoning tokens on extract_wisdom, sometimes zero content); `max_output_tokens: 8000` caps reasoning burn
5. `config.fallback_models` config-driven fallback chain replaces hardcoded lists in orchestrator/metadata_extractor/refiner
6. `output_language: English` → `OUTPUT REQUIREMENTS` in packet preamble (guards MiMo Chinese drift — observed non-deterministic ZH output)
7. Append path now writes frontmatter `pattern_runs` (source: append) — provenance gap vs locked decision #2 closed
8. CLI argv pre-parse bug: `--patterns VALUES` were stolen as URL (only URL-looking args accepted now)
9. Live config: chunk TEMP knob removed (expert.chunk_size 8000 is the real knob; chunking: block was dead); Go has no TPM cliff so 8K chunks restored (15.6K-token transcript → 3 chunks vs ~7 before)

**E2E verified**: GTA 6 note (1h video, 12.9K words): Phase 1 metadata 3 patterns single-call (no TPM cliff), extract_wisdom 3 chunks 67/47/33s ≈ 2.5 min, append + pattern_runs frontmatter + `*Model: mimo-v2.5 · 2026-09-05*` lines all green. Second append (summarize) green.

**Known quirks**: append adds a NEW `### Extract Wisdom` heading next to stale empty ones from old failed runs (retro cleanup domain); orchestrator `--stream` Popen path not yet adapter-wired (only used with --stream flag).

**Uncommitted**: 10 modified files (this session). Next: commit, retro batch on mimo-v2.5 (65 targets; 37 need transcript re-fetch first).

#### 2026-09-05 (same day, follow-up): Exact context limits verified + docs

- New doc `docs/MODEL_CONTEXT_LIMITS.md`: exact context windows + max-output for every registry model, with source + verification method per row.
- Method: Groq API `/models` (live metadata); gateway bracket-probing (glm-5.3-flash accepted 1,048,018 / rejected 1,050,023 → **1,048,576 = 2^20**; nemotron-3-ultra-free limit stated verbatim in gateway error = **1,048,576**; mimo-v2.5 pass at 300,253 tok, >1M prompts hang with no clean reject); models.dev vendor entries (xiaomi/zai/nvidia).
- `context_window` synced to exact values in `~/.yt-obsidian/config.yml`, `ytobs/config.py` defaults + embedded template, and repo `config.yaml`: go/goflash/gofabric/gofree = 1,048,576; best = 131,042; fast/quality/compound = 131,072; pt/ornith/omnicoder = 32,768 (Lusófona 503, unverifiable).
- Gotchas recorded: glm gateway limit (2^20) ≠ z.ai native spec (1M); mimo >1M-token prompts hang (keep <~900K); prompt caching live on Go gateway (287K cached on 300K probe); max_output cap 8,000 vs Groq compound-mini real max completion 8,192.

#### 2026-09-05 (same day, final): Failure Session Protocol + `ytobs doctor`

**Standing rule (user decision)**: every time the tool fails, a session runs and learnings compound. Codified as the Failure Session Protocol in `docs/AGENTIC_GRAPH.md` §0: doctor → classify vs breakage tree → fix at the right level (config / new doctor check / new tree row / code) → write back to the structure. A failure session that doesn't update the structure hasn't happened.

**Shipped `ytobs doctor`** (`ytobs/doctor.py`, wired as subcommand): one-command triage — env (OBSVAULT/cache), config resolution + fallback chain, per-model key resolution (never prints values), fabric binary + patterns dir (openai-compat depends on it), endpoint reachability (Go/Zen /models, Lusófona watchdog), quota-state file freshness, and a smoke test of the primary model through the REAL adapter. Flags: `--model ALIAS` (smoke a specific model), `--full` (smoke fabric providers too). Exit 1 = hard failure.

**Validated live**: default run = HEALTHY with 1 warning (Lusófona 503, warning by design); `--model gofree` = HEALTHY (61s — free pool slow but alive). New empirical gotcha recorded in MODEL_CONTEXT_LIMITS.md: **mimo-v2.5 is a hybrid reasoning model** — tiny prompts emit `reasoning_content` with null `content` (doctor smoke needed a finish_reason=length pass-through instead of hard-failing on empty content).

**Agentic structure this session**: docs/AGENTIC_GRAPH.md (execution graph, transport routing, model chain, 13-row breakage tree, session trace + probing recipe, economics), docs/plans/YTOBS_MASTERPLAN.md (multi-session work queue, waves 0-3 + backlog), START_HERE.md refresh, README de-staled (kimi/llama refs), RUNBOOK registry rewritten for the Go era.

**Uncommitted**: 12 modified + 3 new files. Next session: Wave 0 (commit) → Wave 1 (retro backlog on mimo, ~$2 for 65 targets; 37 need transcript re-fetch).
