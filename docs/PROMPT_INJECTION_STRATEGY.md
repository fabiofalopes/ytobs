# Fabric Prompt Injection Strategy

**Status**: Design Phase  
**Created**: 2025-12-08  
**Purpose**: Define how to inject chunking context into Fabric patterns without breaking them

---

## Problem Statement

Fabric patterns have carefully-crafted system prompts that end with:
```
# INPUT

INPUT:
[user content goes here]
```

**Challenge**: We need to inject chunking metadata (position, global context) into the input in a way that:
1. Respects the pattern's existing structure and instructions
2. Provides position awareness without overwhelming the model
3. Works universally across all patterns (youtube_summary, extract_wisdom, etc.)
4. Keeps token overhead minimal (~85 tokens)

---

## Fabric Pattern Structure Analysis

### Pattern Format (Universal)

All Fabric patterns follow this structure:

```markdown
# IDENTITY and PURPOSE
[Who you are and what you do]

# STEPS (or ## STEPS)
[Detailed processing instructions]

# OUTPUT INSTRUCTIONS (or ## OUTPUT INSTRUCTIONS)
[Format requirements, constraints]

# INPUT (or ## INPUT)

INPUT:
```

**Key Insight**: The `INPUT:` marker is where user content begins. This is our injection point.

### Example: youtube_summary

```markdown
# IDENTITY and PURPOSE
You are an AI assistant specialized in creating concise, informative 
summaries of YouTube video content based on transcripts...

## STEPS
- Carefully read through the entire transcript to understand the overall content...
- Identify the main topic and purpose of the video
- Note key points, important concepts, and significant moments...

## OUTPUT INSTRUCTIONS
- Only output Markdown
- Begin with a brief overview of the video's main topic and purpose
- Include timestamps in [HH:MM:SS] format before each key point...

## INPUT

INPUT:
```

### Example: extract_wisdom

```markdown
# IDENTITY and PURPOSE
You extract surprising, insightful, and interesting information from text content...

# STEPS
- Extract a summary of the content in 25 words...
- Extract 20 to 50 of the most surprising, insightful, and/or interesting ideas...

# OUTPUT INSTRUCTIONS
- Only output Markdown.
- Write the IDEAS bullets as exactly 16 words.
- Extract at least 25 IDEAS from the content.

# INPUT

INPUT:
```

---

## Injection Strategy: Contextual Preamble

### Core Principle

**Inject a structured preamble IMMEDIATELY AFTER `INPUT:`** that:
1. Declares this is a chunk of larger content
2. Provides minimal global context
3. States position and role in the sequence
4. Maintains Markdown formatting for readability

**Format**:
```markdown
INPUT:

---
CONTENT CONTEXT:
- Source: [Video Title]
- Overview: [1-2 sentence summary]
- Key Topics: [comma-separated topics]

CHUNK INFORMATION:
- Position: [beginning|middle|end] (chunk X of Y)
- Timestamp Range: [HH:MM:SS - HH:MM:SS]
- Processing Note: [position-specific instruction]

---

[actual transcript chunk]
```

### Token Budget

- Section headers: ~20 tokens
- Global context: ~50 tokens
- Chunk info: ~25 tokens
- Separators: ~10 tokens
- **Total overhead: ~105 tokens per chunk**

Percentage of 8K chunk: **1.3%** (acceptable)

---

## Implementation Design

### Packet Structure

```python
@dataclass
class EnrichedPacket:
    """Context-enriched chunk for Fabric processing."""
    
    # Metadata (from Phase 1)
    video_title: str
    video_summary: str          # 1-2 sentences
    key_topics: str             # Comma-separated
    
    # Chunk info
    chunk_id: str               # "chunk_001"
    chunk_index: int            # 0, 1, 2
    total_chunks: int           # 3
    position: str               # "beginning", "middle", "end", "single"
    timestamp_range: Tuple[str, str]  # ("00:00:00", "00:12:30")
    
    # Content
    transcript_segment: str
    
    def to_fabric_input(self) -> str:
        """
        Format packet as Fabric-compatible input.
        
        Returns the complete string that goes after "INPUT:"
        """
        preamble = self._generate_preamble()
        return f"{preamble}\n\n{self.transcript_segment}"
    
    def _generate_preamble(self) -> str:
        """Generate contextual preamble."""
        
        # Position-specific note
        position_note = self._get_position_note()
        
        return f"""---
CONTENT CONTEXT:
- Source: {self.video_title}
- Overview: {self.video_summary}
- Key Topics: {self.key_topics}

CHUNK INFORMATION:
- Position: {self.position} (chunk {self.chunk_index + 1} of {self.total_chunks})
- Timestamp Range: {self.timestamp_range[0]} - {self.timestamp_range[1]}
- Processing Note: {position_note}

---"""
    
    def _get_position_note(self) -> str:
        """Generate position-specific processing note."""
        
        notes = {
            "single": (
                "This is the complete content. Analyze comprehensively."
            ),
            
            "beginning": (
                "This is the opening segment. Focus on introductions, setup, "
                "and initial themes. Establish context for what follows."
            ),
            
            "middle": (
                "This is a middle segment continuing from previous content. "
                "Focus on development, details, and progression of established themes."
            ),
            
            "end": (
                "This is the final segment concluding previous content. "
                "Focus on conclusions, resolutions, and final takeaways."
            )
        }
        
        return notes.get(self.position, notes["middle"])
```

---

## Example: Real Packet Generation

### Inputs

**Phase 1 Metadata** (extracted once):
```python
video_title = "The Chinese AI Iceberg"
video_summary = "This video explores the Chinese AI landscape, covering flagship labs like DeepSeek and Qwen, plus underground research powerhouses."
key_topics = "DeepSeek, Qwen, ByteDance, Tencent Hunyuan, Kimi K2, MiniMax, Chinese AI development"
```

**Chunk Info**:
```python
chunk_1 = EnrichedPacket(
    video_title=video_title,
    video_summary=video_summary,
    key_topics=key_topics,
    chunk_id="chunk_001",
    chunk_index=0,
    total_chunks=3,
    position="beginning",
    timestamp_range=("00:00:00", "00:12:30"),
    transcript_segment="With the top open source AI models now..."
)
```

### Generated Fabric Input

When calling `chunk_1.to_fabric_input()`:

```markdown
---
CONTENT CONTEXT:
- Source: The Chinese AI Iceberg
- Overview: This video explores the Chinese AI landscape, covering flagship labs like DeepSeek and Qwen, plus underground research powerhouses.
- Key Topics: DeepSeek, Qwen, ByteDance, Tencent Hunyuan, Kimi K2, MiniMax, Chinese AI development

CHUNK INFORMATION:
- Position: beginning (chunk 1 of 3)
- Timestamp Range: 00:00:00 - 00:12:30
- Processing Note: This is the opening segment. Focus on introductions, setup, and initial themes. Establish context for what follows.

---

With the top open source AI models now mostly being dominated by Chinese AI labs and even closing in on the performance of private AI models, I think there really needs to be a rundown on Chinese AI developments before the US dude decides to make a diabolical move. And what's a better way to compile all these information than diving in from the most popular commercial research labs down to the underground powerhouse that are also making incredible AI progress themselves...

[continues for ~2,400 words]
```

### How This Works with Patterns

#### Pattern: youtube_summary

**Full prompt sent to model**:
```markdown
# IDENTITY and PURPOSE
You are an AI assistant specialized in creating concise, informative 
summaries of YouTube video content based on transcripts...

## STEPS
- Carefully read through the entire transcript to understand the overall content...
- Identify the main topic and purpose of the video
[...full pattern instructions...]

## OUTPUT INSTRUCTIONS
- Only output Markdown
- Begin with a brief overview of the video's main topic and purpose
- Include timestamps in [HH:MM:SS] format...

## INPUT

INPUT:
---
CONTENT CONTEXT:
- Source: The Chinese AI Iceberg
- Overview: This video explores the Chinese AI landscape...
- Key Topics: DeepSeek, Qwen, ByteDance...

CHUNK INFORMATION:
- Position: beginning (chunk 1 of 3)
- Timestamp Range: 00:00:00 - 00:12:30
- Processing Note: This is the opening segment. Focus on introductions...

---

With the top open source AI models now mostly being dominated by...
[rest of transcript chunk]
```

**Key**: The preamble acts as a "stage-setting" header that the model reads BEFORE processing the transcript. It doesn't interfere with the pattern's instructions—it enhances them by providing context.

#### Pattern: extract_wisdom

**Same approach**:
```markdown
# IDENTITY and PURPOSE
You extract surprising, insightful, and interesting information...

# STEPS
- Extract a summary of the content in 25 words...
- Extract 20 to 50 of the most surprising ideas...

# OUTPUT INSTRUCTIONS
- Write the IDEAS bullets as exactly 16 words.
- Extract at least 25 IDEAS from the content.

# INPUT

INPUT:
---
CONTENT CONTEXT:
[same preamble as above]
---

[transcript chunk]
```

The `extract_wisdom` pattern still extracts ideas, but now it:
- Knows this is chunk 1 of 3 (the beginning)
- Understands the broader video context
- Can reference the global topics in its analysis

---

## Position-Specific Behavior

### Single Chunk (< 8K tokens)

```python
position = "single"
note = "This is the complete content. Analyze comprehensively."
```

**Result**: Pattern processes normally, no chunking awareness needed.

### Beginning Chunk

```python
position = "beginning"
note = "This is the opening segment. Focus on introductions, setup, and initial themes. Establish context for what follows."
```

**Effect on youtube_summary**:
- Model emphasizes introductory content
- Extracts setup and context-setting moments
- Notes themes being established

**Effect on extract_wisdom**:
- IDEAS focus on foundational concepts introduced
- INSIGHTS note what's being set up for development
- QUOTES capture introductory statements

### Middle Chunk

```python
position = "middle"
note = "This is a middle segment continuing from previous content. Focus on development, details, and progression of established themes."
```

**Effect on youtube_summary**:
- Model builds on established context (from CONTENT CONTEXT)
- Focuses on development and details
- Connects to key topics mentioned in preamble

**Effect on extract_wisdom**:
- IDEAS capture developmental concepts
- INSIGHTS note how themes progress
- Avoids redundant "introductory" content

### End Chunk

```python
position = "end"
note = "This is the final segment concluding previous content. Focus on conclusions, resolutions, and final takeaways."
```

**Effect on youtube_summary**:
- Model emphasizes conclusions
- Extracts final takeaways and calls-to-action
- Ties themes together

**Effect on extract_wisdom**:
- IDEAS focus on conclusions and implications
- INSIGHTS capture final synthesis
- RECOMMENDATIONS emphasize actionable takeaways

---

## Testing Strategy

### Test 1: Verify Non-Interference

**Goal**: Ensure preamble doesn't break pattern output format

```bash
# Test with single chunk (no chunking logic)
echo "Test transcript about AI" | fabric-ai -p youtube_summary

# Test with preamble injected
cat << EOF | fabric-ai -p youtube_summary
---
CONTENT CONTEXT:
- Source: Test Video
- Overview: A test video about AI.
- Key Topics: artificial intelligence, machine learning

CHUNK INFORMATION:
- Position: single (chunk 1 of 1)
- Timestamp Range: 00:00:00 - 00:05:00
- Processing Note: This is the complete content. Analyze comprehensively.

---

Test transcript about AI and machine learning concepts...
EOF
```

**Expected**: Both outputs follow youtube_summary format (headings, timestamps, structure).

### Test 2: Position Awareness

**Goal**: Verify position affects content focus

```bash
# Beginning chunk
cat beginning_packet.md | fabric-ai -p youtube_summary > output_beginning.md

# Middle chunk (same pattern)
cat middle_packet.md | fabric-ai -p youtube_summary > output_middle.md

# End chunk (same pattern)
cat end_packet.md | fabric-ai -p youtube_summary > output_end.md
```

**Expected**:
- Beginning output emphasizes introductions, setup
- Middle output emphasizes development, details
- End output emphasizes conclusions, takeaways

### Test 3: Global Context Utilization

**Goal**: Verify model uses CONTENT CONTEXT

**Approach**: Include a key topic in global context that appears in chunk.

```markdown
CONTENT CONTEXT:
- Key Topics: DeepSeek, Qwen, ByteDance

[chunk mentions "DeepSeek's new model"]
```

**Expected**: Model recognizes DeepSeek as a key topic (from context) and highlights it appropriately, rather than treating it as an unknown entity.

---

## Implementation Checklist

### Phase 1: Packet Builder

- [ ] `lib/packet_builder.py` - Create EnrichedPacket class
- [ ] Implement `to_fabric_input()` method
- [ ] Implement `_generate_preamble()` method
- [ ] Implement `_get_position_note()` method
- [ ] Position detection logic (single/beginning/middle/end)

### Phase 2: Integration

- [ ] Update `lib/fabric_orchestrator.py` to use packets
- [ ] Pass `packet.to_fabric_input()` to fabric-ai stdin
- [ ] Test with real patterns (youtube_summary, extract_wisdom)
- [ ] Verify output format preserved

### Phase 3: Validation

- [ ] Test: Preamble doesn't break pattern outputs
- [ ] Test: Position awareness affects content focus
- [ ] Test: Global context is utilized by model
- [ ] Test: Token overhead is acceptable (~105 tokens)

---

## Token Overhead Analysis

### Preamble Size Breakdown

```markdown
---                                                    # 3 tokens
CONTENT CONTEXT:                                       # 3 tokens
- Source: The Chinese AI Iceberg                       # 8 tokens
- Overview: This video explores the Chinese AI         # ~15 tokens
  landscape, covering flagship labs like DeepSeek...
- Key Topics: DeepSeek, Qwen, ByteDance...            # ~12 tokens

CHUNK INFORMATION:                                     # 3 tokens
- Position: beginning (chunk 1 of 3)                   # 8 tokens
- Timestamp Range: 00:00:00 - 00:12:30                # 10 tokens
- Processing Note: This is the opening segment...      # ~25 tokens

---                                                    # 3 tokens
```

**Total: ~90 tokens** (slightly under initial 105 estimate)

### Cost Per Video (27-minute, 3 chunks)

**Phase 1** (metadata extraction, one-time):
```
Full transcript: 13,310 tokens
Run 3 patterns: 40K tokens input
```

**Phase 2** (chunk processing):
```
Chunk 1: 6,650 + 90 (preamble) = 6,740 tokens
Chunk 2: 6,650 + 90 = 6,740 tokens
Chunk 3: 3,300 + 90 = 3,390 tokens

Per pattern: 16,870 tokens
For 2 patterns: 33,740 tokens
```

**Total: 73,740 tokens** (~74K)

**Overhead from preambles: 270 tokens** (0.37% of total)

---

## Alternative Strategies Considered

### ❌ Strategy 1: Modify Pattern Files

**Idea**: Edit `system.md` files to include chunking instructions.

**Why rejected**:
- Requires maintaining custom pattern forks
- Breaks on Fabric updates (`fabric --update` overwrites)
- Not portable across patterns

### ❌ Strategy 2: Append After Transcript

**Idea**: Put preamble AFTER the transcript chunk.

```
INPUT:
[transcript chunk]

---
NOTE: This is chunk 1 of 3...
```

**Why rejected**:
- Model may not "see" context before processing content
- Many patterns instruct "extract from input" (looks backward)
- Position note comes too late to affect early processing

### ✅ Strategy 3: Preamble Before Content (CHOSEN)

**Why chosen**:
- Non-invasive (doesn't modify patterns)
- Model sees context BEFORE processing content
- Universal across all patterns
- Minimal token overhead
- Easy to implement and test

---

## Success Criteria

This strategy succeeds if:

✅ **Pattern outputs remain valid**
- youtube_summary still produces timestamped summaries
- extract_wisdom still produces IDEAS/INSIGHTS/QUOTES sections
- No format breakage

✅ **Position awareness is evident**
- Beginning chunks emphasize introductions
- End chunks emphasize conclusions
- Middle chunks focus on development

✅ **Global context is utilized**
- Model references key topics from preamble
- Summaries maintain awareness of video theme
- Chunks don't feel isolated

✅ **Token overhead is acceptable**
- ~90 tokens per chunk (1.1% of 8K chunk)
- No measurable quality degradation
- Processing time remains under 10s per chunk

---

## Next Steps

1. **Implement `lib/packet_builder.py`** (30 min)
   - EnrichedPacket class
   - Preamble generation
   - Position detection

2. **Test preamble with real patterns** (30 min)
   - youtube_summary
   - extract_wisdom
   - Verify format preservation

3. **Integrate into orchestrator** (1 hour)
   - Update fabric_orchestrator.py
   - Pass packets to fabric-ai
   - Handle position detection

4. **Validate position awareness** (30 min)
   - Generate 3-chunk test case
   - Verify beginning/middle/end behavior
   - Check global context utilization

**Total: ~2.5 hours**

---

**Ready to implement `lib/packet_builder.py`?**
