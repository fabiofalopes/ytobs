# Bug Fix: Long Video Transcripts

## Problem

When running with long videos (28K+ words), `pattern_optimizer` failed:

```bash
./yt "https://www.youtube.com/watch?v=-HzgcbRXUK8"
📥 Extracting video: -HzgcbRXUK8
✅ Extracted transcript: 28001 words
❌ Error: pattern_optimizer failed:
```

## Root Cause

- 28,001 words ≈ 36,401 tokens
- LLM context limits:
  - `llama-4-scout`: ~16K tokens
  - `kimi`: ~10K tokens
- **Problem**: Sending entire transcript to `pattern_optimizer` exceeded context window

## Solution

Truncate transcript for pattern analysis only:

```python
# In run_pattern_optimizer()
words = transcript.split()
if len(words) > 2000:
    sample_transcript = ' '.join(words[:2000])  # ~2600 tokens
else:
    sample_transcript = transcript

# Use sample_transcript for pattern_optimizer
# Full transcript still used for actual AI analysis
```

**Rationale**:
- Pattern selection only needs a content sample, not full transcript
- 2000 words is sufficient to understand content type, topics, complexity
- Full transcript still processed via chunking in Phase 2

## Testing

Test video: Demis Hassabis podcast (28,001 words)

### Before Fix
```
❌ Error: pattern_optimizer failed
```

### After Fix
```
✅ Preview mode: Works
   - 13 patterns recommended
   - Correctly identified as "high complexity" AI/ML content

✅ Quick mode: Works
   - Transcript chunked into 5 parts
   - Processing 5 patterns × 5 chunks = 25 operations

✅ Auto mode: Works
   - Smart pattern selection with 15 patterns
```

## Files Modified

- `yt` (lines 135-158) - Added truncation in `run_pattern_optimizer()`

## Impact

- ✅ Long videos now work correctly
- ✅ No change to short videos (< 2000 words)
- ✅ Pattern recommendations still accurate (uses representative sample)
- ✅ Full transcript analysis unchanged (chunking handles it)

## Related

This is the same fix previously applied in CONTEXT.md session log from earlier debugging session. The fix ensures pattern_optimizer works within LLM context limits while maintaining full transcript analysis.
