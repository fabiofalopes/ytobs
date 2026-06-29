# YouTube-Obsidian - Quick Start for AI Agents

**Version:** V3.0 - Smart Cache System  
**Status:** ✅ Fully Operational  
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
./yt --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Run again - should SKIP instantly (cache working)
ytobs "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# Expected: ⏭️ SKIPPED: Note already exists
```

---

## 📚 Navigation (Where to Look)

| Task | Document |
|------|----------|
| **Understand full context** | [CONTEXT.md](CONTEXT.md) - Complete history, decisions, current state |
| **User documentation** | [README.md](README.md) - How to use the tool |
| **Installation** | [SETUP.md](SETUP.md) - Setup instructions |
| **Architecture understanding** | [docs/architecture/](docs/architecture/) - System design by version |
| **Development work** | [docs/development/](docs/development/) - Developer guides |
| **Fix bugs** | CONTEXT.md → "Known Issues" section |
| **Add features** | docs/architecture/future-multi-provider.md |

---

## 🚀 Current State (V3.0)

**Implemented & Working:**
- ✅ Smart cache prevents duplicate processing
- ✅ Incremental pattern addition (`--append`)
- ✅ Multi-model fallback (llama-70b, kimi, llama-8b)
- ✅ Rate limit handling with retry logic
- ✅ Intelligent pattern selection via `pattern_optimizer`
- ✅ Phase 1 (global metadata) + Phase 2 (pattern analysis)

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
| **V3.0** | **2025-12-09** | **Smart cache + incremental updates** |

---

## 🔧 Common Development Tasks

### Fixing Bugs
1. Read CONTEXT.md → Find "Known Issues" or relevant section
2. Check recent session logs at end of CONTEXT.md
3. Review relevant architecture doc in docs/architecture/
4. Make changes, test with short video

### Adding Features
1. Check docs/architecture/future-multi-provider.md for roadmap
2. Review V3.0 implementation in CONTEXT.md as example
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
- 15 Python modules in `lib/`
- ~3,000 lines of production code
- V3.0 added: `cache_manager.py`, `incremental_writer.py`

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
- `ytobs` - Main CLI interface
- `lib/cache_manager.py` - V3.0 core functionality
- `lib/fabric_orchestrator.py` - AI analysis engine
- `config.yaml` - Default configuration template

---

## 🔜 Next Steps (V3.1+)

Ready for implementation:
1. Implement `--update` flag (metadata refresh)
2. Bulk playlist processing
3. Migration tool for existing notes
4. Vector DB integration
5. Knowledge graph construction

See: docs/architecture/future-multi-provider.md

---

## 💡 Pro Tips

1. **Always test cache:** Run same video twice to verify skip
2. **Check cache contents:** `cat $OBSVAULT/youtube/.cache/index.json`
3. **Debug mode:** Add `--debug` flag to any command
4. **Clean slate:** `rm -rf $OBSVAULT/youtube/.cache` to reset
5. **Update this file:** When adding major features, update the "Current State" section

---

**Last Updated:** 2025-12-09  
**Maintained By:** AI-assisted development sessions  
**License:** MIT
