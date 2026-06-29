# Fabric Orchestration Framework: Context-Aware Packet Processing

**Status**: Design Phase  
**Created**: 2025-12-08  
**Scope**: Universal pattern for chunked AI processing with contextual enrichment

---

## Vision Statement

**The Problem**: Naively chunking content and sending it to AI models results in poor quality output because each chunk lacks broader context and position awareness.

**The Solution**: A two-phase orchestration framework where:
1. **Phase 1**: Extract global context using Fabric patterns (metadata enrichment)
2. **Phase 2**: Process chunks with enriched packets containing position-aware prompting

This creates a **feedback loop** where Fabric helps prepare better inputs for itself, resulting in coherent, context-aware outputs across all chunks.

---

## Core Principles

### 1. Context-Aware Chunking

**NOT THIS** (Naive):
```
Chunk 1: [raw transcript text]
Chunk 2: [raw transcript text]
Chunk 3: [raw transcript text]
```

**THIS** (Context-Enriched):
```
Chunk 1: {
  position: "beginning",
  global_context: "[brief video summary]",
  key_topics: "[extracted topics]",
  transcript_segment: "[text]",
  instruction: "This is the beginning segment. Focus on setup and introduction."
}

Chunk 2: {
  position: "middle",
  global_context: "[same summary]",
  key_topics: "[same topics]",
  transcript_segment: "[text]",
  instruction: "This is a middle segment. Focus on development and details."
}

Chunk 3: {
  position: "end",
  global_context: "[same summary]",
  key_topics: "[same topics]",
  transcript_segment: "[text]",
  instruction: "This is the final segment. Focus on conclusions and takeaways."
}
```

### 2. Position Awareness

Each chunk must know:
- **Where it is**: beginning / middle / end
- **What came before**: (for middle/end chunks)
- **The whole picture**: global summary/topics
- **How to behave**: position-specific instructions

### 3. Minimal Token Overhead

Context enrichment must be **concise**:
- Global summary: 1-2 sentences max (~50 tokens)
- Key topics: 5-10 keywords (~20 tokens)
- Position instruction: 1 sentence (~15 tokens)
- **Total overhead per chunk: ~85 tokens** (1% of 8K chunk)

### 4. Two-Phase Orchestration

**Phase 1: Global Context Extraction** (runs once)
- Input: Full transcript
- Patterns: `create_micro_summary`, `extract_main_idea`, `extract_patterns`
- Output: Metadata to inject into all chunks

**Phase 2: Chunk Processing** (runs per chunk, per pattern)
- Input: Enriched packet (metadata + chunk text)
- Patterns: `youtube_summary`, `extract_wisdom`, etc.
- Output: Position-aware analysis

---

## Architectural Pattern

### The Packet Structure

```python
@dataclass
class EnrichedPacket:
    """Context-enriched chunk for AI processing."""
    
    # Position metadata
    chunk_id: str              # "chunk_001"
    chunk_index: int           # 0, 1, 2...
    total_chunks: int          # 3
    position: str              # "beginning" | "middle" | "end"
    
    # Global context (from Phase 1)
    video_title: str           # "The Chinese AI Iceberg"
    video_summary: str         # 1-2 sentence summary
    key_topics: List[str]      # ["DeepSeek", "Qwen", "ByteDance", ...]
    main_theme: str            # "Overview of Chinese AI landscape"
    
    # Chunk-specific
    transcript_segment: str    # The actual chunk text
    timestamp_range: Tuple[str, str]  # ("00:00:00", "00:12:30")
    word_count: int
    token_count: int
    
    # Position-specific instruction
    processing_instruction: str
```

### Two-Phase Processing Flow

```
INPUT: Full transcript (13,310 tokens)
    ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: GLOBAL CONTEXT EXTRACTION                      │
│ (Run once, before chunking)                             │
└─────────────────────────────────────────────────────────┘
    │
    ├─→ fabric-ai -p create_micro_summary
    │       Output: "This video explores Chinese AI labs..."
    │
    ├─→ fabric-ai -p extract_main_idea  
    │       Output: "Comprehensive overview of AI development..."
    │
    └─→ fabric-ai -p extract_patterns
            Output: ["DeepSeek", "Qwen", "ByteDance", ...]
    │
    ↓
GLOBAL METADATA: {
    summary: "...",
    theme: "...",
    topics: [...]
}
    ↓
┌─────────────────────────────────────────────────────────┐
│ CHUNKING WITH ENRICHMENT                                │
│ (Split transcript, inject metadata into each packet)    │
└─────────────────────────────────────────────────────────┘
    ↓
ENRICHED PACKETS: [
    Packet 1 (beginning) + metadata,
    Packet 2 (middle) + metadata,
    Packet 3 (end) + metadata
]
    ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: CHUNK PROCESSING                               │
│ (Run each packet through each pattern)                  │
└─────────────────────────────────────────────────────────┘
    │
    ├─→ Pattern: youtube_summary
    │   ├─→ Process Packet 1 → Output 1
    │   ├─→ Process Packet 2 → Output 2
    │   └─→ Process Packet 3 → Output 3
    │       ↓
    │   Combine outputs → Final youtube_summary
    │
    └─→ Pattern: extract_wisdom
        ├─→ Process Packet 1 → Output 1
        ├─→ Process Packet 2 → Output 2
        └─→ Process Packet 3 → Output 3
            ↓
        Combine outputs → Final extract_wisdom
    ↓
FINAL MARKDOWN: All patterns appended
```

---

## Prompt Engineering Strategy

### Phase 1: Metadata Extraction Prompts

These patterns run on the **full transcript** (if it fits) or a **representative sample**.

**Pattern 1: `create_micro_summary`**
```
Purpose: Generate 1-2 sentence global summary
Usage: fabric-ai -p create_micro_summary < transcript_full.txt
Output: "This 27-minute video provides a comprehensive overview..."
Token cost: ~50 tokens output
```

**Pattern 2: `extract_main_idea`**
```
Purpose: Extract the core theme/purpose
Usage: fabric-ai -p extract_main_idea < transcript_full.txt
Output: "Comprehensive landscape analysis of Chinese AI companies"
Token cost: ~20 tokens output
```

**Pattern 3: `extract_patterns` (or custom)**
```
Purpose: Extract key entities/topics mentioned
Usage: fabric-ai -p extract_patterns < transcript_full.txt
Output: ["DeepSeek", "Qwen", "ByteDance", "Kimi", ...]
Token cost: ~30 tokens output
```

**Total Phase 1 cost**: ~100 tokens output (reused for all chunks)

---

### Phase 2: Position-Aware Packet Prompts

Each enriched packet gets formatted as:

```markdown
---
VIDEO CONTEXT
Title: {video_title}
Summary: {video_summary}
Main Theme: {main_theme}
Key Topics: {topics_list}

CHUNK CONTEXT
Position: {position} (chunk {index+1} of {total})
Timestamp Range: {start} - {end}
Processing Note: {position_instruction}
---

TRANSCRIPT SEGMENT:

{transcript_segment}
```

**Position-Specific Instructions**:

```python
def get_position_instruction(position: str) -> str:
    """Generate position-aware processing instruction."""
    
    instructions = {
        "beginning": (
            "This is the opening segment. Focus on introductions, "
            "context-setting, and initial themes. Note what's being set up."
        ),
        
        "middle": (
            "This is a middle segment. Focus on development of ideas, "
            "detailed explanations, and connections between concepts. "
            "Build on established context."
        ),
        
        "end": (
            "This is the final segment. Focus on conclusions, summaries, "
            "calls-to-action, and final takeaways. Tie themes together."
        ),
        
        "single": (
            "This is the complete content. Analyze comprehensively "
            "from introduction through conclusion."
        )
    }
    
    return instructions.get(position, instructions["middle"])
```

---

## Example: Real Processing Flow

### Input
- Video: "The Chinese AI Iceberg" (27 min, 4,840 words, ~13,310 tokens)
- Patterns to run: `youtube_summary`, `extract_wisdom`

### Phase 1: Global Context Extraction

```bash
# Run metadata extraction (full transcript fits in one call)
cat transcript_full.txt | fabric-ai -p create_micro_summary > global_summary.txt
cat transcript_full.txt | fabric-ai -p extract_main_idea > global_theme.txt
cat transcript_full.txt | fabric-ai -p extract_patterns > global_topics.txt
```

**Results**:
```
global_summary.txt:
"This 27-minute video provides a comprehensive overview of the Chinese AI 
landscape, covering flagship research labs like DeepSeek and Qwen, as well 
as underground powerhouses making significant AI progress."

global_theme.txt:
"Comprehensive landscape analysis of Chinese AI companies and research labs"

global_topics.txt:
DeepSeek, Qwen, ByteDance Seed, Tencent Hunyuan, Kimi K2, Zhipu AI, 
MiniMax, Kuaishou KLING, Baidu ERNIE, OpenBMB, Huawei, SenseTime, 
Shanghai AI Lab, Ant Group, Xiaomi, Meituan
```

### Chunking with Enrichment

**Chunk 1** (0:00 - 12:30, ~6,650 tokens):
```markdown
---
VIDEO CONTEXT
Title: The Chinese AI Iceberg
Summary: This 27-minute video provides a comprehensive overview of the 
Chinese AI landscape, covering flagship research labs like DeepSeek and 
Qwen, as well as underground powerhouses making significant AI progress.
Main Theme: Comprehensive landscape analysis of Chinese AI companies
Key Topics: DeepSeek, Qwen, ByteDance Seed, Tencent Hunyuan, Kimi K2

CHUNK CONTEXT
Position: beginning (chunk 1 of 3)
Timestamp Range: 00:00:00 - 00:12:30
Processing Note: This is the opening segment. Focus on introductions, 
context-setting, and initial themes. Note what's being set up.
---

TRANSCRIPT SEGMENT:

With the top open source AI models now mostly being dominated by 
Chinese AI labs and even closing in on the performance of private 
AI models, I think there really needs to be a rundown on Chinese 
AI developments before the US dude decides to make a diabolical move...
[continues for ~2,400 words]
```

**Chunk 2** (12:00 - 24:15, ~6,650 tokens):
```markdown
---
[Same VIDEO CONTEXT]

CHUNK CONTEXT
Position: middle (chunk 2 of 3)
Timestamp Range: 00:12:00 - 00:24:15
Processing Note: This is a middle segment. Focus on development of ideas, 
detailed explanations, and connections between concepts. Build on 
established context.
---

TRANSCRIPT SEGMENT:

[~2,400 words continuing from DeepSeek through to Noah's Ark Lab]
```

**Chunk 3** (23:45 - 27:06, ~3,300 tokens):
```markdown
---
[Same VIDEO CONTEXT]

CHUNK CONTEXT
Position: end (chunk 3 of 3)
Timestamp Range: 00:23:45 - 00:27:06
Processing Note: This is the final segment. Focus on conclusions, summaries, 
calls-to-action, and final takeaways. Tie themes together.
---

TRANSCRIPT SEGMENT:

[~1,200 words covering final labs and conclusion]
```

### Phase 2: Pattern Processing

**For `youtube_summary` pattern**:
```bash
# Process each enriched packet
cat enriched_packet_001.md | fabric-ai -p youtube_summary > output_001.md
cat enriched_packet_002.md | fabric-ai -p youtube_summary > output_002.md
cat enriched_packet_003.md | fabric-ai -p youtube_summary > output_003.md

# Combine outputs
cat output_001.md output_002.md output_003.md > youtube_summary_combined.md
```

**For `extract_wisdom` pattern**:
```bash
# Same process with different pattern
cat enriched_packet_001.md | fabric-ai -p extract_wisdom > wisdom_001.md
cat enriched_packet_002.md | fabric-ai -p extract_wisdom > wisdom_002.md
cat enriched_packet_003.md | fabric-ai -p extract_wisdom > wisdom_003.md

# Combine outputs
cat wisdom_001.md wisdom_002.md wisdom_003.md > extract_wisdom_combined.md
```

---

## Token Economics

### Cost Analysis for 27-Minute Video

**Phase 1: Global Context** (one-time cost)
```
Full transcript: 13,310 tokens input
├─ create_micro_summary: 13,310 in → 50 out
├─ extract_main_idea: 13,310 in → 20 out
└─ extract_patterns: 13,310 in → 30 out
Total: ~40K tokens input, ~100 tokens output
```

**Phase 2: Chunk Processing** (per pattern)
```
Enriched Packet 1: 6,650 + 85 (metadata) = 6,735 tokens
Enriched Packet 2: 6,650 + 85 = 6,735 tokens
Enriched Packet 3: 3,300 + 85 = 3,385 tokens
Total per pattern: ~16,855 tokens input

For 2 patterns (youtube_summary, extract_wisdom):
Total: ~33,700 tokens input
```

**Grand Total**:
- Phase 1: ~40K tokens
- Phase 2: ~34K tokens
- **Total: ~74K tokens** (vs. naive ~80K without optimization)

**Benefits**:
- Smaller chunks = faster processing (8s vs 30s per call)
- Better rate limit behavior
- Coherent outputs across chunks
- Only ~5% token overhead for massive quality gain

---

## Implementation Architecture

### Component Structure

```
lib/
├── fabric_orchestrator.py      # NEW - Main orchestration logic
├── packet_builder.py           # NEW - Enriched packet construction
├── metadata_extractor.py       # NEW - Phase 1 processing
├── chunker.py                  # UPDATED - Position-aware chunking
├── fabric_processor.py         # UPDATED - Packet processing
├── token_counter.py            # EXISTS - Token utilities
└── exceptions.py               # UPDATED - Orchestration errors

.fabric/{video_id}/
├── transcript_full.txt         # Original transcript
├── metadata/                   # Phase 1 outputs
│   ├── global_summary.txt
│   ├── global_theme.txt
│   └── global_topics.txt
├── packets/                    # Enriched packets
│   ├── packet_001.md
│   ├── packet_002.md
│   └── packet_003.md
└── outputs/                    # Phase 2 outputs
    ├── youtube_summary/
    └── extract_wisdom/
```

---

## Configuration Schema

```yaml
# config.yaml

fabric:
  enabled: true
  
  # Phase 1: Metadata extraction
  metadata_extraction:
    enabled: true
    patterns:
      summary: create_micro_summary      # 1-2 sentence overview
      theme: extract_main_idea           # Core theme
      topics: extract_patterns           # Key entities/topics
    
    # If transcript too large for Phase 1
    max_tokens_for_full: 16000          # Use sampling if larger
    sample_strategy: representative     # "beginning+end" | "representative"
  
  # Chunking settings
  chunking:
    max_tokens_per_chunk: 8000
    overlap_tokens: 200
    strategy: sentence                   # Split on sentences
    
    # Position awareness
    enable_position_instructions: true
    custom_instructions:                 # Optional overrides
      beginning: null
      middle: null
      end: null
  
  # Phase 2: Pattern processing
  patterns:
    - youtube_summary
    - extract_wisdom
  
  # Execution settings
  timeout_per_chunk: 60
  retry_on_failure: true
  max_retries: 2
  
  # Rate limiting
  delay_between_chunks: 0               # Seconds
  delay_between_patterns: 2             # Seconds (be nice to API)
  
  # Cleanup
  keep_temp_files: false                # Delete .fabric/ after success
```

---

## Error Handling & Resilience

### Failure Scenarios

**1. Phase 1 Failure** (metadata extraction)
```python
# Fallback: Use basic metadata from video info
if metadata_extraction_fails:
    fallback_metadata = {
        "summary": f"Video titled '{video_title}'",
        "theme": "Content analysis",
        "topics": extract_from_title_and_tags(video_info)
    }
```

**2. Chunk Processing Timeout**
```python
# Skip chunk, continue with others
if chunk_timeout:
    log_warning(f"Chunk {i} timed out, skipping...")
    outputs.append(f"⚠️ Chunk {i} processing failed")
    continue  # Don't abort entire pipeline
```

**3. Pattern Unavailable**
```python
# Validate patterns exist before processing
available_patterns = get_available_fabric_patterns()
for pattern in config.patterns:
    if pattern not in available_patterns:
        warn(f"Pattern '{pattern}' not found, skipping")
        continue
```

**4. Fabric Command Not Found**
```python
# Graceful degradation
if not fabric_available():
    print("⚠️  Fabric not installed, skipping AI analysis")
    return {}  # Continue with transcript-only output
```

---

## Output Format: Final Markdown

```markdown
---
title: the_chinese_ai_iceberg
url: https://www.youtube.com/watch?v=XFhUI1fphKU
video_id: XFhUI1fphKU
# ... other metadata ...
fabric_analysis: true
fabric_patterns: [youtube_summary, extract_wisdom]
fabric_chunks_processed: 3
fabric_date: '2025-12-08T21:15:00-05:00'
---

# The Chinese AI Iceberg

**Channel:** [bycloud](https://www.youtube.com/channel/...)  
**Published:** 2025-11-01  
**Duration:** 27:06

---

## Description

[video description]

---

## Transcript

[full 4,840-word transcript]

---

## AI Analysis

### YouTube Summary

#### Part 1 of 3 (00:00:00 - 00:12:30)

[Fabric's analysis of beginning segment with position awareness]

**Key Points:**
- [00:01:23] Introduction to Chinese AI landscape
- [00:03:45] DeepSeek's open source dominance
- ...

---

#### Part 2 of 3 (00:12:00 - 00:24:15)

[Fabric's analysis of middle segment]

**Key Points:**
- [00:12:34] ByteDance Seed capabilities
- [00:15:22] Tencent Hunyuan architecture
- ...

---

#### Part 3 of 3 (00:23:45 - 00:27:06)

[Fabric's analysis of final segment with conclusion focus]

**Key Points:**
- [00:24:10] Emerging underground labs
- [00:26:30] Future implications and call to action
- ...

---

### Key Insights & Wisdom

#### Part 1 of 3

# SUMMARY
Chinese AI labs are rapidly advancing open-source models that rival private...

# IDEAS
- DeepSeek's models demonstrate that open-source can compete with closed...
- [more 16-word formatted ideas]

# INSIGHTS
- [refined insights from beginning segment]

---

#### Part 2 of 3

[Same structure for middle segment]

---

#### Part 3 of 3

[Same structure for final segment]

---

## Notes

<!-- User notes -->
```

---

## File Naming Convention

### Preference: Slugified Titles

**User requirement**: Terminal-friendly, underscored/slugified filenames

**Implementation**:
```python
def slugify_title(title: str, max_length: int = 80) -> str:
    """
    Convert video title to filesystem-friendly slug.
    
    Examples:
        "The Chinese AI Iceberg" → "the_chinese_ai_iceberg"
        "DeepSeek V3.2: What's New?" → "deepseek_v3_2_whats_new"
        "🔥 AI Breaks Records!" → "ai_breaks_records"
    """
    import re
    
    # Lowercase
    slug = title.lower()
    
    # Remove emojis and special chars
    slug = re.sub(r'[^\w\s-]', '', slug)
    
    # Replace whitespace with underscores
    slug = re.sub(r'[\s_-]+', '_', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    
    # Truncate if too long
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('_')
    
    return slug

# Usage
filename = f"{upload_date}_{slugify_title(title)}.md"
# Result: "2025-11-01_the_chinese_ai_iceberg.md"
```

**Why**:
- Tab completion in terminal works perfectly
- No escaping spaces in bash commands
- grep/find work without quotes
- Consistent, predictable naming

**Tradeoff**: Less visual appeal in file browsers (but title is beautiful inside the note)

---

## Testing Strategy

### Test Cases

**1. Short Video** (< 8K tokens, single chunk)
```
Input: 5-minute video, 1,500 words
Expected:
  - Phase 1: Extract metadata
  - Phase 2: Single enriched packet (position="single")
  - Output: No "Part X/Y" headers (single continuous output)
Duration: ~30 seconds total
```

**2. Medium Video** (8K-16K tokens, 2 chunks)
```
Input: 15-minute video, 4,000 words
Expected:
  - Phase 1: Extract metadata
  - Phase 2: 2 enriched packets (position="beginning", "end")
  - Output: "Part 1/2" and "Part 2/2" sections
Duration: ~60 seconds total
```

**3. Long Video** (> 16K tokens, 3+ chunks)
```
Input: 30-minute video, 8,000 words
Expected:
  - Phase 1: Extract metadata
  - Phase 2: 4 enriched packets (beginning, middle, middle, end)
  - Output: "Part 1/4" through "Part 4/4" sections
Duration: ~120 seconds total
```

**4. Metadata Extraction Failure**
```
Scenario: Phase 1 patterns fail/timeout
Expected:
  - Fallback to basic metadata (title, tags)
  - Phase 2 still proceeds with minimal context
  - Warning logged but processing continues
```

**5. Chunk Processing Failure**
```
Scenario: One chunk times out in Phase 2
Expected:
  - Skip failed chunk, continue with others
  - Output shows "⚠️ Part 2 processing failed"
  - Other parts still appear in final markdown
```

**6. Multiple Patterns**
```
Input: 3 patterns configured (youtube_summary, extract_wisdom, create_summary)
Expected:
  - All patterns process all chunks
  - Each pattern gets dedicated section in output
  - Total processing time: ~3x single pattern
```

---

## Performance Benchmarks

### Target Metrics

| Video Length | Words | Tokens | Chunks | Patterns | Est. Duration | Target |
|--------------|-------|--------|--------|----------|---------------|--------|
| 5 min | 1,500 | 4K | 1 | 2 | 30s | ✅ |
| 15 min | 4,000 | 11K | 2 | 2 | 60s | ✅ |
| 30 min | 8,000 | 22K | 3 | 2 | 120s | ✅ |
| 60 min | 16,000 | 44K | 6 | 2 | 240s | ⚠️ |

**Key constraint**: Stay under 5 minutes total for 30-minute video (user tolerance threshold)

---

## Future Extensions

### Beyond YouTube (Generalized Packet Processing)

This framework can be applied to:

**1. Podcast Transcripts**
```yaml
metadata_extraction:
  patterns:
    summary: create_micro_summary
    theme: extract_main_idea
    speakers: extract_speakers      # NEW pattern
    topics: extract_patterns
```

**2. Long-Form Articles**
```yaml
chunking:
  strategy: section                 # Split by markdown headers
  preserve_headers: true
```

**3. PDF Documents**
```yaml
metadata_extraction:
  patterns:
    summary: create_academic_summary  # Different pattern
    key_arguments: extract_arguments
    citations: extract_references
```

**4. Multi-Document Analysis**
```yaml
# Process multiple docs, cross-reference in packets
metadata_extraction:
  cross_document:
    enabled: true
    patterns:
      common_themes: compare_and_contrast
```

---

## Open Questions

### For User Decision

1. **Phase 1 Patterns**: 
   - Stick with 3 patterns (summary, theme, topics)?
   - Add more? (speaker detection, sentiment, etc.)

2. **Packet Overhead**:
   - Current ~85 tokens of metadata per chunk acceptable?
   - Want more/less context injected?

3. **Position Instructions**:
   - Use suggested wording for beginning/middle/end?
   - Want custom instructions per pattern?

4. **Rate Limiting**:
   - Add delays between chunks/patterns? (currently 0s)
   - Or rely on Fabric's built-in throttling?

5. **Temp File Cleanup**:
   - Delete `.fabric/` after success (default)?
   - Or keep for debugging/reprocessing?

6. **Failure Behavior**:
   - Continue with partial results if chunks fail?
   - Or abort entire pattern if one chunk fails?

---

## Documentation TODOs

- [ ] Update `ARCHITECTURE.md` with orchestration flow
- [ ] Create `PROMPT_ENGINEERING.md` with packet templates
- [ ] Update `PHASE1C_FABRIC_INTEGRATION.md` with this framework
- [ ] Add examples to `README.md`
- [ ] Document custom pattern creation for Phase 1
- [ ] Create troubleshooting guide for Fabric timeouts

---

## Implementation Checklist

### Phase 1: Metadata Extraction (NEW)
- [ ] `lib/metadata_extractor.py` - Phase 1 orchestration
- [ ] Pattern validation (check patterns exist)
- [ ] Fallback metadata generation
- [ ] Sampling strategy for very large transcripts

### Phase 2: Packet Building (NEW)
- [ ] `lib/packet_builder.py` - Enriched packet construction
- [ ] Position detection logic (beginning/middle/end)
- [ ] Position-specific instruction generation
- [ ] Packet serialization (markdown format)

### Phase 3: Chunking Updates
- [ ] `lib/chunker.py` - Position-aware chunking
- [ ] Optimal chunk size calculation
- [ ] Sentence boundary splitting
- [ ] Overlap handling

### Phase 4: Orchestration
- [ ] `lib/fabric_orchestrator.py` - Main pipeline
- [ ] Two-phase execution flow
- [ ] Error handling and resilience
- [ ] Progress reporting

### Phase 5: Integration
- [ ] Update `yt-obsidian.py` CLI
- [ ] Update `lib/formatter.py` for multi-part outputs
- [ ] Update `config.yaml` schema
- [ ] Filename slugification

### Phase 6: Testing
- [ ] Unit tests for each component
- [ ] Integration tests (short/medium/long videos)
- [ ] Failure scenario tests
- [ ] Performance benchmarks

---

## Success Criteria

This framework is complete when:

✅ **Phase 1 works reliably**
- Extracts meaningful global context
- Gracefully handles failures with fallbacks
- Completes in < 30 seconds for any transcript size

✅ **Phase 2 produces coherent outputs**
- Each chunk shows position awareness
- Beginning chunks focus on setup
- End chunks focus on conclusions
- Combined outputs read naturally

✅ **Performance is acceptable**
- 30-minute video processes in < 2 minutes
- No unnecessary API calls
- Efficient rate limit behavior

✅ **Error handling is robust**
- Partial failures don't abort entire pipeline
- Clear error messages guide user
- Temp files cleaned up on success

✅ **Framework is reusable**
- Can be adapted to non-YouTube content
- Configuration-driven (not hardcoded)
- Well-documented for future extensions

---

**Ready to begin implementation with this framework?**

Next step: Create `lib/metadata_extractor.py` (Phase 1 processing)
