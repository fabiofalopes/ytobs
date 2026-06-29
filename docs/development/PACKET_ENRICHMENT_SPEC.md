# Packet Enrichment & Enhanced Workflow Specification

**Created**: 2025-12-11  
**Updated**: 2025-12-13  
**Status**: SPECIFICATION (Unified Vision)  
**Priority**: HIGH

---

## Executive Summary

This specification unifies two interconnected visions:

1. **Packet Enrichment** (Original): Ensure each Fabric call has full YouTube metadata context
2. **Enhanced Iterative Workflow** (New): Enable dynamic, living pattern selection and vault-aware operations

The goal is to transform `yt` from a "one-shot extraction tool" into a **dynamic content synthesis engine** that:
- Extracts YouTube content as structured Obsidian notes
- Enables iterative pattern discovery and application
- Supports vault-wide operations and analytics
- Creates high-value synthetic data from video content

### The Vision

> "It's almost like a web clip where we do that for YouTube plus have some AI fabric patterns running against the content... Then essentially taking all this content through better lenses."

The workflow should feel **alive**:
- Run `fabric -l` to discover patterns dynamically
- Think "this content would benefit from X pattern" and just add it
- Accumulate insights iteratively without re-processing
- Build a vault of deeply-analyzed YouTube knowledge

### Problems Identified

1. **Missing Context in Packets**: Packets sent to Fabric patterns lack YouTube metadata (channel, tags, description)

2. **No Transcript Refinement**: No preprocessing to fix typos while preserving content

3. **Static Pattern Selection**: Can't dynamically discover and apply new patterns

4. **No Vault Awareness**: Tool operates on single videos, not vault-wide

5. **No Iterative Accumulation**: Can't build on previous analysis without full re-run

---

# PART I: PACKET ENRICHMENT (Foundation)

This section addresses the core infrastructure needed for quality analysis.

---

## Phase A: Enhanced Packet Context (HIGH PRIORITY)

**Goal**: Every chunk sent to Fabric includes full YouTube context for better analysis.

### Current State

**`lib/packet_builder.py`** - `EnrichedPacket` preamble includes:
```
CONTENT CONTEXT:
- Source: {video_title}
- Overview: {video_summary}  ← from Phase 1 AI
- Key Topics: {key_topics}   ← from Phase 1 AI

CHUNK INFORMATION:
- Position, timestamps, processing notes
```

**Missing:**
- Channel name (who is talking)
- Video tags (correct terminology)
- Description excerpt (key terms, links, references)
- Upload date (temporal context)
- Video URL (reference)

### Proposed Changes

#### 1. New `VideoContext` Dataclass

```python
@dataclass
class VideoContext:
    """Raw YouTube metadata context for packet enrichment."""
    video_id: str
    video_url: str
    channel_name: str
    channel_url: str
    upload_date: str  # YYYY-MM-DD
    tags: List[str]
    description_excerpt: str  # First ~150 words
    duration_formatted: str  # HH:MM:SS
```

#### 2. Updated `EnrichedPacket`

Add `video_context: VideoContext` field.

#### 3. Updated Preamble Generation

```markdown
---
VIDEO CONTEXT:
- Channel: {channel_name}
- Published: {upload_date}
- Tags: {tags_csv}  # First 10 tags, comma-separated
- Key Terms: {extracted_terms_from_description}

CONTENT CONTEXT:
- Title: {video_title}
- Overview: {video_summary}
- Key Topics: {key_topics}

CHUNK INFORMATION:
- Position: {position} ({chunk_display})
- Timestamp Range: {start} - {end}
- Processing Note: {position_note}
---
```

### Token Impact Analysis

| Field | Estimated Tokens | Justification |
|-------|-----------------|---------------|
| Channel name | ~5-10 | Short string |
| Upload date | ~5 | Fixed format |
| Tags (10 max) | ~30-50 | CSV of short terms |
| Description excerpt | ~150-200 | First 150 words |
| **Total Addition** | **~200-270** | Acceptable overhead |

**Current preamble**: ~100 tokens  
**Proposed preamble**: ~300-370 tokens  
**Per-chunk overhead increase**: ~200 tokens (acceptable for 8000-token chunks)

### Files to Modify

| File | Changes |
|------|---------|
| `lib/packet_builder.py` | Add `VideoContext`, update `EnrichedPacket`, update `_generate_preamble()`, update `create_packet()` |
| `lib/chunker.py` | Accept `video_info` parameter, pass to `create_packet()` |
| `lib/fabric_orchestrator.py` | Pass `video_info` from `orchestrate()` to chunker |

### Data Flow (After Changes)

```
yt → extract_metadata() → video_info dict
  ↓
fabric_orchestrator.orchestrate(video_info=video_info)
  ↓
chunker.chunk_and_enrich(video_info=video_info)
  ↓
packet_builder.create_packet(video_context=VideoContext.from_dict(video_info))
  ↓
EnrichedPacket.to_fabric_input() → includes full context preamble
```

---

## Phase B: Transcript Refinement Pipeline (MEDIUM PRIORITY)

### Vision

A **preprocessing step** that:
1. Takes raw transcript + YouTube metadata
2. Outputs refined transcript that is:
   - **Word-for-word identical** (content preserved)
   - **Typo-corrected** (using tags/description for correct spellings)
   - **Better formatted** (paragraphs, potential speaker turns)
3. Refined transcript is used for all subsequent analysis

### Key Constraint

> "We want to see the output pretty. It's not never, we want to now change the content of the transcription... at least I want to run for sure a pattern with this exact almost or literally a word by word of the transcript except for typos"

This is **NOT** summarization or paraphrasing. It's cleanup.

### Proposed Implementation

#### New Module: `lib/transcript_refiner.py`

```python
class TranscriptRefiner:
    """Refines transcript without changing content."""
    
    def refine(
        self,
        transcript: str,
        video_title: str,
        channel_name: str,
        tags: List[str],
        description: str
    ) -> str:
        """
        Refine transcript using context for typo correction.
        
        - Fixes capitalization of proper nouns
        - Corrects tech terms using tags as reference
        - Improves paragraph breaks
        - Does NOT change wording, order, or meaning
        """
        ...
```

#### Fabric Pattern: `refine_transcript`

A Fabric pattern that:
- Receives transcript + context (tags, description excerpt)
- Outputs corrected transcript
- System prompt emphasizes: "DO NOT change wording, only fix typos and formatting"

#### Pipeline Position

```
URL → Extract Metadata → Extract Transcript 
    → **REFINE TRANSCRIPT** (Phase 0.5)
    → Phase 1: Global Metadata
    → Chunk → Enrich → Phase 2: Analysis Patterns
```

### Configuration

```yaml
refinement:
  enabled: true
  pattern: "refine_transcript"
  max_input_tokens: 10000  # Truncate if larger
  store_original: true  # Keep original for comparison
```

### Token Considerations for Long Transcripts

For transcripts > 10K tokens:
1. **Option A**: Run refinement in chunks (like analysis patterns)
2. **Option B**: Skip refinement for very long videos
3. **Option C**: Refine first N words, leave rest as-is

Recommendation: **Option B** initially (simpler), with Option A as future enhancement.

---

## Phase C: Always-Run Pattern Infrastructure (LOW PRIORITY)

### Concept

Some patterns should run regardless of mode selection:
- `refine_transcript` - always want clean transcript
- `extract_references` - always want to capture links/citations

### Configuration

```yaml
patterns:
  always_run:
    - refine_transcript
  quick:
    - extract_wisdom
    - summarize
  auto:
    # dynamically selected
  deep:
    # all patterns
```

### Implementation

In `yt` main function:

```python
# Determine patterns to run
selected_patterns = get_patterns_for_mode(mode)

# Merge always-run patterns (deduplicate)
always_patterns = config.patterns.get('always_run', [])
final_patterns = list(set(always_patterns + selected_patterns))
```

---

# PART II: INTERACTIVE WORKFLOW & PROGRESSIVE ANALYSIS

This section specifies the **interactive, navigable workflow** that transforms `yt` into a content synthesis engine. The key principle: **navigation is built into the tool**, not exposed as verbose CLI flags.

---

## Design Philosophy

### Anti-Pattern: Flag Overload

**What we DON'T want:**
```bash
# Too verbose, requires memorization, breaks flow
yt vault list --missing extract_predictions --channel "Lex Fridman"
yt add VIDEO_ID --patterns analyze_personality --suggest --all-suggested
yt patterns search "extract" --category analysis --content-type podcast
```

This approach:
- Requires users to memorize flags
- Breaks the exploratory, "lively" feeling
- Makes the tool feel like work, not discovery

### Design Principle: Interactive Navigation

**What we WANT:**
```
$ ./yt "URL"

The tool guides you. It knows context. It suggests intelligently.
You navigate with simple keystrokes, not verbose commands.
```

The tool should feel like a **conversation**, not a command manual.

---

## Phase D: Unified Interactive Interface (HIGH PRIORITY)

### Core Interaction Model

When you run `yt` with a video URL, the tool enters an **interactive session** that adapts to context:

#### Flow 1: New Video

```
$ ./yt "https://youtube.com/watch?v=XYZ"

📺 The Future of AI - Lex Fridman Podcast #421
   Channel: Lex Fridman | Duration: 2:34:15 | Published: 2024-01-15

🆕 New video. How would you like to process it?

   [1] Quick    - 5 essential patterns (~30s)
   [2] Auto     - Smart selection (~60s)  
   [3] Deep     - Comprehensive (~90s)
   [4] Browse   - Choose patterns manually
   [q] Cancel

   > 
```

If user selects `[4] Browse`:

```
📋 Pattern Browser
   
   Showing: Recommended for podcast/interview content
   
   EXTRACTION (foundational)
   ┌──────────────────────────────────────────────────┐
   │ [x] extract_wisdom      Key insights             │
   │ [x] extract_insights    Actionable takeaways     │
   │ [ ] extract_questions   Questions raised         │
   │ [ ] extract_predictions Future predictions       │
   │ [ ] extract_references  Links and citations      │
   └──────────────────────────────────────────────────┘
   
   ANALYSIS (deeper understanding)
   ┌──────────────────────────────────────────────────┐
   │ [ ] analyze_claims      Verify claims made       │
   │ [ ] analyze_personality Speaker traits           │
   │ [ ] analyze_debate      Argument structure       │
   └──────────────────────────────────────────────────┘
   
   ↑/↓ Navigate | Space: Toggle | /: Search | Enter: Run selected
   Tab: More categories | ?: Help
```

#### Flow 2: Existing Video (Already Processed)

```
$ ./yt "https://youtube.com/watch?v=XYZ"

📺 The Future of AI - Lex Fridman Podcast #421

✅ Already processed (5 patterns)
   └─ Note: ~/vault/youtube/2024-01-15_the-future-of-ai.md

   Patterns run: extract_wisdom, youtube_summary, extract_insights,
                 extract_patterns, extract_main_idea

   What would you like to do?

   [a] Add patterns   - Run additional analysis
   [v] View note      - Open in editor
   [s] Show analysis  - Preview AI outputs
   [r] Re-run         - Full re-analysis
   [q] Done

   > 
```

If user selects `[a] Add patterns`:

```
📋 Add Patterns to "The Future of AI"

   Already run (5): extract_wisdom, youtube_summary, extract_insights...
   
   SUGGESTED NEXT (based on content + what you have)
   ┌──────────────────────────────────────────────────┐
   │ [ ] analyze_personality  "Interesting speaker"   │
   │ [ ] extract_predictions  "Makes future claims"   │
   │ [ ] write_essay          "Rich enough for essay" │
   │ [ ] rate_content         "Get quality score"     │
   └──────────────────────────────────────────────────┘
   
   The suggestions above are ranked by relevance to YOUR content,
   not just generic "extract_*" patterns.
   
   ↑/↓ Navigate | Space: Toggle | Enter: Run | /: Search all
```

### Progressive Pattern Depth

The key insight: **patterns have natural progressions**. After extraction comes analysis. After analysis comes synthesis/creation.

```
LAYER 1: EXTRACTION (run first)
├── extract_wisdom, extract_insights, extract_main_idea
├── extract_patterns, extract_questions
└── extract_references, extract_predictions

LAYER 2: ANALYSIS (run after extraction exists)
├── analyze_claims, analyze_personality
├── analyze_debate, analyze_tech_impact
└── analyze_prose, analyze_risk

LAYER 3: SYNTHESIS (run after analysis exists)  
├── write_essay, create_keynote
├── create_summary (informed by analysis)
└── provide_guidance, rate_content

LAYER 4: CREATIVE (optional, any time)
├── create_art_prompt
├── create_quiz, create_flashcards
└── Custom patterns
```

The tool should **suggest patterns from the appropriate layer** based on what's already run:

```python
def suggest_next_patterns(patterns_run: List[str]) -> List[str]:
    """Suggest patterns based on progression, not just content type."""
    
    has_extraction = any(p.startswith("extract_") for p in patterns_run)
    has_analysis = any(p.startswith("analyze_") for p in patterns_run)
    has_synthesis = any(p in ["write_essay", "create_keynote", "create_summary"] for p in patterns_run)
    
    if not has_extraction:
        # Start with extraction
        return ["extract_wisdom", "extract_insights", "extract_main_idea"]
    
    elif has_extraction and not has_analysis:
        # Ready for analysis
        return ["analyze_claims", "analyze_personality", "analyze_debate"]
    
    elif has_analysis and not has_synthesis:
        # Ready for synthesis
        return ["write_essay", "create_keynote", "rate_content"]
    
    else:
        # Deep mode - suggest unexplored patterns
        return get_unexplored_patterns(patterns_run)
```

---

## Phase E: Reasonable Limits & Bulk Automation (HIGH PRIORITY)

### The Problem

> "I can imagine that for bulk automation... we'll probably want to settle between tops dozens of patterns being run for each video, not to completely destroy or become maniac over such content"

Without limits:
- Interactive use: User might keep adding patterns indefinitely
- Bulk processing: Processing 100 videos × 50 patterns = 5000 API calls = chaos

### Soft Limits for Interactive Mode

The tool should gently guide toward reasonable depth:

```
📋 Add Patterns to "The Future of AI"

   ⚠️  You've run 12 patterns on this video.
   
   That's quite comprehensive! Most videos benefit from 8-15 patterns.
   
   Still want to add more?
   
   [y] Yes, show more patterns
   [n] No, this is good
   [e] Export what I have
```

After ~15 patterns:

```
   ⚠️  This video has 15 patterns - that's thorough!
   
   Additional patterns may have diminishing returns.
   Consider moving to synthesis:
   
   [ ] write_essay      - Synthesize into cohesive essay
   [ ] create_keynote   - Create presentation from insights
   
   Or continue adding extraction/analysis patterns...
```

### Hard Limits for Headless/Bulk Mode

```yaml
# ~/.yt-obsidian/config.yml

limits:
  # Interactive mode (soft limits, can override)
  interactive:
    suggest_stop_at: 12      # Suggest stopping here
    warn_at: 15              # Warn but allow
    max_patterns: 25         # Hard cap
  
  # Headless/bulk mode (hard limits)
  headless:
    max_patterns_per_video: 10   # Hard cap for automation
    max_videos_per_batch: 50     # Prevent runaway bulk jobs
    
  # Bulk channel download mode
  bulk:
    patterns_per_video: 5        # Conservative for scale
    max_concurrent: 3            # Rate limit protection
```

### Bulk Processing Flow

For processing entire channels:

```
$ ./yt --bulk "https://youtube.com/@LexFridman"

📺 Lex Fridman Podcast
   Found: 421 videos | Already processed: 45

   Bulk mode limits:
   - Patterns per video: 5 (quick mode)
   - New videos to process: 376
   - Estimated time: ~3 hours
   - Estimated API calls: ~1,880
   
   [s] Start bulk processing
   [c] Configure (change patterns/limits)
   [p] Preview first 5 videos
   [q] Cancel

   > c

   Bulk Configuration:
   
   Patterns to run on each video:
   [x] extract_wisdom
   [x] youtube_summary  
   [x] extract_insights
   [ ] extract_patterns
   [ ] extract_main_idea
   
   Max patterns per video: [5____]
   Process videos newer than: [2024-01-01]
   
   Save and start? [y/n]
```

---

## Phase F: Vault Awareness (Built Into Navigation)

### Not Separate Commands - Integrated Context

Instead of:
```bash
# Bad: separate commands
yt vault stats
yt vault list --missing extract_predictions
```

The vault awareness is **woven into the interactive flow**:

```
$ ./yt

📚 YouTube Vault
   47 videos processed | 423 pattern runs

   [n] New video      - Process a new URL
   [b] Browse videos  - See what you have
   [g] Gaps           - Find missing patterns
   [s] Statistics     - Vault overview
   [q] Quit

   > g

📊 Pattern Gaps

   These patterns aren't run on many videos:
   
   extract_predictions (3/47 videos)
   ├── Missing on 44 videos
   └── [a] Add to all missing | [p] Preview which videos
   
   analyze_personality (8/47 videos)  
   ├── Missing on 39 videos
   └── [a] Add to all missing | [p] Preview which videos
   
   write_essay (0/47 videos)
   ├── Never run
   └── [a] Add to select videos | [i] What is this pattern?
```

### Quick Actions from Anywhere

The tool maintains context and allows quick jumps:

```
# While browsing a video's patterns:

   [/] Search patterns
   [?] Help
   [~] Back to vault overview  ← Quick jump
   [q] Quit
```

---

## Phase G: Headless Mode for Scripting

While the interactive mode is primary, headless mode exists for automation:

```bash
# Headless: no prompts, uses config defaults
./yt --headless "URL"

# Headless with specific patterns
./yt --headless --patterns extract_wisdom,youtube_summary "URL"

# Headless bulk
./yt --headless --bulk "@channel_url" --limit 50
```

In headless mode:
- No interactive prompts
- Respects hard limits from config
- Outputs JSON for scripting
- Suitable for cron jobs, pipelines

---

## Implementation: Interactive Navigator

### New Module: `lib/navigator.py`

```python
"""Interactive navigation for yt command."""

import sys
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Callable

class Screen(Enum):
    """Navigation screens."""
    MAIN = "main"
    NEW_VIDEO = "new_video"
    EXISTING_VIDEO = "existing_video"  
    PATTERN_BROWSER = "pattern_browser"
    VAULT_OVERVIEW = "vault_overview"
    BULK_CONFIG = "bulk_config"

@dataclass
class NavigatorState:
    """Current navigation state."""
    screen: Screen
    video_id: Optional[str] = None
    video_info: Optional[dict] = None
    selected_patterns: List[str] = None
    patterns_run: List[str] = None

class Navigator:
    """Interactive navigation controller."""
    
    def __init__(self, config, cache, pattern_discovery):
        self.config = config
        self.cache = cache
        self.patterns = pattern_discovery
        self.state = NavigatorState(screen=Screen.MAIN)
    
    def run(self, url: Optional[str] = None):
        """Main navigation loop."""
        if url:
            self._handle_url(url)
        else:
            self._show_main_menu()
        
        while True:
            action = self._get_input()
            if action == 'q':
                break
            self._handle_action(action)
    
    def _handle_url(self, url: str):
        """Handle incoming URL - route to appropriate screen."""
        video_id = extract_video_id(url)
        
        if self.cache.exists(video_id):
            self.state.screen = Screen.EXISTING_VIDEO
            self.state.video_id = video_id
            self.state.patterns_run = self.cache.get(video_id).patterns_run
            self._show_existing_video_menu()
        else:
            self.state.screen = Screen.NEW_VIDEO
            self.state.video_id = video_id
            self._show_new_video_menu()
    
    def _show_pattern_browser(self, context: str = "new"):
        """Show interactive pattern browser."""
        # Get patterns organized by layer/progression
        suggestions = self.patterns.suggest_progressive(
            patterns_run=self.state.patterns_run or [],
            content_type=self._detect_content_type()
        )
        
        # Render browsable list with categories
        self._render_pattern_list(suggestions)
    
    def _suggest_progressive(self, patterns_run: List[str]) -> dict:
        """Suggest patterns based on progression, not just extraction bias."""
        
        layers = {
            "suggested": [],      # Smart suggestions for THIS video
            "extraction": [],     # If not done
            "analysis": [],       # If extraction done
            "synthesis": [],      # If analysis done
            "creative": [],       # Always available
        }
        
        # Detect what layer we're at
        has_extraction = any(p.startswith("extract_") for p in patterns_run)
        has_analysis = any(p.startswith("analyze_") for p in patterns_run)
        
        # Build suggestions based on progression
        if not has_extraction:
            layers["suggested"] = ["extract_wisdom", "extract_insights"]
        elif not has_analysis:
            layers["suggested"] = ["analyze_claims", "analyze_personality"]
        else:
            layers["suggested"] = ["write_essay", "rate_content", "create_keynote"]
        
        return layers
```

### Entry Point Changes: `yt`

```python
def main():
    # ... existing setup ...
    
    # Check if running in headless mode
    if args.headless:
        return run_headless(args, config)
    
    # Interactive mode - use navigator
    from lib.navigator import Navigator
    from lib.pattern_discovery import PatternDiscovery
    
    navigator = Navigator(
        config=config,
        cache=cache,
        pattern_discovery=PatternDiscovery()
    )
    
    # If URL provided, start there; otherwise show main menu
    navigator.run(url=args.url)
```
System: Validate new patterns not already run
         ↓
System: Run only NEW patterns on cached transcript
         ↓
System: Append new sections to existing markdown
         ↓
System: Update cache with new patterns_run
         ↓
Output: "✅ Added 1 pattern to existing note"
```

### Enhanced Cache Structure

Update `lib/cache_manager.py`:

```python
@dataclass
class CacheEntry:
    video_id: str
    video_url: str
    title: str
    upload_date: str
    duration_seconds: int
    transcript_word_count: int
    markdown_path: str
    last_updated: str
    patterns_run: List[str]
    processing_history: List[Dict]
    chunks: Optional[List[Dict]]
    phase1_metadata: Optional[Dict]
    
    # NEW FIELDS for iterative workflow
    transcript_hash: str  # For detecting transcript changes
    content_type: Optional[str]  # "podcast", "lecture", "interview", etc.
    suggested_patterns: List[str]  # AI-suggested patterns not yet run
    pattern_outputs: Dict[str, str]  # pattern_name -> output_text (for re-use)
    
    def get_remaining_suggestions(self) -> List[str]:
        """Get suggested patterns that haven't been run yet."""
        return [p for p in self.suggested_patterns if p not in self.patterns_run]
    
    def can_add_pattern(self, pattern: str) -> bool:
        """Check if pattern can be added (not already run)."""
        return pattern not in self.patterns_run
```

### Transcript Caching

For iterative workflows, we need efficient transcript access:

```python
class TranscriptCache:
    """Manages cached transcripts for efficient re-processing."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "transcripts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, video_id: str, transcript: str) -> Path:
        """Save transcript to cache."""
        path = self.cache_dir / f"{video_id}.txt"
        path.write_text(transcript)
        return path
    
    def load(self, video_id: str) -> Optional[str]:
        """Load transcript from cache."""
        path = self.cache_dir / f"{video_id}.txt"
        if path.exists():
            return path.read_text()
        return None
    
    def exists(self, video_id: str) -> bool:
        """Check if transcript is cached."""
        return (self.cache_dir / f"{video_id}.txt").exists()
```

---

## Phase F: Vault-Aware Operations (MEDIUM PRIORITY)

### Vision

> "It could be interesting to really try and create a solid, almost vault perspective."

The tool should understand the **vault as a whole**:
- What videos have been processed?
- What patterns are most commonly useful?
- What topics are covered?
- Batch operations on multiple videos

### Vault Analytics Interface

#### New Commands

```bash
# Vault overview
yt vault stats

# Output:
# 📚 YouTube Vault Statistics
# ════════════════════════════
# Total videos: 47
# Total patterns run: 423
# Unique patterns used: 18
# Total tokens consumed: 2.4M
# 
# Most used patterns:
#   1. extract_wisdom (47 videos)
#   2. youtube_summary (47 videos)
#   3. extract_insights (45 videos)
#   4. extract_patterns (42 videos)
#   5. analyze_claims (23 videos)
#
# Content types:
#   - podcast: 23 videos
#   - lecture: 15 videos
#   - interview: 6 videos
#   - other: 3 videos
#
# Top channels:
#   1. Lex Fridman Podcast (12 videos)
#   2. 3Blue1Brown (8 videos)
#   3. Two Minute Papers (7 videos)

# List all videos by channel
yt vault list --by-channel

# List videos missing a specific pattern
yt vault list --missing extract_predictions

# Bulk add pattern to all videos
yt vault apply extract_predictions --all
yt vault apply extract_predictions --channel "Lex Fridman Podcast"
yt vault apply extract_predictions --missing  # Only where not run
```

### Vault Manager Module

New module: `lib/vault_manager.py`

```python
class VaultManager:
    """Manages vault-wide operations on YouTube notes."""
    
    def __init__(self, vault_path: Path, cache: CacheManager):
        self.vault_path = vault_path
        self.cache = cache
    
    def get_statistics(self) -> Dict[str, Any]:
        """Generate vault-wide statistics."""
        all_entries = self.cache.list_all()
        
        stats = {
            "total_videos": len(all_entries),
            "total_patterns_run": 0,
            "unique_patterns": set(),
            "total_tokens": 0,
            "pattern_counts": {},
            "channel_counts": {},
            "content_types": {}
        }
        
        for video_id, entry in all_entries:
            for pattern in entry.get("patterns_run", []):
                stats["total_patterns_run"] += 1
                stats["unique_patterns"].add(pattern)
                stats["pattern_counts"][pattern] = stats["pattern_counts"].get(pattern, 0) + 1
            
            # ... aggregate other stats
        
        return stats
    
    def find_videos_missing_pattern(self, pattern: str) -> List[str]:
        """Find videos that haven't run a specific pattern."""
        missing = []
        for video_id, entry in self.cache.list_all():
            if pattern not in entry.get("patterns_run", []):
                missing.append(video_id)
        return missing
    
    def bulk_apply_pattern(
        self, 
        pattern: str, 
        video_ids: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, bool]:
        """Apply a pattern to multiple videos."""
        results = {}
        for i, video_id in enumerate(video_ids):
            if progress_callback:
                progress_callback(i + 1, len(video_ids), video_id)
            
            try:
                # Use iterative append workflow
                success = self._apply_pattern_to_video(video_id, pattern)
                results[video_id] = success
            except Exception as e:
                results[video_id] = False
        
        return results
```

---

## Phase G: Content Synthesis Engine (FUTURE VISION)

### The Ultimate Goal

> "More than just getting information, we're trying to really get a lot of perspective, a lot of thinking, a lot of creative writing, and a lot of interesting things—the commentary, a lot of analysis, obviously, and content distillation."

The end state is a **synthesis engine** that:

1. **Extracts**: Raw transcript + metadata from YouTube
2. **Refines**: Clean, typo-corrected, formatted transcript
3. **Analyzes**: Multiple perspectives via Fabric patterns
4. **Synthesizes**: Combined insights from all analyses
5. **Creates**: New content (essays, summaries, study guides) from synthesis
6. **Connects**: Links to related content in vault

### Synthesis Pipeline

```
YouTube Video
     ↓
┌────────────────────────────────────────────────────────────┐
│ EXTRACTION LAYER                                           │
│ - Transcript (raw)                                         │
│ - Metadata (channel, tags, description)                    │
│ - Thumbnails, chapters, comments (future)                  │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ REFINEMENT LAYER                                           │
│ - Typo correction (using metadata context)                 │
│ - Speaker attribution (if multi-party)                     │
│ - Paragraph formatting                                     │
│ - Timestamp synchronization                                │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ ANALYSIS LAYER                                             │
│ - Core extraction (wisdom, insights, patterns)             │
│ - Deep analysis (claims, personality, debate structure)    │
│ - Creative outputs (essays, art prompts, keynotes)         │
│ - Fact-checking (references, claims verification)          │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ SYNTHESIS LAYER                                            │
│ - Cross-pattern synthesis (combine all insights)           │
│ - Vault connections (link to related notes)                │
│ - Knowledge graph nodes (topics, people, concepts)         │
│ - Study materials (flashcards, quizzes)                    │
└────────────────────────────────────────────────────────────┘
     ↓
📄 Rich Obsidian Note
   - Structured front matter
   - Refined transcript
   - Multiple analysis sections
   - Connected to vault knowledge
```

### Synthesis Patterns (Future Fabric Patterns)

Custom patterns for this workflow:

```
synthesize_video         - Combine all pattern outputs into unified summary
connect_to_vault         - Suggest links to existing notes
create_study_guide       - Generate study materials from content
extract_knowledge_nodes  - Extract entities for knowledge graph
cross_reference_claims   - Compare claims to known facts in vault
```

---

# PART III: UNIFIED IMPLEMENTATION PLAN

## Implementation Roadmap (Revised)

### Sprint 1: Foundation (Packet Enrichment)
**Time**: 2-3 hours | **Priority**: CRITICAL

1. `lib/packet_builder.py`: Add VideoContext, update preamble
2. `lib/chunker.py`: Accept and pass video_info
3. `lib/fabric_orchestrator.py`: Flow video_info through pipeline
4. Test: Verify packets include YouTube metadata

### Sprint 2: Pattern Discovery
**Time**: 3-4 hours | **Priority**: HIGH

1. Create `lib/pattern_discovery.py`
2. Add `yt patterns` subcommand
3. Add pattern search and categorization
4. Add pattern description lookup
5. Test: Verify pattern discovery works

### Sprint 3: Iterative Workflow Enhancement
**Time**: 4-5 hours | **Priority**: HIGH

1. Enhance `lib/cache_manager.py` with new fields
2. Create `lib/transcript_cache.py`
3. Add `yt status` and `yt add` commands
4. Implement smart pattern suggestions
5. Test: Verify iterative append workflow

### Sprint 4: Transcript Refinement
**Time**: 4-6 hours | **Priority**: MEDIUM

1. Create `refine_transcript` Fabric pattern
2. Create `lib/transcript_refiner.py`
3. Integrate into pipeline (Phase 0.5)
4. Add refinement config options
5. Test: Verify refinement preserves content

### Sprint 5: Vault Operations
**Time**: 4-5 hours | **Priority**: MEDIUM

1. Create `lib/vault_manager.py`
2. Add `yt vault` subcommand family
3. Implement statistics and analytics
4. Implement bulk operations
5. Test: Verify vault-wide operations

### Sprint 6: Always-Run Patterns & Polish
**Time**: 2-3 hours | **Priority**: LOW

1. Add always_run config
2. Merge pattern lists properly
3. Documentation updates
4. End-to-end integration testing

---

## Testing Strategy

### Unit Tests

| Module | Test Cases |
|--------|------------|
| `packet_builder.py` | VideoContext creation, preamble generation |
| `pattern_discovery.py` | List, search, categorize, suggest |
| `cache_manager.py` | New fields, iterative updates |
| `transcript_cache.py` | Save, load, hash verification |
| `vault_manager.py` | Statistics, bulk operations |

### Integration Tests

1. **Full Pipeline**: URL → enriched packets with VideoContext
2. **Iterative Append**: Add patterns to existing note
3. **Pattern Discovery**: Search and describe patterns
4. **Vault Operations**: Stats and bulk apply

### End-to-End Tests

1. Process new video with `--quick`
2. Check status with `yt status`
3. Add patterns with `yt add --patterns`
4. Verify vault stats with `yt vault stats`

---

## Configuration Schema (Enhanced)

```yaml
# ~/.yt-obsidian/config.yml (v4.0)

# ============================================================================
# ANALYSIS MODE
# ============================================================================
analysis_mode: auto  # auto, quick, deep, expert

# ============================================================================
# MODEL SELECTION  
# ============================================================================
model: best  # best, fast, quality, or specific name

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
output_dir: null  # Default: $OBSVAULT/youtube
open_in_editor: false
keep_temp_files: false
verbose: false

# ============================================================================
# PACKET ENRICHMENT (NEW - Phase A)
# ============================================================================
packets:
  include_channel: true
  include_tags: true
  max_tags: 10
  include_description: true
  description_words: 150

# ============================================================================
# TRANSCRIPT REFINEMENT (NEW - Phase B)
# ============================================================================
refinement:
  enabled: true
  pattern: "refine_transcript"
  max_input_tokens: 10000
  store_original: true

# ============================================================================
# PATTERN MANAGEMENT (NEW - Phase D/E)
# ============================================================================
patterns:
  # Always run these patterns
  always_run:
    - refine_transcript
  
  # Quick mode patterns
  quick:
    - extract_wisdom
    - youtube_summary
    - extract_insights
    - extract_patterns
    - extract_main_idea
  
  # Auto mode settings
  auto:
    min_priority: high
    max_patterns: 15
    show_recommendations: false
  
  # Deep mode settings
  deep:
    min_priority: optional
    max_patterns: 25

# ============================================================================
# CACHE SETTINGS (NEW - Phase E)
# ============================================================================
cache:
  store_transcripts: true
  store_pattern_outputs: true
  auto_suggest_patterns: true

# ============================================================================
# VAULT SETTINGS (NEW - Phase F)
# ============================================================================
vault:
  track_statistics: true
  auto_link_related: false  # Future: auto-suggest related notes
  knowledge_graph: false    # Future: extract to knowledge graph

# ============================================================================
# EXPERT MODE SETTINGS
# ============================================================================
expert:
  fabric_command: fabric-ai
  timeout_per_pattern: 120
  chunk_size: 8000
```

---

## Command Reference (Enhanced)

### Core Commands

| Command | Description |
|---------|-------------|
| `yt URL` | Process video (default: auto mode) |
| `yt --quick URL` | Fast analysis (5 patterns) |
| `yt --deep URL` | Full analysis (all patterns) |
| `yt --preview URL` | Show recommendations only |
| `yt --patterns P1 P2 URL` | Run specific patterns |

### Cache & Status Commands

| Command | Description |
|---------|-------------|
| `yt status VIDEO_ID` | Show what's been analyzed |
| `yt add VIDEO_ID --patterns P1 P2` | Add patterns to existing |
| `yt add VIDEO_ID --suggest` | Add suggested patterns |
| `yt --list-processed` | List all cached videos |
| `yt --force URL` | Re-analyze ignoring cache |

### Pattern Discovery Commands

| Command | Description |
|---------|-------------|
| `yt patterns` | List all available patterns |
| `yt patterns search KEYWORD` | Search patterns |
| `yt patterns describe PATTERN` | Show pattern details |
| `yt patterns --category TYPE` | List by category |
| `yt patterns suggest --content-type TYPE` | Get suggestions |

### Vault Commands

| Command | Description |
|---------|-------------|
| `yt vault stats` | Vault-wide statistics |
| `yt vault list` | List all videos |
| `yt vault list --missing PATTERN` | Videos missing pattern |
| `yt vault apply PATTERN --all` | Bulk add pattern |
| `yt vault apply PATTERN --channel NAME` | Add to channel videos |

---

## Appendix: Current Code References

### packet_builder.py Key Lines

```python
# Line 53-68: to_fabric_input() - generates preamble + content
# Line 70-96: _generate_preamble() - current preamble template
# Line 167-214: create_packet() - factory function
```

### chunker.py Key Lines

```python
# Line 36-120: chunk_and_enrich() - main workflow
# Line 160-193: _create_packets_from_chunks() - packet creation
```

### fabric_orchestrator.py Key Lines

```python
# Line 136-270: orchestrate() - main orchestration
# Line 201-212: chunk_transcript() call - needs video_info
```

---

## Open Questions

1. **Description Excerpt**: How to extract "key terms" from description?
   - Decision: First 150 words (simple, effective)

2. **Tag Limit**: How many tags to include?
   - Decision: First 10 (configurable)

3. **Refinement Chunking**: Handle long transcripts?
   - Decision: Skip refinement for >10K tokens initially

4. **Cache Invalidation**: When refinement settings change?
   - Decision: Offer `--force-refine` flag

5. **Pattern Output Storage**: Store raw outputs for re-synthesis?
   - Decision: Yes, optional via config

6. **Vault Linking**: Auto-suggest related notes?
   - Decision: Future phase, manual links first

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Add VideoContext to packets | Provides terminology/attribution context | 2025-12-11 |
| Limit description to 150 words | Balance context vs token cost | 2025-12-11 |
| Limit tags to 10 | Most relevant tags are first | 2025-12-11 |
| Refinement is optional/configurable | Not all users want preprocessing overhead | 2025-12-11 |
| Store transcripts in cache | Enables efficient iterative workflow | 2025-12-13 |
| Add pattern discovery commands | Supports dynamic pattern selection | 2025-12-13 |
| Vault-wide operations | Supports batch processing and analytics | 2025-12-13 |
| 6-sprint roadmap | Balanced between quick wins and full vision | 2025-12-13 |

---

## Success Criteria

### Phase Complete When:

**Sprint 1 (Foundation)**:
- [ ] Packets include VideoContext
- [ ] Preamble shows channel, tags, description excerpt
- [ ] Token overhead < 300 per chunk

**Sprint 2 (Pattern Discovery)**:
- [ ] `yt patterns` lists all patterns
- [ ] `yt patterns search` works
- [ ] `yt patterns describe` shows system prompt

**Sprint 3 (Iterative Workflow)**:
- [ ] `yt status VIDEO_ID` shows analysis history
- [ ] `yt add --patterns` appends without re-processing
- [ ] Smart suggestions based on content type

**Sprint 4 (Transcript Refinement)**:
- [ ] Refinement pattern created
- [ ] Refinement preserves word count (±5%)
- [ ] Refined transcript flows to analysis

**Sprint 5 (Vault Operations)**:
- [ ] `yt vault stats` shows vault analytics
- [ ] `yt vault list --missing` finds gaps
- [ ] `yt vault apply` does bulk operations

**Sprint 6 (Polish)**:
- [ ] Always-run patterns work
- [ ] Documentation complete
- [ ] All tests pass
