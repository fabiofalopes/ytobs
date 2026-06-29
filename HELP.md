# YouTube-Obsidian (yt) - Complete Command Reference

Extract YouTube videos to AI-enhanced Obsidian notes with intelligent pattern selection and smart caching.

**Latest Version**: V4.0 (Status & Vault Commands)  
**Status**: Production-Ready  
**Command**: `yt`

---

## Quick Navigation

- **New to `yt`?** → Start with [Basic Commands](#basic-commands)
- **Want to understand modes?** → See [Usage Modes](#usage-modes)
- **Exploring patterns?** → See [Pattern Discovery](#pattern-discovery-commands)
- **Managing existing notes?** → See [Iterative Workflow](#iterative-workflow-commands)
- **Troubleshooting?** → See [Common Issues](#common-issues)

---

## Basic Commands

### One-Shot Usage

```bash
# Recommended: Smart mode with intelligent pattern selection (~50s)
yt "https://youtube.com/watch?v=VIDEO_ID"

# Fast: Essential patterns only (~25s)
yt --quick "https://youtube.com/watch?v=VIDEO_ID"

# Complete: All available patterns (~70s)
yt --deep "https://youtube.com/watch?v=VIDEO_ID"

# Preview: See recommendations without running
yt --preview "https://youtube.com/watch?v=VIDEO_ID"
```

### Cache Management (V3.0)

```bash
# Re-analyze a video (ignore cache)
yt --force "https://youtube.com/watch?v=VIDEO_ID"

# Add new patterns to existing note (incremental)
yt --append --patterns extract_wisdom extract_ideas "URL"

# Show all processed videos
yt --list-processed

# Update metadata only (refresh title, views, etc.)
yt --update "https://youtube.com/watch?v=VIDEO_ID"
```

---

## URL Formats

All standard YouTube URL formats are supported:

```bash
yt "https://www.youtube.com/watch?v=jNQXAC9IVRw"    # Full URL
yt "https://youtu.be/jNQXAC9IVRw"                    # Short URL
yt "https://m.youtube.com/watch?v=jNQXAC9IVRw"      # Mobile
yt "https://youtube.com/watch?v=jNQXAC9IVRw"        # Without www
yt "jNQXAC9IVRw"                                     # Just video ID
```

---

## Usage Modes

### Smart Mode (Default)

Automatically selects 10-20 most relevant patterns based on content.

```bash
yt "YOUTUBE_URL"
```

**What happens:**
1. Extracts video transcript
2. Runs `pattern_optimizer` to analyze content
3. Filters patterns by priority (essential → high → medium → optional)
4. Runs selected patterns
5. Saves analysis to note + cache

**Timing:** ~50 seconds for typical video  
**API Calls:** ~20-50 depending on video length  
**Cost:** Low (uses free Groq tier)

**Configuration:**
- Edit `~/.yt-obsidian/config.yml`:
  - `auto_min_priority: medium` - Start with "medium" importance patterns
  - `auto_max_patterns: 20` - Max 20 patterns
  - `auto_show_recommendations: true` - Show pattern list before running

### Quick Mode

Fast analysis with 5 essential patterns for time-constrained workflows.

```bash
yt --quick "YOUTUBE_URL"
```

**Patterns:** `extract_wisdom`, `create_summary`, `extract_insights`, `extract_patterns`, `extract_main_idea`  
**Timing:** ~25 seconds  
**API Calls:** ~10-15  
**Use when:** You need quick insights without full analysis

### Deep Mode

Complete analysis with all recommended patterns for comprehensive coverage.

```bash
yt --deep "YOUTUBE_URL"
```

**What happens:**
1. Runs content analysis
2. Selects ALL "essential" and "high" priority patterns
3. Continues through "medium" and "optional"
4. Comprehensive 30-50 pattern analysis

**Timing:** ~70 seconds  
**API Calls:** ~40-80 (depending on video)  
**Use when:** Research, important content, or thorough documentation needed

### Preview Mode

See what patterns would be selected without making API calls.

```bash
yt --preview "YOUTUBE_URL"
```

**Output shows:**
- Content type analysis
- Complexity assessment
- Estimated value of each pattern
- Primary topics
- Selected patterns with priority levels
- Estimated total processing time

**API Calls:** 1 (just pattern_optimizer)  
**Use when:** Exploring content or checking costs before committing

### Expert Mode

Specify exactly which patterns to run.

```bash
yt --patterns extract_wisdom create_summary extract_ideas "YOUTUBE_URL"
```

**Pattern examples:**
- `extract_wisdom` - Key wisdom and lessons
- `create_summary` - Concise video summary
- `extract_insights` - Actionable insights
- `extract_patterns` - Recurring themes
- `extract_main_idea` - Core message
- `youtube_summary` - YouTube-optimized summary
- And 250+ more patterns available

**API Calls:** Number of patterns × chunks  
**Use when:** You know exactly what analysis you want

---

## Model Selection

Override the default LLM model for analysis.

```bash
# Use fastest model (30K TPM)
yt --model llama-4-scout "YOUTUBE_URL"

# Use highest quality model (12K TPM)
yt --model llama-70b "YOUTUBE_URL"

# Use default (10K TPM)
yt --model kimi "YOUTUBE_URL"

# Use in deep mode
yt --deep --model llama-70b "YOUTUBE_URL"
```

**Available Models:**

| Model | TPM | Speed | Quality | Best For |
|-------|-----|-------|---------|----------|
| `llama-4-scout` | 30K | ⚡⚡⚡ | Good | Long videos, quick turnaround |
| `llama-70b` | 12K | ⚡ | Excellent | High-quality analysis |
| `kimi` | 10K | ⚡⚡ | Very Good | Default, balanced |
| `llama-8b` | 6K | ⚡⚡⚡ | Good | Fast for short videos |

**Configuration:**
- Edit `~/.yt-obsidian/config.yml`:
  - `model: kimi` - Default model for all modes

---

## Advanced Options

### No Analysis Mode

Extract metadata and transcript without AI analysis.

```bash
yt --no-analysis "YOUTUBE_URL"
```

**Use when:**
- You want just the transcript and metadata
- Network issues prevent Groq API access
- Testing or debugging
- Saving API quota

**Output:** Minimal note with no AI sections

### Verbose Output

Show detailed processing information.

```bash
yt --verbose "YOUTUBE_URL"
yt -v "YOUTUBE_URL"  # Short form
```

**Shows:**
- Video ID and metadata
- Selected mode and model
- Pattern selection process
- Chunk information
- Pattern execution progress
- Caching operations

### Debug Output

Show debugging information for troubleshooting.

```bash
yt --debug "YOUTUBE_URL"
```

**Shows everything from --verbose PLUS:**
- API request/response details
- Token counts
- Timing information
- Full error stack traces

---

## Output and Organization

### Output Location

Notes are saved to: `$OBSVAULT/youtube/`

```bash
# Verify your output directory
echo $OBSVAULT/youtube/

# If not set, create it
export OBSVAULT="/path/to/your/obsidian/vault"

# Add to ~/.zshrc or ~/.bashrc for persistence:
# echo 'export OBSVAULT="/path/to/obsidian/vault"' >> ~/.zshrc
```

### Filename Format

`YYYY-MM-DD_slugified_title.md`

Examples:
- `2025-12-17_rick_astley_never_gonna_give_you_up.md`
- `2025-12-17_the_future_of_ai_with_sam_altman.md`
- `2025-12-17_short_11_minute_video.md`

### Note Structure

Every generated note includes:

```markdown
---
url: https://youtube.com/watch?v=VIDEO_ID
title: Video Title
channel: Channel Name
upload_date: YYYY-MM-DD
duration: HH:MM:SS
views: 1234567
likes: 12345
tags: [tag1, tag2]
transcript_word_count: 5432
ai_patterns: [pattern1, pattern2, ...]
---

# Video Title

**Channel:** Channel Name  
**Published:** YYYY-MM-DD  
**Duration:** HH:MM:SS  
**Views:** 1,234,567

## Description
[Full video description]

## Transcript
[Full transcript with timestamps]

## AI Analysis

### Pattern Name 1
[AI-generated analysis]

### Pattern Name 2
[AI-generated analysis]

...

```

---

## Pattern Discovery Commands (V4.0)

### List All Patterns

```bash
yt patterns
```

**Output:**
- All 260+ available Fabric patterns
- Grouped by category
- Brief description for each

### Search Patterns

```bash
yt patterns search wisdom
yt patterns search "extract wisdom"
```

**Finds patterns matching keywords:**
- By name: `extract_wisdom`, `extract_wisdom_from_experts`
- By description: searching for "wisdom" finds all wisdom-related patterns

### Describe a Pattern

```bash
yt patterns describe extract_wisdom
yt patterns describe create_summary
```

**Output:**
- Full pattern description
- Expected input/output format
- Typical use cases
- Time estimate

### Smart Pattern Suggestions

```bash
yt patterns suggest                    # Context-aware suggestions
yt patterns suggest --content-type podcast
yt patterns suggest --for-action summarize
yt patterns suggest --for-role researcher
```

**Suggests patterns based on:**
- Content type (podcast, interview, tutorial, speech, etc.)
- Desired action (summarize, extract, analyze, synthesize)
- User role (researcher, student, marketer, executive)

---

## Iterative Workflow Commands (V4.0)

### Check Analysis Status

```bash
yt status VIDEO_ID
yt status jNQXAC9IVRw
```

**Shows:**
- Processing status
- Patterns already run
- Last update time
- Markdown file location
- Suggested next patterns

### Add Patterns Incrementally

```bash
# Add specific patterns
yt add VIDEO_ID --patterns extract_wisdom extract_ideas

# Add with smart suggestions
yt add VIDEO_ID --suggest

# Show what would be added
yt add VIDEO_ID --patterns extract_wisdom --preview
```

**Use when:**
- You want to enhance existing analysis
- New patterns become available
- You discover you need different analysis
- Running full re-analysis wastes quota

**What happens:**
1. Extracts transcript from cache (0 time if cached)
2. Runs only NEW patterns (don't re-run existing)
3. Appends new sections to existing markdown
4. Updates cache with new patterns

**Time:** ~15-20s per new pattern (vs 50s full re-run)

---

## Vault Operations Commands (V4.0)

### Vault Overview

```bash
yt vault
```

**Shows:**
- Total videos processed
- Total patterns run
- Storage usage
- Last updated
- Recent additions

### Vault Statistics

```bash
yt vault stats
```

**Detailed statistics:**
- Videos by channel
- Most-run patterns
- Average analysis time
- Estimated API costs
- Trend data (by day/week/month)

### List Vault Contents

```bash
yt vault list                        # All videos
yt vault list --sort date            # By date (default)
yt vault list --sort channel         # By channel
yt vault list --sort title           # Alphabetically
yt vault list --filter channel=name  # Videos from channel
yt vault list --filter pattern=name  # Videos with pattern
yt vault list --missing pattern_name # Videos lacking pattern
```

### Apply Pattern to Multiple Videos

```bash
# Apply pattern to specific videos
yt vault apply extract_wisdom --to VIDEO_ID1 VIDEO_ID2

# Apply to all videos missing the pattern
yt vault apply extract_wisdom --all --missing

# Apply to videos from specific channel
yt vault apply create_summary --from "Channel Name"

# Preview before running
yt vault apply extract_ideas --all --preview
```

**Pricing:**
- Each video × pattern = 1 API call
- 100 videos × 1 pattern = ~50s, 100 calls
- Preview first to see scope

---

## Cache System (V3.0)

### How Caching Works

**First run:**
1. Extract, analyze, save note
2. Store cache entry with:
   - Video ID
   - Title, duration, channel
   - Patterns run
   - Note location
   - Timestamp

**Second run (default):**
- Instant skip (0.1s, 0 API calls)
- Shows existing note location
- Suggests --append or --force

**Cache location:** `$OBSVAULT/youtube/.cache/`

### Cache Commands

```bash
# View what's cached
yt --list-processed

# Force re-analysis (ignore cache)
yt --force "URL"

# Append new patterns (use existing transcript)
yt --append --patterns pattern1 pattern2 "URL"

# Update metadata (not implemented yet)
yt --update "URL"

# Clear all cache
rm -rf $OBSVAULT/youtube/.cache/

# Clear specific video
rm $OBSVAULT/youtube/.cache/VIDEO_ID.json
```

### Cache Contents

Each cache entry stores:

```json
{
  "video_id": "jNQXAC9IVRw",
  "video_url": "https://youtube.com/watch?v=jNQXAC9IVRw",
  "title": "Me at the zoo",
  "upload_date": "2005-04-23",
  "duration_seconds": 18,
  "transcript_word_count": 47,
  "markdown_path": "/path/to/vault/youtube/2025-12-17_me_at_the_zoo.md",
  "last_updated": "2025-12-17T12:34:56",
  "patterns_run": ["extract_wisdom", "create_summary"],
  "processing_history": [
    {
      "timestamp": "2025-12-17T12:34:56",
      "mode": "quick",
      "model": "kimi",
      "patterns_run": ["extract_wisdom", "create_summary"],
      "success": true
    }
  ]
}
```

---

## Configuration

### Config File Location

`~/.yt-obsidian/config.yml`

**Auto-created on first run with sensible defaults.**

### Default Configuration

```yaml
# Analysis settings
analysis_mode: auto              # auto, quick, deep
model: kimi                      # Default LLM model

# Output settings
output_dir: ~/Documents/Obsidian/YouTube
open_in_editor: false            # Open note after creation

# Quick mode patterns (5 essential)
quick_patterns:
  - extract_wisdom
  - create_summary
  - extract_insights
  - extract_patterns
  - extract_main_idea

# Auto mode filtering
auto_min_priority: medium        # Start with medium+ importance
auto_max_patterns: 20            # Max 20 patterns
auto_show_recommendations: true  # Show patterns before running

# Deep mode filtering
deep_min_priority: optional      # Include all patterns
deep_max_patterns: 50            # Max 50 patterns

# Processing settings
timeout_per_pattern: 60          # Seconds per pattern
chunk_size: 10000                # Tokens per chunk
verbose: false                   # Show detailed output

# Fabric/AI settings
fabric:
  enabled: true
  command: fabric-ai
  timeout: 120
```

### Customizing Configuration

Edit `~/.yt-obsidian/config.yml`:

```bash
# Open config
nano ~/.yt-obsidian/config.yml

# Or with your default editor
$EDITOR ~/.yt-obsidian/config.yml

# Verify it's valid YAML before saving
```

**Key customizations:**

```yaml
# Change default output location
output_dir: /my/custom/obsidian/vault/youtube

# Make auto mode more aggressive (more patterns)
auto_max_patterns: 30

# Make auto mode more conservative (fewer patterns)
auto_max_patterns: 10

# Change default model
model: llama-70b

# Show recommendations every time
auto_show_recommendations: true

# Automatically open notes in editor
open_in_editor: true

# Make quick mode even faster (3 patterns)
quick_patterns:
  - extract_wisdom
  - create_summary
  - extract_main_idea
```

---

## Output Examples

### Example Note Output

File: `2025-12-17_rick_astley_never_gonna_give_you_up.md`

```markdown
---
url: https://youtube.com/watch?v=dQw4w9WgXcQ
title: Rick Astley - Never Gonna Give You Up
channel: Rick Astley Official
upload_date: 2009-10-25
duration: 00:03:33
views: 1720502931
likes: 18669337
tags: [music, 80s, classic, rickroll]
transcript_word_count: 198
ai_patterns: [extract_wisdom, create_summary, extract_insights]
---

# Rick Astley - Never Gonna Give You Up

**Channel:** Rick Astley Official  
**Published:** 2009-10-25  
**Duration:** 00:03:33  
**Views:** 1,720,502,931

## Description
Rick Astley's official video for "Never Gonna Give You Up" released 
on 25th October 2009. This is the new refurbished HD version of the 
official video...

## Transcript
[00:00:00] Never gonna give you up
[00:00:05] Never gonna let you down
...

## AI Analysis

### Extract Wisdom

#### KEY LESSONS
- The power of consistency in messaging
- Iconic cultural moments transcend generations
- Digital media creates unexpected legacy value

#### TAKEAWAYS
- Simple, clear messages are most memorable
- Longevity through cultural relevance
- Authenticity resonates across time

### Create Summary

Rick Astley's iconic 1987 hit gets an official HD upgrade. The 
song's earworm quality and the accompanying music video have made 
it a digital culture touchstone, spawning the "Rickroll" meme that 
remains relevant decades later. The track exemplifies how pop music's 
golden age produced genuinely memorable works.

### Extract Insights

- **Cultural Impact**: This video transformed from dated 80s pop 
  to internet meme phenomenon, showing how context determines value
- **Memetic Quality**: The predictability of the song/video makes 
  it perfect for surprising people with redirects
- **Longevity**: Unlike most music videos, this one grew MORE 
  popular after initial release due to digital culture
```

### --list-processed Example

```bash
$ yt --list-processed

📚 Processed Videos (5):

  🎬 Me at the zoo
     ID: jNQXAC9IVRw
     Note: 2025-04-23_me_at_the_zoo.md
     Patterns: 2 (extract_wisdom, create_summary)
     Last: 2025-12-17T10:30:00

  🎬 Rick Astley - Never Gonna Give You Up
     ID: dQw4w9WgXcQ
     Note: 2009-10-25_rick_astley_never_gonna_give_you_up.md
     Patterns: 3 (extract_wisdom, create_summary, extract_insights)
     Last: 2025-12-17T12:15:00

  ...

📊 Statistics:
   Total videos: 5
   Total patterns: 12
   Total tokens: 45,320
```

---

## Common Issues

### Issue: "Invalid YouTube URL"

**Error message:**
```
❌ Invalid YouTube URL
```

**Causes:**
- Malformed URL syntax
- Not a YouTube URL
- URL parsing failed

**Solutions:**
```bash
# Use standard YouTube URL formats:
yt "https://youtube.com/watch?v=VIDEO_ID"
yt "https://youtu.be/VIDEO_ID"
yt "https://m.youtube.com/watch?v=VIDEO_ID"

# Not supported:
yt "youtube.com/watch?v=VIDEO_ID"  # Missing https://
yt "VIDEO_ID"  # Just video ID
```

### Issue: "OBSVAULT not set"

**Error message:**
```
❌ OBSVAULT environment variable not set
```

**Solution:**
```bash
# Set for current session only
export OBSVAULT="/path/to/your/obsidian/vault"

# Make permanent (add to ~/.zshrc or ~/.bashrc)
echo 'export OBSVAULT="/path/to/your/obsidian/vault"' >> ~/.zshrc
source ~/.zshrc

# Verify
echo $OBSVAULT  # Should print your vault path
```

### Issue: "Transcript not available"

**Appears when:**
```
⚠️  Transcript not available
   Skipping AI analysis (no transcript)
```

**Causes:**
- Video creator disabled transcripts
- Very old video (before transcripts existed)
- Non-English video
- Age-restricted content

**Solutions:**
```bash
# Try specifying language
yt --transcript-lang es "URL"  # Spanish

# Use without analysis (metadata only)
yt --no-analysis "URL"

# Note will still have metadata and description
```

### Issue: "Rate limit exceeded"

**Error message:**
```
❌ Rate limit exceeded. Retrying...
```

**What happens:**
- Tool automatically retries with backoff
- Will eventually succeed or timeout after 3 retries

**To prevent:**
```bash
# Use faster model (higher TPM quota)
yt --model llama-4-scout "URL"

# Use quick mode (fewer patterns)
yt --quick "URL"

# Wait a few minutes between videos
sleep 60

# Use --preview first to estimate cost
yt --preview "URL"
```

### Issue: "Duplicate file created"

**Happens when:**
- Same video analyzed twice
- File already exists at output path
- Creates `filename (2).md` instead

**Solutions:**
```bash
# Check cache (should skip automatically)
yt --list-processed

# Force skip even if file exists
yt "URL"  # Checks cache first

# If cache corrupted, clear it
rm -rf $OBSVAULT/youtube/.cache/
```

### Issue: Network timeouts

**Error message:**
```
❌ Network error: Connection timed out
```

**Causes:**
- Slow internet connection
- YouTube server overload
- API service issues

**Solutions:**
```bash
# Tool auto-retries with backoff (3 attempts)
# Wait and try again

# Increase timeout
yt --timeout 120 "URL"  # 2 minutes per pattern

# Use offline mode (metadata only)
yt --no-analysis "URL"
```

---

## Keyboard Shortcuts

```
Ctrl+C          Stop analysis (can resume later with --append)
Ctrl+Z          Suspend process
```

---

## Performance Tips

### Speed Up Analysis

```bash
# Use fastest model (3x throughput)
yt --model llama-4-scout "URL"

# Use quick mode (5 patterns only)
yt --quick "URL"

# Skip analysis
yt --no-analysis "URL"

# Limit patterns
yt --max-patterns 5 "URL"
```

### Save API Quota

```bash
# Preview first (1 API call)
yt --preview "URL"

# Use existing analysis (0 API calls)
yt "URL"  # Skips if cached

# Append patterns incrementally (cheaper than full re-run)
yt --append --patterns new_pattern "URL"
```

### Better Quality Analysis

```bash
# Use highest quality model
yt --deep --model llama-70b "URL"

# Run more patterns
yt --max-patterns 40 "URL"

# Let auto mode choose (optimized for content)
yt "URL"  # Smart mode
```

---

## Integration with Obsidian

### Dataview Queries

```dataview
TABLE title, channel, duration, views
FROM #youtube
SORT upload_date DESC
```

```dataview
TABLE patterns
FROM #youtube
WHERE ai_patterns AND ai_patterns.length > 0
```

### Daily Notes

Add to your daily note:

```markdown
[[YouTube Videos]]
- [[2025-12-17_my_video_title]]
- Recently watched: [[Another Video]]
```

### Tags

Auto-generated tags:
- `#youtube` - All YouTube videos
- `#podcast` - If detected as podcast
- `#tutorial` - If detected as tutorial
- `#lecture` - If detected as lecture
- `#interview` - If detected as interview

---

## Getting Help

### Quick Help

```bash
yt --help
```

### This Documentation

```bash
yt help
cat README.md
```

### Check Configuration

```bash
cat ~/.yt-obsidian/config.yml
```

### See All Cached Videos

```bash
yt --list-processed
```

### Debug Mode

```bash
yt --debug "URL"
```

---

## Examples Walkthrough

### Example 1: Quick Video Analysis

```bash
# Analyze Rick Astley music video (3:33)
yt "https://youtu.be/dQw4w9WgXcQ"

# Output: Shows metadata extraction and 15-20 patterns analyzed
# Result: Note with full analysis in ~50 seconds
```

### Example 2: Fast Turnaround on Long Video

```bash
# 2-hour podcast - use quick mode
yt --quick "https://youtube.com/watch?v=LONG_VIDEO_ID"

# Output: 5 essential patterns in ~25 seconds
# Result: Quick summary + key insights
```

### Example 3: Adding More Analysis Later

```bash
# Initial quick analysis
yt --quick "https://youtu.be/VIDEO_ID"
# → Note created, 5 patterns analyzed

# Later: Add more patterns without full re-run
yt --append --patterns extract_wisdom extract_questions "https://youtu.be/VIDEO_ID"
# → 2 new sections appended, existing content unchanged
# → No re-processing needed

# Total time: 25s + 10s = 35s (vs 50s+ full re-run)
```

### Example 4: Research Deep Dive

```bash
# Complete analysis on academic lecture
yt --deep --model llama-70b "https://youtu.be/LECTURE_ID"

# Output: 30-50 patterns covering every angle
# Result: Comprehensive research notes with all perspectives
```

### Example 5: Previewing Before Committing

```bash
# See what patterns would run
yt --preview "https://youtu.be/VIDEO_ID"

# Output: Content analysis, recommended patterns, time estimate
# Cost: 1 API call only

# If satisfied, run without preview
yt "https://youtu.be/VIDEO_ID"
```

---

## Troubleshooting Checklist

- [ ] `echo $OBSVAULT` outputs correct path
- [ ] `ls $OBSVAULT` shows existing vault directory
- [ ] `yt --version` shows version number
- [ ] `which fabric-ai` shows fabric installed
- [ ] `yt --help` displays this documentation
- [ ] `yt --list-processed` shows at least one video
- [ ] `yt "https://youtu.be/jNQXAC9IVRw"` completes successfully
- [ ] Running same URL twice shows cache skip

---

## For Developers

### Project Structure
- `yt` - Main CLI interface
- `lib/` - Core modules
- `docs/` - Architecture and design
- `CONTEXT.md` - Full project history
- `README.md` - User documentation

### Contributing

See `CONTRIBUTING.md` for development guidelines.

### Architecture

See `docs/ARCHITECTURE.md` for system design.

---

**Last Updated:** December 2025  
**Version:** 4.0 (Status & Vault Commands)  
**Status:** Production Ready
