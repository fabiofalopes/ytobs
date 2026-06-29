# Phase 1C: Fabric AI Integration - Implementation Plan

**Status**: Planning  
**Created**: 2025-12-08  
**Estimated**: 4-6 hours implementation + 1-2 hours testing

---

## Overview

Integrate [Fabric AI](https://github.com/danielmiessler/fabric) pattern system to automatically generate AI-powered analysis and summaries of YouTube transcripts. This builds on Phase 1B (transcript extraction) by adding semantic understanding and structured insights.

### User Requirements

1. **Default behavior**: Auto-run Fabric patterns after transcript extraction
2. **Multiple patterns**: Run configurable set of patterns (not just one)
3. **Smart chunking**: Handle transcripts > 16K tokens without breaking API endpoints
4. **Configuration**: User-editable config file (not hardcoded)
5. **Optional**: Can be disabled via CLI flag

### Key Constraints

- Fabric runs as external CLI tool (`fabric-ai` command)
- LLM endpoints can timeout/exhaust with large inputs
- Need efficient one-shot processing when possible
- Results appended to markdown (organized sections)

---

## Research Findings

### Available Fabric Patterns

Total: **259 patterns** (as of 2025-12-08)

**Recommended for YouTube analysis**:
- `youtube_summary` - Structured summary with timestamps
- `extract_wisdom` - Key ideas, insights, quotes, facts
- `create_summary` - Concise general summary
- `extract_insights` - Refined abstract insights
- `extract_ideas` - Specific actionable ideas
- `analyze_tech_impact` - Technology assessment (for tech videos)

**Custom patterns available**:
User has custom patterns in `~/projetos/hub/.myscripts/fabric-custom-patterns/`

### Token Analysis

**Test Results** (GPT-4 encoding):
- Tokens/Word ratio: ~2.75 (4,840 words = ~13,310 tokens)
- Target limit: **16,000 tokens** (safe margin for most LLMs)
- Transcript word count captured in front matter

**Current file**:
```
Words: 4,840
Est. Tokens: ~13,310 (fits in one shot)
```

### Fabric Command Structure

```bash
# Basic usage
fabric-ai -p <pattern_name> < input.txt

# With streaming (for progress)
fabric-ai -p <pattern_name> -s < input.txt

# With specific model
fabric-ai -p <pattern_name> -m <model> < input.txt

# Current config
Models available: Groq, Ollama, OpenRouter
Default pattern behavior: streaming enabled
```

### Pattern Output Structure

**youtube_summary**:
```markdown
Brief overview paragraph

## Key Points
- [00:01:23] Point with timestamp
- [00:05:45] Another point

## Main Themes
- Theme 1
- Theme 2

## Conclusion
Final takeaway
```

**extract_wisdom**:
```markdown
# SUMMARY
25-word summary

# IDEAS
- Exactly 16-word formatted idea bullets (25-50 items)

# INSIGHTS
- Refined 16-word insights (10-20 items)

# QUOTES
- Direct quotes with speaker attribution

# HABITS
- Personal habits mentioned (16 words each)

# FACTS
- Surprising facts (16 words each)

# REFERENCES
- Tools, books, projects mentioned

# ONE-SENTENCE TAKEAWAY
15-word essence

# RECOMMENDATIONS
- Actionable recommendations (16 words each)
```

---

## Architecture Design

### Component Structure

```
lib/
├── fabric_integration.py   # NEW - Fabric wrapper and orchestration
├── token_counter.py        # NEW - Token counting utilities
├── formatter.py            # UPDATED - Add AI analysis sections
├── transcript.py           # NO CHANGE
├── extractor.py            # NO CHANGE
└── exceptions.py           # UPDATED - Add FabricError

config.yaml                 # NEW - User configuration
yt-obsidian.py             # UPDATED - CLI flags
```

### Configuration File (`config.yaml`)

```yaml
# Fabric AI Integration Configuration
fabric:
  enabled: true  # Master switch
  
  # Patterns to run (in order)
  patterns:
    - youtube_summary
    - extract_wisdom
  
  # Token limits
  token_limit: 16000  # Max tokens per API call
  chunk_overlap: 500  # Overlap between chunks (for context)
  
  # Processing strategy
  chunking_strategy: hierarchical  # or 'sequential'
  
  # Execution settings
  streaming: true  # Show progress
  timeout: 60  # Seconds per pattern call
  
  # Model override (optional)
  model: null  # Use Fabric's default if null
  
  # Retry settings
  max_retries: 2
  retry_delay: 5  # Seconds
```

### Markdown Output Structure

```markdown
---
[existing front matter]
fabric_analysis: true
fabric_patterns: [youtube_summary, extract_wisdom]
fabric_date: '2025-12-08T20:49:00-05:00'
---

# [Title]

[metadata sections]

---

## Transcript

[full transcript]

---

## AI Analysis

### YouTube Summary

[fabric youtube_summary output]

---

### Key Insights

[fabric extract_wisdom output]

---

## Notes

<!-- User notes -->
```

---

## Token Handling Strategy

### Strategy 1: Hierarchical Chunking (Recommended)

**For transcripts > 16K tokens:**

1. **Split transcript into chunks** (~12K tokens each, 500 overlap)
2. **Process each chunk** with pattern
3. **Combine chunk outputs**
4. **Run pattern again on combined output** (meta-summary)

**Advantages**:
- Preserves full context across chunks
- Final output is coherent
- Works with any pattern

**Example**:
```
27-minute video → 35K tokens
├─ Chunk 1 (0:00-12:00) → 12K tokens → Summary 1
├─ Chunk 2 (11:30-23:00) → 12K tokens → Summary 2  (30s overlap)
├─ Chunk 3 (22:30-27:06) → 11K tokens → Summary 3
└─ Combine summaries → 8K tokens → Final meta-summary
```

### Strategy 2: Sequential Processing (Alternative)

**For transcripts > 16K tokens:**

1. **Split transcript into chunks**
2. **Process each chunk** separately
3. **Concatenate outputs** (no meta-summary)

**Advantages**:
- Simpler implementation
- Faster (no meta-summary step)

**Disadvantages**:
- May lose coherence across chunks
- Duplicate insights

---

## Implementation Plan

### Phase 1: Core Infrastructure (2 hours)

#### 1.1: Token Counter Utility (`lib/token_counter.py`)

```python
"""Token counting utilities for chunking decisions."""
import tiktoken
from typing import List, Tuple

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def chunk_text(
    text: str, 
    max_tokens: int = 16000, 
    overlap: int = 500
) -> List[Tuple[str, int, int]]:
    """
    Split text into chunks with token limits.
    
    Returns list of (chunk_text, start_idx, end_idx)
    """
    # Implementation: split by paragraphs/sentences
    # Track token counts
    # Add overlap
    pass

def estimate_processing_time(token_count: int) -> float:
    """Estimate API call duration based on tokens."""
    # ~1-2 seconds per 1K tokens (conservative)
    return (token_count / 1000) * 2
```

**Tests**:
- ✅ Count tokens matches GPT-4 encoding
- ✅ Chunks stay under limit
- ✅ Overlap preserves context

---

#### 1.2: Fabric Integration (`lib/fabric_integration.py`)

```python
"""Fabric AI pattern integration."""
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .token_counter import count_tokens, chunk_text
from .exceptions import FabricError

@dataclass
class FabricConfig:
    """Fabric configuration."""
    enabled: bool = True
    patterns: List[str] = None
    token_limit: int = 16000
    chunk_overlap: int = 500
    strategy: str = "hierarchical"
    streaming: bool = True
    timeout: int = 60
    model: Optional[str] = None
    max_retries: int = 2
    retry_delay: int = 5

def run_fabric_pattern(
    pattern: str,
    input_text: str,
    config: FabricConfig
) -> str:
    """
    Run a single Fabric pattern on input text.
    
    Handles retries and error reporting.
    """
    # Build command
    cmd = ["fabric-ai", "-p", pattern]
    if config.streaming:
        cmd.append("-s")
    if config.model:
        cmd.extend(["-m", config.model])
    
    # Execute with timeout
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=config.timeout,
            check=False
        )
        
        if result.returncode != 0:
            raise FabricError(
                f"Pattern '{pattern}' failed: {result.stderr}"
            )
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        raise FabricError(
            f"Pattern '{pattern}' timed out after {config.timeout}s"
        )
    except FileNotFoundError:
        raise FabricError(
            "fabric-ai command not found. Install: brew install fabric-ai"
        )

def process_with_chunking(
    pattern: str,
    transcript: str,
    config: FabricConfig
) -> str:
    """
    Process large transcript with hierarchical chunking.
    """
    # Count tokens
    token_count = count_tokens(transcript)
    
    if token_count <= config.token_limit:
        # One-shot processing
        return run_fabric_pattern(pattern, transcript, config)
    
    # Chunk processing
    chunks = chunk_text(
        transcript, 
        max_tokens=config.token_limit, 
        overlap=config.chunk_overlap
    )
    
    print(f"Processing {len(chunks)} chunks...")
    
    # Process each chunk
    chunk_outputs = []
    for i, (chunk_text, _, _) in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)}...")
        output = run_fabric_pattern(pattern, chunk_text, config)
        chunk_outputs.append(output)
    
    # Hierarchical: Meta-summary
    if config.strategy == "hierarchical":
        combined = "\n\n---\n\n".join(chunk_outputs)
        combined_tokens = count_tokens(combined)
        
        if combined_tokens > config.token_limit:
            # Outputs too large, chunk again (rare)
            print("  Creating meta-summary (outputs large)...")
            return process_with_chunking(pattern, combined, config)
        
        print("  Creating final meta-summary...")
        return run_fabric_pattern(pattern, combined, config)
    
    # Sequential: Just concatenate
    return "\n\n---\n\n".join(chunk_outputs)

def run_fabric_analysis(
    transcript: str,
    config: FabricConfig
) -> Dict[str, str]:
    """
    Run all configured patterns on transcript.
    
    Returns dict: {pattern_name: output}
    """
    if not config.enabled:
        return {}
    
    if not config.patterns:
        return {}
    
    results = {}
    
    for pattern in config.patterns:
        print(f"Running Fabric pattern: {pattern}")
        try:
            output = process_with_chunking(pattern, transcript, config)
            results[pattern] = output
        except FabricError as e:
            print(f"  ⚠️  {e}")
            # Continue with other patterns
    
    return results
```

**Tests**:
- ✅ Single pattern execution
- ✅ Error handling (command not found, timeout)
- ✅ Chunking for large inputs
- ✅ Multiple patterns sequentially

---

### Phase 2: Integration (1.5 hours)

#### 2.1: Configuration Loading

```python
# In lib/fabric_integration.py

def load_config(config_path: Path = None) -> FabricConfig:
    """Load Fabric config from YAML file."""
    if config_path is None:
        config_path = Path.cwd() / "config.yaml"
    
    if not config_path.exists():
        # Return defaults
        return FabricConfig(patterns=["youtube_summary"])
    
    import yaml
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    fabric_data = data.get("fabric", {})
    return FabricConfig(**fabric_data)
```

#### 2.2: Update Formatter (`lib/formatter.py`)

```python
def format_fabric_analysis(
    fabric_results: Dict[str, str]
) -> str:
    """Format Fabric AI analysis section."""
    if not fabric_results:
        return ""
    
    sections = ["---\n\n## AI Analysis\n"]
    
    pattern_titles = {
        "youtube_summary": "YouTube Summary",
        "extract_wisdom": "Key Insights & Wisdom",
        "create_summary": "Summary",
        "extract_insights": "Deep Insights",
        "extract_ideas": "Ideas & Concepts"
    }
    
    for pattern, output in fabric_results.items():
        title = pattern_titles.get(pattern, pattern.replace("_", " ").title())
        sections.append(f"### {title}\n\n{output}\n\n---\n")
    
    return "\n".join(sections)

def generate_markdown(
    info: Dict,
    transcript_text: str = None,
    transcript_meta: Dict = None,
    fabric_results: Dict[str, str] = None
) -> str:
    """Generate complete markdown (updated)."""
    # ... existing code ...
    
    # Add transcript section
    if transcript_text:
        markdown.append("\n---\n\n## Transcript\n")
        markdown.append(transcript_text)
    
    # Add Fabric analysis
    if fabric_results:
        markdown.append(format_fabric_analysis(fabric_results))
    
    # ... existing notes/metadata sections ...
```

#### 2.3: Update CLI (`yt-obsidian.py`)

```python
import argparse
from lib.fabric_integration import (
    load_config, 
    run_fabric_analysis, 
    FabricError
)

def main():
    parser = argparse.ArgumentParser()
    # ... existing args ...
    
    # Fabric options
    parser.add_argument(
        "--no-fabric",
        action="store_true",
        help="Disable Fabric AI analysis"
    )
    parser.add_argument(
        "--fabric-patterns",
        type=str,
        help="Comma-separated list of patterns (overrides config)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.cwd() / "config.yaml",
        help="Path to config file"
    )
    
    args = parser.parse_args()
    
    # ... extract metadata + transcript ...
    
    # Fabric analysis
    fabric_results = {}
    if transcript_text and not args.no_fabric:
        config = load_config(args.config)
        
        # CLI override
        if args.fabric_patterns:
            config.patterns = args.fabric_patterns.split(",")
        
        if config.enabled and config.patterns:
            print("\n🤖 Running Fabric AI analysis...")
            fabric_results = run_fabric_analysis(
                transcript_text, 
                config
            )
    
    # Generate markdown
    markdown = formatter.generate_markdown(
        info,
        transcript_text,
        transcript_meta,
        fabric_results
    )
```

---

### Phase 3: Testing (1 hour)

#### Test Cases

**1. Short video (< 16K tokens)**
```bash
./yt-obsidian.py "https://youtube.com/watch?v=SHORT_VIDEO"
# Expected: One-shot Fabric processing, < 10s
```

**2. Long video (> 16K tokens)**
```bash
./yt-obsidian.py "https://youtube.com/watch?v=LONG_VIDEO"
# Expected: Chunking triggered, progress shown
```

**3. Multiple patterns**
```bash
./yt-obsidian.py \
  --fabric-patterns "youtube_summary,extract_wisdom,create_summary" \
  "URL"
# Expected: 3 sections in output
```

**4. Disable Fabric**
```bash
./yt-obsidian.py --no-fabric "URL"
# Expected: No AI analysis section
```

**5. Fabric not installed**
```bash
# Rename fabric-ai temporarily
mv /opt/homebrew/bin/fabric-ai /opt/homebrew/bin/fabric-ai.bak
./yt-obsidian.py "URL"
# Expected: Clear error message, transcript still saved
mv /opt/homebrew/bin/fabric-ai.bak /opt/homebrew/bin/fabric-ai
```

**6. Pattern timeout**
```bash
# Test with very large transcript + low timeout
# Expected: Timeout error, other patterns still run
```

---

## Front Matter Updates

Add these fields when Fabric runs:

```yaml
fabric_analysis: true
fabric_patterns: [youtube_summary, extract_wisdom]
fabric_date: '2025-12-08T20:49:00-05:00'
fabric_token_count: 13310
fabric_chunks_used: 1
```

---

## Error Handling

### Error Types

```python
class FabricError(Exception):
    """Base Fabric error."""
    pass

class FabricNotFoundError(FabricError):
    """fabric-ai command not found."""
    pass

class FabricTimeoutError(FabricError):
    """Pattern execution timeout."""
    pass

class FabricPatternError(FabricError):
    """Pattern execution failed."""
    pass
```

### User Messages

**Fabric not installed**:
```
⚠️  Fabric AI not found. Install with:
    brew install fabric-ai
Continuing without AI analysis...
```

**Pattern timeout**:
```
⚠️  Pattern 'youtube_summary' timed out (60s limit)
    Try shorter transcript or increase timeout in config.yaml
Continuing with other patterns...
```

**Pattern failed**:
```
⚠️  Pattern 'extract_wisdom' failed: [error details]
Continuing with other patterns...
```

---

## Performance Estimates

### Processing Times

| Transcript Length | Tokens | Strategy | Est. Time |
|-------------------|--------|----------|-----------|
| 5 minutes | ~3,500 | One-shot | 5-10s |
| 15 minutes | ~10,000 | One-shot | 15-20s |
| 30 minutes | ~20,000 | Chunked (2) | 45-60s |
| 60 minutes | ~40,000 | Chunked (4) | 90-120s |

**Per pattern**. Multiple patterns run sequentially.

---

## Future Enhancements (Phase 2+)

### Out of Scope for Phase 1C

1. **Parallel pattern execution** - Run multiple patterns concurrently
2. **Pattern caching** - Store results to avoid re-running
3. **Custom pattern creation** - User-defined patterns
4. **Interactive pattern selection** - TUI for choosing patterns
5. **Fabric server mode** - Long-running server for faster execution
6. **Smart pattern selection** - Choose patterns based on video content/category
7. **Result comparison** - Compare outputs across models

---

## Dependencies

### New Requirements

```txt
# Add to requirements.txt
tiktoken>=0.5.0        # Token counting
PyYAML>=6.0.1          # Config file parsing
```

### External Tools

- `fabric-ai` (Homebrew): Already installed
- Fabric patterns: Already configured (`~/.config/fabric/`)

---

## Open Questions

1. **Default patterns**: Which 2-3 patterns should be default?
   - Candidate: `youtube_summary` + `extract_wisdom`
   - User preference?

2. **Chunk overlap**: 500 tokens enough? Too much?
   - Test with real videos

3. **Streaming output**: Show Fabric progress or silent?
   - Currently: progress messages enabled
   - User preference?

4. **Model selection**: Use Fabric's default or specify?
   - Current: Use Fabric's configured default
   - Allow CLI override?

5. **Pattern failure behavior**: Continue or abort?
   - Current: Continue with other patterns
   - Store error in front matter?

---

## Success Criteria

Phase 1C is complete when:

- ✅ `config.yaml` controls Fabric behavior
- ✅ CLI flags `--no-fabric` and `--fabric-patterns` work
- ✅ Transcripts < 16K tokens process one-shot
- ✅ Transcripts > 16K tokens chunk correctly
- ✅ Multiple patterns run sequentially
- ✅ Errors handled gracefully (Fabric not found, timeouts)
- ✅ Output markdown includes AI analysis sections
- ✅ Tests pass for all scenarios
- ✅ Documentation updated (README, ARCHITECTURE)

---

## Implementation Timeline

**Day 1 (4 hours)**:
- Token counter utility (30 min)
- Fabric integration core (2 hours)
- Config loading (30 min)
- Formatter updates (1 hour)

**Day 2 (3 hours)**:
- CLI updates (1 hour)
- Testing suite (1 hour)
- Documentation (1 hour)

**Total**: 7 hours

---

## Next Steps

1. **Review this plan** - User approval/modifications
2. **Answer open questions** - User decisions
3. **Create config.yaml** - Default settings
4. **Implement token_counter.py**
5. **Implement fabric_integration.py**
6. **Update formatter.py**
7. **Update CLI**
8. **Test all scenarios**
9. **Update documentation**

---

**Ready to proceed with implementation?**
