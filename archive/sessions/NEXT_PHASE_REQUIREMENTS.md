# Next Phase Requirements - Production Readiness

**Status**: Planning Document  
**Priority**: HIGH  
**Created**: 2025-12-09  

---

## Executive Summary

The tool works but has critical issues with long videos and rate limiting. This document outlines the technical requirements to achieve production-ready status with proper error handling, streaming output, and optimized chunking.

---

## Current State Analysis

### What Works ✅
- Short videos (< 5 min): Full analysis successful
- Quick mode: 5 patterns, reliable
- Transcript extraction: Fast, accurate
- Note creation: Clean markdown output
- Pattern selection: Smart via pattern_optimizer

### Critical Issues ❌

#### 1. Rate Limit Failures (HIGH PRIORITY)
**Problem**: 50% failure rate on long videos
- RateLimitHandler exists but ISN'T USED by orchestrator
- No retry logic on 429 errors
- Silent failures ("Exit code 1")

**Impact**: 
- Long videos: 50% of patterns fail
- User sees incomplete analysis
- No indication of what failed or why

#### 2. Phase 1 Pattern Failures (HIGH PRIORITY)
**Problem**: Phase 1 always shows "3 pattern(s) failed, using fallbacks"
- create_micro_summary, extract_main_idea, extract_patterns fail
- Falls back to title-based extraction
- These patterns are SUPPOSED to run on full transcript to create global context

**Root Cause**: Not clear if this is:
- Token limit exceeded (28K words = 36K tokens)
- Missing retry logic
- Wrong chunking strategy

#### 3. No Streaming Output (MEDIUM PRIORITY)
**Current**: All processing happens in memory, writes at end
**Problem**: 
- User sees nothing for minutes
- If process fails, loses all work
- Can't stop mid-way and keep partial results

**Desired**: 
- Create note immediately
- Stream each section as it's ready
- Graceful failure (keep what succeeded)

#### 4. Chunking Issues (MEDIUM PRIORITY)
**Problem**: Current chunking doesn't respect Phase 1 vs Phase 2
- Phase 1 should run on FULL transcript (with retry/chunking if needed)
- Phase 2 runs on chunks with Phase 1 context embedded
- Currently Phase 1 fails and falls back, Phase 2 works

---

## Technical Deep Dive: The Pipeline Vision

### Intended Architecture (Not Fully Implemented)

```
INPUT: YouTube URL
  ↓
EXTRACT: Metadata + Full Transcript (28K words)
  ↓
═══════════════════════════════════════════════
PHASE 1: Global Context Extraction
═══════════════════════════════════════════════
Goal: Extract high-level context from FULL content

Run 3 patterns on FULL transcript:
  1. create_micro_summary    → "This is about X discussing Y"
  2. extract_main_idea       → "Core concept: Z"  
  3. extract_patterns        → "Patterns: A, B, C"

Problem: 28K words = 36K tokens (exceeds 10-16K limit)

Solution Options:
  A. Chunk transcript, run patterns, COMBINE results
     - Run pattern on chunk 1 → result 1
     - Run pattern on chunk 2 → result 2
     - ...
     - COMBINE all results → single summary
     - Challenge: How to combine? Use join pattern?
  
  B. Smart truncation for Phase 1
     - Use first 8K tokens for summary
     - Use full transcript for Phase 2 only
  
  C. Hierarchical summarization
     - Summarize each chunk
     - Summarize the summaries
     - Recursive until < token limit

Output: GlobalMetadata
  - summary: "50-word overview"
  - theme: "Main theme"
  - topics: ["AI", "ML", "Physics"]

  ↓
═══════════════════════════════════════════════
BUILD ENRICHED PACKETS
═══════════════════════════════════════════════
Chunk transcript into N chunks (~8K tokens each)

For each chunk, create EnrichedPacket:
  - chunk_text: "The actual transcript segment"
  - global_summary: "50-word overview" (from Phase 1)
  - global_theme: "Main theme" (from Phase 1)
  - global_topics: ["AI", "ML"] (from Phase 1)
  - chunk_index: 1 of 5
  - video_title: "..."

This gives each chunk CONTEXT about the full video.

  ↓
═══════════════════════════════════════════════
PHASE 2: Pattern Analysis on Chunks
═══════════════════════════════════════════════
For each pattern (e.g., extract_wisdom):
  For each chunk (1-5):
    Run pattern on EnrichedPacket
    Get result
  
  COMBINE all chunk results → single output per pattern
  
Problem: How to combine?
  - Simple concatenation?
  - Run join_pattern on concatenated?
  - Smart merging (dedupe, prioritize)?

Current: Uses join_pattern if available

  ↓
═══════════════════════════════════════════════
OUTPUT: Generate Markdown
═══════════════════════════════════════════════
Combine:
  - Front matter (metadata)
  - Video description
  - Transcript (formatted)
  - AI Analysis (pattern outputs)

Write to: $OBSVAULT/youtube/DATE_TITLE.md
```

---

## Critical Requirements

### REQ-1: Integrate Rate Limiting (CRITICAL)

**Objective**: Use existing RateLimitHandler in orchestrator

**Current Code** (fabric_orchestrator.py):
```python
# Lines 432-462
process = subprocess.Popen(cmd, ...)  # Direct call, no retry
if process.returncode != 0:
    return {"success": False, "error": f"Exit code {process.returncode}"}
```

**Required Changes**:
```python
from .rate_limiter import RateLimitHandler

# In __init__:
self.rate_limiter = RateLimitHandler(
    max_retries=3,
    base_delay=5.0,
    inter_chunk_delay=2.0  # 2s between chunks
)

# In _run_pattern_on_chunk:
result = self.rate_limiter.run_fabric_with_retry(
    pattern=pattern,
    input_text=packet.to_prompt(),
    model=self.model,
    timeout=self.timeout
)

if not result.success:
    if "429" in result.error:
        # Wait and retry (handled by rate_limiter)
        pass
    else:
        # Real error, log it
        return {"success": False, "error": result.error}

return {"success": True, "output": result.output}
```

**Files to Modify**:
- `lib/fabric_orchestrator.py` (lines 430-490)

**Testing**:
- Long video with 10 patterns
- Should see retries on rate limits
- Should complete all patterns (even if slower)

**Acceptance Criteria**:
- ✅ No "Exit code 1" failures on rate limits
- ✅ Auto-retry with exponential backoff
- ✅ Clear messages: "⏳ Rate limited, retrying in 5s..."
- ✅ All patterns complete (100% success rate)

---

### REQ-2: Fix Phase 1 Failures (CRITICAL)

**Objective**: Phase 1 patterns should succeed, not fall back

**Current Behavior**:
```
📊 Extracting global metadata...
  Running: create_micro_summary
  Running: extract_main_idea
  Running: extract_patterns
  ⚠️  3 pattern(s) failed, using fallbacks
```

**Problem Investigation Needed**:
1. Is it token limit? (28K words = 36K tokens)
2. Is it rate limiting? (3 calls in quick succession)
3. Is it wrong model? (model doesn't support pattern)

**Solution Approach**:

**Option A: Chunk Phase 1 Too**
```python
# For Phase 1, if transcript > 10K tokens:
# 1. Chunk transcript
# 2. Run pattern on each chunk
# 3. Combine results using join pattern

def extract_global_metadata_chunked(transcript):
    if token_count(transcript) < 10000:
        # Run directly
        return run_patterns(transcript)
    
    # Chunk transcript
    chunks = chunk_transcript(transcript, max_tokens=8000)
    
    # Run each pattern on all chunks
    results = {}
    for pattern in ["create_micro_summary", "extract_main_idea", "extract_patterns"]:
        chunk_results = []
        for chunk in chunks:
            result = run_pattern(pattern, chunk)
            chunk_results.append(result)
        
        # COMBINE chunk results into single result
        combined = combine_results(pattern, chunk_results)
        results[pattern] = combined
    
    return results

def combine_results(pattern, chunk_results):
    # Option 1: Use join pattern
    if has_join_pattern(pattern):
        return run_pattern(f"join_{pattern}", "\n\n".join(chunk_results))
    
    # Option 2: Simple concatenation with deduplication
    return dedupe_and_merge(chunk_results)
```

**Option B: Smart Truncation**
```python
# For Phase 1, use representative sample
def extract_global_metadata_sampled(transcript):
    # Use first 2K words + last 500 words
    words = transcript.split()
    if len(words) > 10000:
        sample = ' '.join(words[:2000] + ["..."] + words[-500:])
    else:
        sample = transcript
    
    return run_patterns(sample)
```

**Recommendation**: Try Option B first (simpler), fall back to Option A if quality suffers.

**Files to Modify**:
- `lib/metadata_extractor.py` (lines 80-150)

**Acceptance Criteria**:
- ✅ Phase 1 patterns succeed (no "failed, using fallbacks")
- ✅ Quality global metadata extracted
- ✅ Works for videos up to 50K words

---

### REQ-3: Streaming Output to File (MEDIUM PRIORITY)

**Objective**: Write note incrementally as processing happens

**Current Flow**:
```
Process everything → Build full markdown → Write file
```

**Desired Flow**:
```
Create empty note immediately
  ↓
Write front matter → Flush
  ↓
Write description → Flush
  ↓
Write transcript → Flush
  ↓
For each pattern:
  Write "## Pattern Name" → Flush
  For each chunk result:
    Append result → Flush
```

**Benefits**:
- User sees progress immediately
- Graceful failure (keeps partial results)
- Can Ctrl+C and keep what's done
- Better UX for long videos

**Implementation Challenges**:
1. **Markdown heading conflicts**: Can't append raw outputs (might have H1)
2. **Order matters**: Must ensure sections append in correct order
3. **Async complexity**: Multiple patterns running, must synchronize writes

**Proposed Solution**:

```python
class StreamingNoteWriter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.lock = threading.Lock()  # Prevent write conflicts
    
    def write_section(self, section_name: str, content: str):
        """Append a section to the note file."""
        with self.lock:
            # Normalize headings (H1 → H3, H2 → H4, etc)
            normalized = normalize_headings(content, base_level=3)
            
            with open(self.filepath, 'a') as f:
                f.write(f"\n\n## {section_name}\n\n")
                f.write(normalized)
                f.flush()  # Ensure written immediately

# In orchestrator:
note_writer = StreamingNoteWriter(output_path)

# Write initial sections
note_writer.write_section("Front Matter", frontmatter)
note_writer.write_section("Description", description)
note_writer.write_section("Transcript", transcript)

# Stream AI analysis
for pattern in patterns:
    note_writer.write_section(f"AI Analysis - {pattern}", "")
    for chunk_result in process_chunks(pattern):
        note_writer.append_to_section(f"AI Analysis - {pattern}", chunk_result)
```

**Files to Modify**:
- `lib/filesystem.py` - Add StreamingNoteWriter class
- `lib/fabric_orchestrator.py` - Use streaming writer
- `yt` - Pass output path to orchestrator

**Acceptance Criteria**:
- ✅ Note created immediately (empty)
- ✅ Sections appear as they complete
- ✅ Ctrl+C keeps partial results
- ✅ No corrupted markdown (proper heading levels)
- ✅ Thread-safe (no race conditions)

---

### REQ-4: Transcript Formatting (LOW PRIORITY)

**Objective**: Readable transcript with speaker labels and paragraphs

**Current**: Wall of text
```
we're talking about AI and machine learning and how it relates to physics and then we discuss the future of AGI and whether...
```

**Desired**: Formatted with paragraphs and speakers
```
**Speaker 1**: We're talking about AI and machine learning, and how it relates to physics.

**Speaker 2**: That's fascinating. I think the connection between computation and physics is...

**Speaker 1**: Exactly. And then when we discuss the future of AGI, whether it will emerge from...
```

**Approach**:
- Use Fabric pattern (e.g., `format_transcript`)
- Or custom pattern: `transcribe_speakers`
- Run BEFORE saving transcript section

**Challenge**: 
- yt-dlp doesn't give speaker labels
- Need AI to infer speakers from context
- Might not be 100% accurate

**Files to Modify**:
- `lib/transcript.py` - Add format_transcript() function
- `lib/formatter.py` - Call formatting before including transcript

**Acceptance Criteria**:
- ✅ Paragraphs separated logically
- ✅ Speaker labels (if multiple speakers detected)
- ✅ Fallback to raw transcript if formatting fails

---

### REQ-5: Token Counting and Metrics (LOW PRIORITY)

**Objective**: Track token usage in front matter

**Add to YAML front matter**:
```yaml
---
# ... existing fields
metrics:
  transcript_words: 28001
  transcript_tokens: 31908
  chunks_created: 5
  patterns_run: 10
  api_calls_made: 50
  api_calls_failed: 6
  total_processing_time: 180s
  estimated_cost: $0.00  # If using paid API
---
```

**Files to Modify**:
- `lib/formatter.py` - Add metrics to front matter
- `lib/fabric_orchestrator.py` - Track calls and timing

**Acceptance Criteria**:
- ✅ Token counts accurate
- ✅ API call metrics tracked
- ✅ Processing time recorded

---

## Optimization Strategies

### Strategy 1: Adaptive Pattern Selection

**Concept**: Reduce patterns for long videos automatically

```python
def get_optimal_patterns(transcript_length, mode):
    if mode == "quick":
        return 5
    elif mode == "auto":
        if transcript_length > 20000:
            return 5  # Too long, use quick
        elif transcript_length > 10000:
            return 10
        else:
            return 15
    elif mode == "deep":
        if transcript_length > 20000:
            return 10  # Even deep mode scales back
        else:
            return 20
```

**Benefit**: Avoid rate limits on long videos automatically

---

### Strategy 2: Inter-Chunk Delays

**Concept**: Pace API calls to stay within rate limits

```python
# In orchestrator, between chunks:
time.sleep(2)  # 2 seconds between chunks

# Math:
# 5 chunks × 2s = 10s extra per pattern
# 10 patterns × 10s = 100s total overhead
# But avoids rate limit failures
```

**Trade-off**: Slower but more reliable

---

### Strategy 3: Hierarchical Chunking

**Concept**: Chunk recursively for very long videos

```python
def hierarchical_process(transcript):
    # Level 1: Chunk to 8K tokens
    chunks = chunk_transcript(transcript, 8000)
    
    # Level 2: Process each chunk
    summaries = [summarize(chunk) for chunk in chunks]
    
    # Level 3: Combine summaries (if still too long)
    if total_tokens(summaries) > 8000:
        meta_summary = summarize(join(summaries))
    else:
        meta_summary = join(summaries)
    
    return meta_summary
```

**Use Case**: Videos > 50K words

---

## Testing Requirements

### Test Suite Needed

**Test Videos**:
1. Short (< 5 min, < 1K words) - Should complete in < 30s
2. Medium (20 min, 5K words) - Should complete in ~2 min
3. Long (1 hour, 10K words) - Should complete in ~5 min
4. Very Long (3+ hours, 30K words) - Should complete in ~10 min

**Test Modes**:
- Quick mode on each video
- Auto mode on each video
- Deep mode on short/medium only

**Success Criteria**:
- ✅ 100% pattern success rate (with retries)
- ✅ Notes created with all sections
- ✅ No rate limit failures (with proper delays)
- ✅ Streaming works (note appears immediately)

---

## Migration Path

### Phase 1: Critical Fixes (Week 1)
- REQ-1: Integrate rate limiting
- REQ-2: Fix Phase 1 failures
- Test with long videos

### Phase 2: UX Improvements (Week 2)
- REQ-3: Streaming output
- REQ-5: Token metrics
- Better error messages

### Phase 3: Optimizations (Week 3)
- REQ-4: Transcript formatting
- Adaptive pattern selection
- Hierarchical chunking

### Phase 4: Production Release (Week 4)
- Full test suite
- Documentation update
- GitHub release v2.1

---

## Open Questions

1. **Phase 1 Combining**: Best way to combine chunk results?
   - Use join patterns?
   - Simple concatenation?
   - LLM-based smart merging?

2. **Streaming Complexity**: Worth the async complexity?
   - Benefits: Better UX, graceful failure
   - Costs: More complex code, potential bugs

3. **Token Optimization**: Target token limit?
   - 8K (safe for all models)?
   - 10K (Groq free tier)?
   - 16K (more models support)?

4. **Cost vs Speed**: Optimize for?
   - Speed: Parallel calls (hit rate limits faster)
   - Reliability: Sequential with delays (slower but safer)

---

## Success Metrics

**V2.1 Definition of Done**:
- ✅ 100% pattern success rate on long videos
- ✅ Clear retry messages on rate limits
- ✅ Streaming output (note created immediately)
- ✅ Phase 1 patterns succeed
- ✅ Token metrics in front matter
- ✅ Processing time < 10 min for 30K word video

**Current State**: ~50% success rate, no streaming, Phase 1 fails
**Target State**: 100% success rate, streaming, Phase 1 works

---

**Document Status**: DRAFT - Needs review and prioritization
**Next Step**: Discuss with team, assign priorities, create tickets
