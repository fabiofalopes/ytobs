# YouTube-Obsidian System Restructure
## Three-Component Architecture Specification v1.1

**Status**: Specification Updated | **Research Phase for Component 2**  
**Date**: 2026-02-03  
**Philosophy**: Simple tools that do one thing well, composable via pipes

---

## Executive Summary

After extensive reflection, we're **separating the monolithic youtube-obsidian tool into focused components**:

1. **obs-yt** - YouTube-to-Obsidian wrapper (simple, no flags by default)
2. **fabric-mcp** (working title) - Pattern runner / MCP server (research phase)
3. **Ideas & Notes** - LLM proxy concepts (collection of ideas, not a component yet)

**Key Changes from v1.0**:
- Component 1 renamed from `yt` to `obs-yt` (clearer purpose: YouTube → Obsidian)
- Component 2 enters **research phase** - investigate existing Fabric tools, MCP servers
- Component 3 is now just **ideas collection** - not an active component
- Better integration of `txrefine` as pipeable tool

**Why**: The current system tries to handle YouTube extraction, transcript refinement, pattern selection, chunking, rate limiting, and content generation all in one tool. This creates complexity, brittleness, and prevents each part from being optimized independently.

**New Approach**: Unix philosophy - small tools that compose via pipes. Each component can be developed, tested, and used independently.

---

## Component 1: obs-yt - YouTube-to-Obsidian Wrapper

### Purpose
Extract YouTube video metadata and transcript for Obsidian notes. Nothing else.

### Philosophy
- **Zero flags by default** - Just `obs-yt <url>`
- **Clean output** - Structured data that can be piped
- **No AI, no patterns, no chunking** - Pure extraction
- **Integrated refinement** - `txrefine` logic built-in, not separate tool
- **Obsidian-ready** - Output structured for Obsidian vault organization

### Interface

```bash
# Default: Extract and output JSON to stdout
obs-yt "https://youtube.com/watch?v=XYZ"
# → {"title": "...", "transcript": "...", "metadata": {...}}

# Pipe to pattern runner (future)
obs-yt "https://youtube.com/watch?v=XYZ" | fabric-mcp --range 3-7

# Raw mode (skip refinement)
obs-yt --raw "https://youtube.com/watch?v=XYZ"

# Output to Obsidian vault directly
obs-yt --vault ~/Documents/Obsidian "https://youtube.com/watch?v=XYZ"

# Process entire channel (future)
obs-yt --channel "https://youtube.com/c/ChannelName"

# Show help
obs-yt --help
```

### Output Format

```json
{
  "video_id": "jNQXAC9IVRw",
  "url": "https://youtube.com/watch?v=jNQXAC9IVRw",
  "title": "Me at the zoo",
  "channel": "jawed",
  "upload_date": "2005-04-23",
  "duration": 19,
  "description": "The first video on YouTube...",
  "tags": ["zoo", "elephants", "first"],
  "transcript": {
    "raw": "Alright, so here we are in front of the elephants...",
    "refined": "Alright, so here we are in front of the elephants...",
    "refinement_applied": true,
    "corrections": [
      {"original": "cloth", "corrected": "Claude", "confidence": 0.98, "context": "AI tools"}
    ],
    "language": "en",
    "type": "manual",
    "word_count": 45
  },
  "statistics": {
    "view_count": 280000000,
    "like_count": 15000000
  },
  "obsidian": {
    "suggested_filename": "2005-04-23-me-at-the-zoo.md",
    "suggested_tags": ["youtube", "jawed", "zoo", "first"],
    "suggested_folder": "youtube/jawed"
  }
}
```

### Implementation

**File**: `youtube-obsidian/obs-yt` (simplified from current version)

```python
#!/usr/bin/env python3
"""
obs-yt - YouTube to Obsidian

Extracts YouTube video metadata and transcript.
Outputs clean JSON for piping to other tools or direct Obsidian integration.
"""

import sys
import json
import argparse
from pathlib import Path
from lib.extractor import extract_metadata
from lib.transcript_refiner import refine_transcript

def main():
    parser = argparse.ArgumentParser(description="Extract YouTube video to Obsidian-ready format")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument("--raw", action="store_true", help="Skip transcript refinement")
    parser.add_argument("--vault", help="Obsidian vault path (creates note directly)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    args = parser.parse_args()
    
    # Extract
    result = extract_metadata(args.url)
    
    # Refine transcript (unless --raw)
    if not args.raw and result.get("transcript"):
        raw_transcript = result["transcript"]["raw"]
        refined = refine_transcript(raw_transcript, result)
        result["transcript"]["refined"] = refined["text"]
        result["transcript"]["refinement_applied"] = True
        result["transcript"]["corrections"] = refined["corrections"]
    
    # Add Obsidian metadata
    result["obsidian"] = generate_obsidian_metadata(result)
    
    # Output
    output = json.dumps(result, indent=2)
    
    if args.vault:
        # Create Obsidian note directly
        create_obsidian_note(result, args.vault)
    elif args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)

def generate_obsidian_metadata(result):
    """Generate Obsidian-specific metadata."""
    from datetime import datetime
    
    title = result.get("title", "Untitled")
    upload_date = result.get("upload_date", datetime.now().strftime("%Y-%m-%d"))
    channel = result.get("channel", "unknown")
    
    # Slugify title
    slug = title.lower().replace(" ", "-")[:50]
    
    return {
        "suggested_filename": f"{upload_date}-{slug}.md",
        "suggested_tags": ["youtube", channel] + result.get("tags", [])[:3],
        "suggested_folder": f"youtube/{channel}"
    }

def create_obsidian_note(result, vault_path):
    """Create Obsidian markdown note directly."""
    vault = Path(vault_path)
    meta = result["obsidian"]
    
    # Create folder structure
    note_dir = vault / meta["suggested_folder"]
    note_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate markdown
    md_content = generate_markdown(result)
    
    # Write note
    note_path = note_dir / meta["suggested_filename"]
    with open(note_path, 'w') as f:
        f.write(md_content)
    
    print(f"Created Obsidian note: {note_path}", file=sys.stderr)

def generate_markdown(result):
    """Generate Obsidian markdown from result."""
    lines = []
    
    # Frontmatter
    lines.append("---")
    lines.append(f"title: {result['title']}")
    lines.append(f"channel: {result['channel']}")
    lines.append(f"date: {result['upload_date']}")
    lines.append(f"video_id: {result['video_id']}")
    lines.append(f"tags: {result['obsidian']['suggested_tags']}")
    lines.append("---")
    lines.append("")
    
    # Header
    lines.append(f"# {result['title']}")
    lines.append("")
    lines.append(f"**Channel:** {result['channel']}")
    lines.append(f"**URL:** {result['url']}")
    lines.append("")
    
    # Transcript
    if result.get("transcript"):
        lines.append("## Transcript")
        lines.append("")
        transcript_text = result["transcript"].get("refined") or result["transcript"]["raw"]
        lines.append(transcript_text)
        lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    main()
```

### Key Changes from Current

1. **Rename**: `yt` → `obs-yt` (clearer purpose)
2. **Remove**: All pattern orchestration, chunking, cache management, fabric integration
3. **Keep**: URL validation, metadata extraction, transcript extraction
4. **Add**: Integrated transcript refinement (txrefine logic built-in)
5. **Add**: Obsidian-specific metadata generation
6. **Add**: Direct Obsidian vault integration (`--vault` flag)
7. **Output**: JSON by default (for piping), markdown with `--vault`

### Transcript Refinement Integration

The `txrefine` logic is now **built into obs-yt**, not a separate tool:

```python
# lib/transcript_refiner.py (integrated)

def refine_transcript(raw_text: str, video_metadata: dict) -> dict:
    """
    Refine raw ASR transcript.
    
    Returns:
        {
            "text": "refined transcript",
            "corrections": [
                {"original": "cloth", "corrected": "Claude", "confidence": 0.98}
            ],
            "refinement_metadata": {...}
        }
    """
    # Apply domain-specific corrections
    # Use video title/tags for context
    # Conservative approach: only high-confidence corrections
    pass
```

**Why integrate txrefine?**
- It's always needed for quality transcripts
- Simpler than separate tool
- Can use video metadata for context-aware corrections
- Still pipeable: `obs-yt --raw` gives raw, default gives refined

### Dependencies

```
yt-dlp
requests
```

---

## Component 2: fabric-mcp - Pattern Runner (Research Phase)

### Status: 🔍 Research Required

**Before building anything, we need to research:**

1. **Fabric AI tool current state** - What's new? What exists?
2. **Existing MCP servers** - Is there already a Fabric MCP server?
3. **Community tools** - What have others built around Fabric?
4. **MCP architecture** - Should this be an MCP server?

### Research Questions

```
□ What is Fabric AI's current feature set? (Check: github.com/danielmiessler/fabric)
□ Are there existing Fabric MCP servers? (Search: "fabric mcp server")
□ What patterns exist in the community?
□ How do modern MCP servers work? (Check: modelcontextprotocol.io)
□ Can we leverage existing tools rather than building from scratch?
```

### Potential Approaches

**Option A: MCP Server**
- Expose Fabric patterns as MCP tools
- Can be called by Claude Desktop, OpenCode, etc.
- Standardized protocol
- More integrations possible

**Option B: Standalone CLI**
- Simple command-line tool
- Pipeable: `obs-yt <url> | fabric-mcp --range 3-7`
- No dependencies on MCP protocol
- Easier to develop

**Option C: Hybrid**
- CLI tool that can also run as MCP server
- Best of both worlds
- More complex

### Interface (Draft - Subject to Research)

```bash
# If standalone CLI:
cat content.txt | fabric-mcp --range 3-7
obs-yt "https://youtube.com/watch?v=XYZ" | fabric-mcp --patterns extract_wisdom

# If MCP server:
# Would be called by agent/IDE through MCP protocol
```

### Decision Required

**Before implementing Component 2, we must:**

1. Research Fabric AI current state
2. Check for existing MCP servers
3. Decide: MCP vs CLI vs Hybrid
4. Only then write code

**Research Output**: Update this spec with findings

---

## Component 3: Ideas & Notes (Not a Component)

### What This Is
A collection of ideas, research notes, and concepts - **not an active component**.

### LLM Proxy Ideas

**Concept**: Route requests across multiple free LLM providers to avoid rate limits.

**Challenges Identified**:
- Complex authentication across providers
- Different rate limits, context windows, models
- Hard to make transparent/drop-in
- Many existing solutions (OpenRouter, etc.)

**Status**: Interesting idea, but:
- Not immediately needed
- Complex to implement well
- May already exist
- **Defer until Components 1 & 2 are working**

### Other Ideas

1. **YouTube Channel Processing**
   - Download all videos from a channel
   - Batch process transcripts
   - Create structured Obsidian vault
   - **Note**: Future feature for obs-yt

2. **Pattern Effectiveness Tracking**
   - Learn which patterns work best
   - User feedback integration
   - **Note**: Future feature for Component 2

3. **txrefine as Standalone Tool**
   - Even though integrated into obs-yt, could be separate
   - Pipeable transcript refinement
   - **Note**: Low priority, obs-yt integration is enough for now

### Where These Live

```
.myscripts/
├── youtube-obsidian/           # Component 1: obs-yt
├── fabric-mcp/                 # Component 2: (research phase)
└── ideas/                        # Component 3: Ideas & notes
    ├── llm-proxy-concepts.md
    ├── youtube-channel-processing.md
    ├── pattern-effectiveness-tracking.md
    └── README.md
```

---

## Migration Plan (Updated)

### Phase 1: Simplify obs-yt (Session 1)

**Goal**: Strip down to extraction-only, integrate txrefine

**Actions**:
1. Rename `yt` → `obs-yt`
2. Remove all pattern orchestration code
3. Remove chunking, caching, fabric integration
4. Integrate txrefine logic into transcript processing
5. Add Obsidian metadata generation
6. Change output to JSON (for piping)

**Files to Modify**:
- `youtube-obsidian/yt` → `youtube-obsidian/obs-yt` (rewrite)
- `lib/extractor.py` - Keep as-is
- `lib/transcript.py` - Keep as-is
- `lib/transcript_refiner.py` - Create from txrefine logic

**Files to Deprecate** (move to `_deprecated/`):
- `lib/fabric_orchestrator.py`
- `lib/chunker.py`
- `lib/packet_builder.py`
- `lib/cache_manager.py`
- `lib/incremental_writer.py`
- `lib/metadata_extractor.py`
- `lib/rate_limiter.py`
- Complex CLI flags

### Phase 2: Research Component 2 (Session 2)

**Goal**: Research Fabric ecosystem, decide on architecture

**Actions**:
1. Research Fabric AI current state
2. Search for existing MCP servers
3. Check community tools
4. Document findings
5. Decide: MCP vs CLI vs Hybrid

**Output**: Research document + updated spec

### Phase 3: Implement Component 2 (Session 3-4)

**Goal**: Build pattern runner (based on research)

**Actions**:
1. Create `fabric-mcp/` directory
2. Implement based on research findings
3. Add pattern selection logic
4. Implement organized output structure
5. Test piping: `obs-yt <url> | fabric-mcp`

### Phase 4: Integration & Cleanup (Session 5)

**Goal**: Ensure components work together, clean up

**Actions**:
1. Test end-to-end: `obs-yt <url> | fabric-mcp --range 3-7`
2. Update all documentation
3. Move deprecated files to `_deprecated/`
4. Create usage examples

---

## Usage Examples (Target State)

### Example 1: Simple YouTube to Obsidian

```bash
# Extract and create Obsidian note
obs-yt --vault ~/Documents/Obsidian "https://youtube.com/watch?v=XYZ"

# Result: Creates ~/Documents/Obsidian/youtube/channel/YYYY-MM-DD-title.md
```

### Example 2: Extract and Pipe to Pattern Runner

```bash
# Extract and analyze (future, after Component 2 built)
obs-yt "https://youtube.com/watch?v=XYZ" | fabric-mcp --range 3-7

# Result: Creates ./output/20260203-143022-xyz-video/
#   ├── extract_wisdom.md
#   ├── summary.md
#   ├── extract_ideas.md
#   └── metadata.json
```

### Example 3: Raw Extraction

```bash
# Get raw transcript without refinement
obs-yt --raw "https://youtube.com/watch?v=XYZ"

# Result: JSON with raw transcript only
```

### Example 4: Process Any Content

```bash
# Analyze article (future, after Component 2 built)
cat article.txt | fabric-mcp --range 3-7

# Result: Organized analysis in timestamped folder
```

---

## Directory Structure (After Migration)

```
.myscripts/
├── youtube-obsidian/           # Component 1: obs-yt
│   ├── obs-yt                  # Main script (simplified)
│   ├── lib/
│   │   ├── extractor.py        # Metadata extraction
│   │   ├── transcript.py       # Transcript handling
│   │   ├── transcript_refiner.py  # Integrated refinement
│   │   └── validator.py        # URL validation
│   ├── requirements.txt
│   └── README.md
│
├── fabric-mcp/                 # Component 2: (research phase)
│   ├── README.md               # Research findings
│   └── (implementation TBD after research)
│
├── ideas/                      # Component 3: Ideas & notes
│   ├── llm-proxy-concepts.md
│   ├── youtube-channel-processing.md
│   └── README.md
│
└── _deprecated/                # Old code
    └── youtube-obsidian-v3/    # Current complex version
        ├── lib/                # All old modules
        └── README.md
```

---

## Success Criteria

### Component 1 (obs-yt)
- [ ] `obs-yt <url>` outputs clean JSON
- [ ] Transcript refinement works by default
- [ ] `--raw` flag gives unrefined transcript
- [ ] `--vault` flag creates Obsidian note directly
- [ ] No flags needed for basic usage
- [ ] Can pipe to other tools

### Component 2 (fabric-mcp)
- [ ] Research completed
- [ ] Architecture decided (MCP vs CLI vs Hybrid)
- [ ] Implementation started (if research shows it's needed)
- [ ] Can be called via pipes from obs-yt
- [ ] Creates organized output directories

### Integration
- [ ] `obs-yt <url> | [future pattern runner]` works
- [ ] Output is organized and useful
- [ ] No chunking complexity
- [ ] Simple, predictable behavior

---

## Next Steps

1. **Review this updated specification**
2. **Begin Phase 1**: Simplify obs-yt (rename, strip down, integrate txrefine)
3. **Begin Phase 2**: Research Fabric ecosystem
4. **Update spec** with research findings before building Component 2

---

## Document Information

**Version**: 1.1  
**Last Updated**: 2026-02-03  
**Author**: AI Assistant  
**Status**: Ready for Implementation (Component 1), Research Phase (Component 2)  

**Related Documents**:
- `CONTEXT.md` - Current project context
- `EXTRACT_PATTERNS_ENGINE_SPEC.md` - Previous spec (superseded)
- `THREE_COMPONENT_ARCHITECTURE_SPEC.md` - v1.0 (superseded)

**Next Action**: 
1. Begin Phase 1: Simplify obs-yt
2. Begin Phase 2: Research Fabric ecosystem
