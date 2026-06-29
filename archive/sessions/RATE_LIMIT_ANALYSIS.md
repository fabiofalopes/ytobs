# Rate Limit Analysis - Long Video Processing

## What Happened

Running a long video (28K words, 5 chunks) with 10 patterns:
- **Total operations**: 10 patterns × 5 chunks = 50 API calls
- **Success rate**: 25/50 (50%)
- **Result**: Partial analysis, note still created

## Failure Pattern

```
Pattern: extract_wisdom
  Chunk 1/5... ✗ (Exit code 1)  ← Failed immediately, stopped

Pattern: extract_insights  
  Chunk 1/5... ✓
  Chunk 2/5... ✓
  Chunk 3/5... ✗ (Exit code 1)  ← Failed mid-way, stopped

Pattern: extract_predictions
  Chunk 1/5... ✓
  Chunk 2/5... ✓
  Chunk 3/5... ✓
  Chunk 4/5... ✓
  Chunk 5/5... ✓  ← Succeeded fully

[Later patterns failed on first chunk]
```

## Root Cause: Rate Limiting

### Groq Free Tier Limits (llama-4-scout)
- **TPM**: 30,000 tokens per minute
- **Requests**: ~30 per minute (estimated)

### The Math
- Each chunk: ~8,000 tokens input
- 50 operations × 8K = 400K tokens total
- At 30K TPM: Would take ~13 minutes sequentially
- **Problem**: Orchestrator runs patterns in sequence but chunks quickly
  - Pattern 1: Chunk 1, 2, 3, 4, 5 (rapid fire)
  - Pattern 2: Chunk 1, 2, 3, 4, 5 (rapid fire)
  - After ~30 calls in ~1 minute, rate limit hit

### Why Some Patterns Succeeded

**Timeline**:
1. First ~25-30 API calls: Within rate limit ✅
2. After that: Rate limit errors ❌
3. Patterns that started early (predictions, summary, main_idea): Completed
4. Patterns that started late (wisdom, questions, ideas): Failed immediately

## Current Implementation Issue

### What's Missing: Retry Logic

```python
# fabric_orchestrator.py currently does:
result = subprocess.run(["fabric-ai", "--pattern", pattern], input=chunk)
if result.returncode != 0:
    return {"success": False, "error": f"Exit code {result.returncode}"}
    # ❌ NO RETRY on rate limit
```

### What Should Happen

```python
# rate_limiter.py has retry logic but ISN'T BEING USED:
from .rate_limiter import RateLimitHandler  # ✅ Imported but not used!

handler = RateLimitHandler(max_retries=3, base_delay=5.0)
result = handler.run_with_retry(...)  # ← This would auto-retry on 429 errors
```

## Impact

### Current Behavior
- ✅ Creates note with partial analysis
- ⚠️ Some patterns missing completely
- ❌ No retry on rate limit errors
- ❌ Silent failures (just shows "Exit code 1")

### For Long Videos (5+ chunks)
- Auto mode (15 patterns): ~75 API calls → Will hit rate limit
- Quick mode (5 patterns): ~25 API calls → Might hit rate limit
- Deep mode (20+ patterns): ~100+ API calls → Will definitely hit limit

## Recommendations

### Option 1: Add Retry Logic (Best)
Integrate `RateLimitHandler` into orchestrator:
- Auto-retry on 429 errors (exponential backoff)
- Add delays between chunks (respect rate limits)
- Display clearer error messages

### Option 2: Reduce Patterns for Long Videos
Automatically scale down based on transcript length:
```python
if word_count > 10000:
    max_patterns = 5  # Quick mode
elif word_count > 5000:
    max_patterns = 10  # Auto mode  
else:
    max_patterns = 15  # Full auto
```

### Option 3: Sequential Processing with Delays
Add inter-chunk delay:
```python
time.sleep(2)  # 2 seconds between chunks
```
**Cost**: Slower processing (extra 10s per pattern)
**Benefit**: Stays within rate limits

### Option 4: Better Model Selection
Use model with higher TPM for long videos:
```python
if word_count > 10000:
    model = "llama-4-scout"  # 30K TPM
    # Still might hit limits with 50 calls
```

## Immediate Workaround

For users hitting rate limits on long videos:

```bash
# Use quick mode (fewer patterns, fewer API calls)
./yt --quick "LONG_VIDEO_URL"

# Or limit patterns manually
./yt --max-patterns 5 "LONG_VIDEO_URL"

# Or use no-analysis for just transcript
./yt --no-analysis "LONG_VIDEO_URL"
```

## Technical Fix Required

**Priority**: HIGH  
**Complexity**: MEDIUM  
**Files to modify**:
1. `lib/fabric_orchestrator.py` - Use RateLimitHandler for all Fabric calls
2. `yt` - Maybe reduce default patterns for long videos

**Current Status**: Rate limiter exists but isn't integrated properly.

---

## Summary

The tool works but hits Groq's rate limits on long videos with many patterns:
- ✅ Short videos (5 patterns): Works fine
- ⚠️ Long videos (5+ chunks, 10 patterns): Partial failures
- ❌ Long videos (15+ patterns): Many failures

**Note**: Despite failures, a note IS created with whatever succeeded.
