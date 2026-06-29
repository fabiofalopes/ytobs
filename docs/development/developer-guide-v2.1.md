# YouTube to Obsidian - Development Session Prompt

**Project**: AI-enhanced YouTube video extraction to Obsidian notes  
**Status**: V2.0 operational, V2.1 critical fixes needed  
**Location**: `~/projetos/rascunhos/yt-dlp-tests`

---

## 🎯 MISSION: Fix Critical Rate Limiting Issues

You are a Python developer tasked with fixing rate limiting failures in a YouTube-to-Obsidian extraction tool. The tool works perfectly for short videos but has a **50% failure rate** on long videos due to improper rate limit handling.

### What Works ✅
- Short videos (< 5 min): Perfect extraction and analysis
- Quick mode: 5 patterns, 100% success rate
- Transcript extraction: Fast and accurate
- Note generation: Clean Obsidian markdown
- Pattern selection: Smart AI-based recommendations

### Critical Issues ❌
1. **Rate Limit Failures** (HIGH): 50% API call failures on long videos
2. **Phase 1 Extraction** (HIGH): Always falls back to title-based context
3. **No Streaming Output** (MEDIUM): User sees nothing until completion
4. **Poor UX on Failures** (MEDIUM): Silent failures, no progress indication

---

## 📁 Project Context

### Architecture Overview
```
YouTube URL
  ↓
Extract: Metadata + Transcript (via yt-dlp)
  ↓
Phase 1: Global Context Extraction
  - Run 3 patterns on full transcript: summary, theme, topics
  - Problem: Currently FAILS and falls back to title-based extraction
  ↓
Phase 2: Chunked Analysis  
  - Split transcript into ~8K token chunks
  - Run 5-15 patterns per chunk (based on mode)
  - Problem: 50% of API calls fail due to rate limits
  ↓
Combine: Merge pattern outputs
  ↓
Generate: Obsidian markdown note
```

### Key Files
```
yt-dlp-tests/
├── yt                          # Main CLI entry point ⭐ USE THIS
├── yt-obsidian.py             # Legacy fallback (DO NOT USE)
├── lib/
│   ├── fabric_orchestrator.py # ⚠️ NEEDS FIX: Rate limit integration
│   ├── rate_limiter.py        # ✅ EXISTS: Has retry logic (NOT USED!)
│   ├── metadata_extractor.py  # ⚠️ NEEDS FIX: Phase 1 failures
│   ├── config.py              # Config management
│   ├── extractor.py           # yt-dlp wrapper (works perfectly)
│   ├── formatter.py           # Markdown generation (works perfectly)
│   └── [other modules]
├── config.yaml                # Default config
├── NEXT_PHASE_REQUIREMENTS.md # 📋 DETAILED TASK BREAKDOWN (300+ lines)
├── RATE_LIMIT_ANALYSIS.md     # 🔍 Root cause analysis
├── CONTEXT.md                 # Project history and decisions
└── README.md                  # User documentation
```

### Critical Dependencies
- **yt-dlp**: Metadata/transcript extraction (works great)
- **Fabric CLI** (`fabric-ai`): AI pattern execution (requires Groq API)
- **Groq API**: LLM inference (30K TPM limit on free tier)
- **tiktoken**: Token counting
- **tenacity**: Retry logic (installed but not integrated)

---

## 🔥 IMMEDIATE PRIORITY: Fix Rate Limiting

### The Problem

**Current Implementation (BROKEN)**:
```python
# lib/fabric_orchestrator.py line ~373
handler = RateLimitHandler(...)  # ✅ Creates handler
# BUT NEVER USES IT! ❌

# Instead does direct subprocess calls:
result = subprocess.run(["fabric-ai", "--pattern", pattern], input=chunk)
if result.returncode != 0:
    return {"success": False}  # ❌ NO RETRY!
```

**What Should Happen**:
```python
# lib/rate_limiter.py has full retry logic!
handler = RateLimitHandler(max_retries=3, base_delay=5.0)
result = handler.run_fabric_with_retry(
    pattern_name=pattern,
    input_data=chunk,
    model=model,
    context=context
)
# Auto-retries on 429 errors with exponential backoff ✅
```

### The Fix

**FILE**: `lib/fabric_orchestrator.py`

**TASK**: Replace all direct `subprocess.run()` calls with `handler.run_fabric_with_retry()`

**LOCATIONS**:
1. Phase 1 metadata extraction (~line 373+)
2. Phase 2 pattern processing (~line 420+)
3. Any other Fabric invocations

**REQUIREMENTS**:
- Use `RateLimitHandler` that's already imported
- Add inter-chunk delays (2s between chunks to avoid burst)
- Preserve streaming output if `--stream` flag enabled
- Show retry attempts in progress output
- Log failures properly (don't hide them)

**TESTING**:
```bash
# Test with long video that currently fails
./yt --quick "https://www.youtube.com/watch?v=ugvHCXCOmm4"

# Expected: 100% success rate (vs current 50%)
# Monitor: Should see retry messages if rate limited
# Result: All patterns complete successfully
```

---

## 🔍 SECONDARY PRIORITY: Fix Phase 1 Extraction

### The Problem

Phase 1 **always** shows:
```
⚠️ 3 pattern(s) failed, using fallbacks
```

Patterns that fail:
- `create_micro_summary`
- `extract_main_idea` 
- `extract_patterns`

Falls back to title-based extraction (loses valuable context).

### Root Cause Analysis

**Hypothesis 1**: Token limit exceeded
- Long transcripts (28K words = 36K tokens)
- Exceeds model context window (10-16K tokens)
- Solution: Chunk transcript for Phase 1, combine results

**Hypothesis 2**: Missing retry logic
- Same issue as Phase 2 (no RateLimitHandler integration)
- Solution: Apply same fix as Phase 2

**Hypothesis 3**: Wrong pattern approach
- Patterns don't work on raw transcript format
- Solution: Format transcript before Phase 1

### The Fix

**FILE**: `lib/metadata_extractor.py`

**INVESTIGATION** (Required first):
1. Check actual error messages (currently hidden in non-debug mode)
2. Test with short video - does Phase 1 succeed?
3. Check Fabric pattern requirements - do they need special input format?

**IMPLEMENTATION** (After investigation):
- Option A: Chunk Phase 1 if token limit issue
- Option B: Integrate RateLimitHandler if retry issue  
- Option C: Format transcript if input format issue

**TESTING**:
```bash
# Test Phase 1 with short video
./yt --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Expected: "✅ Phase 1 complete" (vs current warning)
# Check: .fabric/{video_id}/metadata/ has valid content
```

---

## 📖 DOCUMENTATION TO READ FIRST

### Essential Reading (Required)
1. **NEXT_PHASE_REQUIREMENTS.md** - Complete technical breakdown of all issues
2. **RATE_LIMIT_ANALYSIS.md** - Detailed failure pattern analysis  
3. **CONTEXT.md** - Project history, decisions, and architecture
4. **lib/rate_limiter.py** - The retry logic that needs integration
5. **lib/fabric_orchestrator.py** - The file that needs fixing

### Reference (As Needed)
- **README.md** - User documentation and usage examples
- **config.yaml** - Configuration options
- **BUGFIX_LONG_VIDEOS.md** - Previous pattern_optimizer fix (already done)

### Architecture Docs
- **docs/ARCHITECTURE.md** - System design
- **docs/PHASE1C_FABRIC_INTEGRATION.md** - Two-phase pipeline design

---

## 🛠️ DEVELOPMENT WORKFLOW

### Step 1: Setup
```bash
cd ~/projetos/rascunhos/yt-dlp-tests
source venv/bin/activate

# Verify environment
./yt --help
fabric-ai --help
```

### Step 2: Read Documentation
Read the files listed in "Essential Reading" section above.

### Step 3: Fix Rate Limiting
1. Open `lib/fabric_orchestrator.py`
2. Find all `subprocess.run()` calls to Fabric
3. Replace with `handler.run_fabric_with_retry()`
4. Add inter-chunk delays (2s)
5. Test with long video

### Step 4: Fix Phase 1 Extraction
1. Open `lib/metadata_extractor.py`
2. Enable debug mode to see actual errors
3. Investigate root cause (token limit vs retry vs format)
4. Implement appropriate fix
5. Test with short + long videos

### Step 5: Testing
```bash
# Short video (should work perfectly)
./yt --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Long video (currently 50% fail, should be 100% success after fix)
./yt --quick "https://www.youtube.com/watch?v=ugvHCXCOmm4"

# Verify outputs
ls -la ~/Documents/obsidian_vault/youtube/*.md
```

---

## 🎯 SUCCESS CRITERIA

### Must Achieve
- [ ] Rate limit fix: 100% success rate on long videos (vs current 50%)
- [ ] Phase 1 fix: No "pattern(s) failed" warnings
- [ ] All tests pass with no silent failures
- [ ] Clean error messages if genuine failures occur

### Should Achieve  
- [ ] Progress indicators during processing
- [ ] Retry attempts visible to user
- [ ] Inter-chunk delays prevent burst rate limiting

### Nice to Have
- [ ] Streaming output (create note incrementally)
- [ ] Adaptive pattern selection (reduce patterns if too long)
- [ ] Better error recovery (partial results still saved)

---

## 🚀 GETTING STARTED (COPY-PASTE THIS)

```bash
# Navigate to project
cd ~/projetos/rascunhos/yt-dlp-tests

# Activate environment
source venv/bin/activate

# Read essential documentation first
cat NEXT_PHASE_REQUIREMENTS.md  # Main task breakdown
cat RATE_LIMIT_ANALYSIS.md      # Problem analysis
cat lib/rate_limiter.py          # Solution that exists

# Identify the problem in code
grep -n "subprocess.run" lib/fabric_orchestrator.py | head -10

# Your mission: Replace subprocess calls with handler.run_fabric_with_retry()
# Reference: lib/rate_limiter.py lines 150-250 for implementation

# Test before fix (expect 50% failure)
./yt --quick "https://www.youtube.com/watch?v=ugvHCXCOmm4"

# [MAKE YOUR CHANGES]

# Test after fix (expect 100% success)
./yt --quick "https://www.youtube.com/watch?v=ugvHCXCOmm4"
```

---

## 🤖 OPENCODE AGENT RECOMMENDATION

This task is best suited for **@build** agent:
- Full development capabilities
- Can read, edit, and test Python code
- Has access to bash for testing
- Can run multiple operations in parallel

**Alternative**: Use **@code** agent for focused code fixes only

**DO NOT USE**: @plan (read-only), @research (documentation only)

---

## 📋 REFERENCE: Available OpenCode Agents

From `~/.config/opencode/`:
- **@build** - Full development (RECOMMENDED for this task)
- **@code** - Code-focused development
- **@plan** - Analysis and planning only (read-only)
- **@research** - Documentation and research
- **@thinking** - Complex reasoning with sequential_thinking MCP

---

## 💡 TIPS FOR SUCCESS

### Code Quality
- Follow existing code style (imports, docstrings, type hints)
- Add comments explaining retry logic
- Preserve existing functionality (don't break short videos)
- Test incrementally (don't change everything at once)

### Testing Strategy
1. Test short video first (baseline - should still work)
2. Test long video (should improve from 50% to 100%)
3. Test with `--preview` mode (fast, no API calls)
4. Test each mode: `--quick`, default, `--deep`

### Debugging
- Enable debug mode: `./yt --debug URL`
- Check Fabric working dir: `.fabric/{video_id}/`
- Check retry logs in console output
- Verify token counts don't exceed limits

### Git
- DO NOT commit without explicit user request
- But DO test your changes thoroughly before asking to commit

---

## ❓ QUESTIONS YOU MIGHT HAVE

**Q: Is RateLimitHandler already implemented?**  
A: YES! See `lib/rate_limiter.py` - fully functional retry logic exists but ISN'T USED.

**Q: Where exactly do I make changes?**  
A: `lib/fabric_orchestrator.py` - Replace `subprocess.run()` with `handler.run_fabric_with_retry()`.

**Q: How do I test without waiting forever?**  
A: Use `--preview` mode or `--quick` mode with short videos first.

**Q: What if I break something?**  
A: Test incrementally! Each subprocess call you fix can be tested separately.

**Q: Do I need to modify rate_limiter.py?**  
A: NO! It's already perfect. Just USE it in fabric_orchestrator.py.

---

## 📞 HELP & RESOURCES

- **Main requirements doc**: `NEXT_PHASE_REQUIREMENTS.md` (300+ lines, very detailed)
- **Problem analysis**: `RATE_LIMIT_ANALYSIS.md` (explains the 50% failure)
- **Project history**: `CONTEXT.md` (decisions and architecture)
- **User guide**: `README.md` (how tool works from user perspective)
- **Future architecture**: `FUTURE_ARCHITECTURE_MULTI_PROVIDER.md` (multi-key rotation, post-V2.1)

---

## ✅ FINAL CHECKLIST BEFORE STARTING

- [ ] Read NEXT_PHASE_REQUIREMENTS.md (15 min)
- [ ] Read RATE_LIMIT_ANALYSIS.md (5 min)
- [ ] Read lib/rate_limiter.py (10 min)
- [ ] Understand fabric_orchestrator.py structure (10 min)
- [ ] Have test video ready: `https://www.youtube.com/watch?v=ugvHCXCOmm4`
- [ ] Environment activated: `source venv/bin/activate`
- [ ] Tool works: `./yt --help`

**Total prep time**: ~40 minutes reading + understanding  
**Expected fix time**: 1-2 hours (replace subprocess calls, test)  
**Total session**: 2-3 hours to completion

---

**Ready? Start with reading NEXT_PHASE_REQUIREMENTS.md then begin coding! 🚀**

---

## 🔮 FUTURE VISION: Multi-Provider Rate Limit Distribution

**Note**: This is a POST-V2.1 enhancement. Fix current single-key issues first!

### The Concept
Instead of hitting rate limits with one API key, use **multiple API keys** from **multiple providers** to distribute load:

- **Multiple Groq keys**: 4 keys = 4× throughput (30K → 120K TPM)
- **Multiple providers**: Groq + Together + Fireworks = 150K+ TPM combined
- **Parallel execution**: Process chunks simultaneously across providers
- **Stay on free tiers**: Maximize free API usage across multiple accounts

### Why This Matters
Current limitation: 30K TPM (single Groq key)
- Long video: 400K tokens needed = 13+ min + 50% failures

With multi-provider:
- Combined: 150K+ TPM
- Same video: 2-3 min + <5% failures
- **5x faster, 10x more reliable**

### Implementation Stages
1. **V2.2**: Multi-key rotation (same provider) - 2-3 days
2. **V2.3**: Multi-provider support (Groq + Together + Fireworks) - 3-5 days  
3. **V2.4**: Parallel chunk processing - 3-5 days

### Complete Architecture Doc
See: `FUTURE_ARCHITECTURE_MULTI_PROVIDER.md` (600+ lines)

**Contains**:
- API key rotation algorithms (round-robin, LRU, random)
- Provider manager design (intelligent failover)
- Parallel orchestrator (concurrent chunk processing)
- Config examples (personal, free-tier max, enterprise)
- Implementation plan with timelines
- Code samples and technical challenges

**When to Implement**: After V2.1 stable (current rate limiting fixed)

**TL;DR**: Think "distribute the load across many free accounts" instead of "optimize single account". Like running multiple download threads instead of one sequential download. Same concept, applied to API rate limits.
