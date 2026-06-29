# YouTube to Obsidian - AI-Enhanced Notes

Transform YouTube videos into AI-enhanced Obsidian notes with one command.

## Quick Start

```bash
# Simple - just works (~50s with smart pattern selection)
ytobs "https://youtu.be/dQw4w9WgXcQ"

# Fast - essential insights only (~25s)
ytobs --quick "https://youtu.be/dQw4w9WgXcQ"

# Deep - comprehensive analysis (~70s)
ytobs --deep "https://youtu.be/dQw4w9WgXcQ"

# Preview - see what patterns would run (instant)
ytobs --preview "https://youtu.be/dQw4w9WgXcQ"
```

## What You Get

Every note includes:
- **Metadata** - title, channel, duration, views, likes, tags, upload date
- **Description & Transcript** - full video content in readable format
- **AI Analysis** - wisdom, insights, patterns, summaries, and more

Output: `2009-10-25_rick_astley_never_gonna_give_you_up.md` in your Obsidian vault

---

## Features

✅ **Extract metadata** - No video download, just metadata via yt-dlp  
✅ **YAML front matter** - Obsidian-ready with all key fields  
✅ **Quick & fast** - Extracts in 1-2 seconds  
✅ **Age-restricted videos** - Works with browser cookies  
✅ **Error handling** - Clear messages for unavailable/deleted videos  
✅ **Customizable** - Output location via environment variable  

🔜 **Coming Later**  
- Phase 2: Transcript extraction
- Phase 3: Audio download
- Phase 4: Batch processing

---

## Installation

### Install via pip (editable, recommended for development)

```bash
pip install -e ~/projetos/hub/ytobs
```

### Or install from PyPI (once published)

```bash
pip install ytobs
```

### 3. Set Obsidian vault location (add to ~/.zshrc or ~/.bashrc)

```bash
export OBSVAULT="/path/to/your/obsidian/vault"
```

### 4. Test it works

```bash
ytobs --help
ytobs --version
```

---

## Usage Modes

### Auto Mode (Default)
Smart pattern selection based on content analysis (~50s):
```bash
ytobs "YOUTUBE_URL"
```

Supports all YouTube URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://m.youtube.com/watch?v=VIDEO_ID` (mobile)

### Age-Restricted Videos

If you get an error about age-restricted content, use browser cookies:

```bash
# Use Firefox
ytobs "https://youtu.be/VIDEO_ID" --cookies firefox

# Or Chrome
ytobs "https://youtu.be/VIDEO_ID" --cookies chrome

# Or Safari
ytobs "https://youtu.be/VIDEO_ID" --cookies safari
```

The tool will extract cookies from your browser's cache automatically.

Automatically selects ~15 most relevant patterns using AI.

### Quick Mode
Fast essential analysis with 5 core patterns (~25s):
```bash
ytobs --quick "YOUTUBE_URL"
```
Runs: wisdom, summary, insights, patterns, main_idea

### Deep Mode  
Comprehensive analysis with all recommended patterns (~70s):
```bash
ytobs --deep "YOUTUBE_URL"
```

### Preview Mode
See what patterns would be selected without running analysis:
```bash
ytobs --preview "YOUTUBE_URL"
```

### Expert Options
```bash
# Use specific model
ytobs --model llama-4-scout "YOUTUBE_URL"

# Run specific patterns only
ytobs --patterns extract_wisdom create_summary "YOUTUBE_URL"

# Limit pattern count in auto mode
ytobs --max-patterns 10 "YOUTUBE_URL"

# Skip AI analysis (metadata + transcript only)
ytobs --no-analysis "YOUTUBE_URL"

# Custom output directory
ytobs --output /custom/path "YOUTUBE_URL"
```

---

## Configuration

On first run, `ytobs` creates `~/.yt-obsidian/config.yml` with defaults:

```yaml
mode: auto              # auto, quick, deep
model: kimi             # kimi, llama-4-scout, llama-70b
output_dir: ~/Documents/obsidian_vault/youtube
timeout_per_pattern: 60
chunk_size: 10000
open_in_editor: false
```

Edit this file to customize your defaults.

---

## Output Example

File: `2009-10-25_rick_astley_never_gonna_give_you_up.md`

```markdown
---
url: https://youtube.com/watch?v=dQw4w9WgXcQ
title: Rick Astley - Never Gonna Give You Up
channel: Rick Astley
upload_date: 2009-10-25
duration: 3:33
views: 1720502931
likes: 18669337
tags: [youtube, music, 80s]
---

# Rick Astley - Never Gonna Give You Up

**Channel:** Rick Astley  
**Published:** 2009-10-25  
**Duration:** 3:33

## Description
[Full description...]

## Transcript
[Full transcript with timestamps...]

## AI Analysis

### Extract Wisdom
#### SUMMARY
[AI-generated summary...]

#### IDEAS
[Key ideas extracted...]

### Youtube Summary
[Video summary...]

[Additional pattern outputs...]
```

---

## Available Models

- **kimi** (default) - 10K TPM, balanced quality/speed  
- **llama-4-scout** - 30K TPM, fastest  
- **llama-70b** - 12K TPM, highest quality  

## Troubleshooting

**"OBSVAULT not set"**: Export `OBSVAULT=/path/to/vault` in your shell config

**Age-restricted videos**: Tool will show clear error with suggestions

**Slow analysis**: Use `--quick` mode or `--model llama-4-scout

# Or if Firefox doesn't work:
ytobs "https://youtu.be/VIDEO_ID" --cookies chrome
```

The tool reads cookies from your browser's cache - you must be logged in to your YouTube account in that browser.

---

### Error: "Video unavailable"

**Problem**: The video is deleted, private, or geo-restricted.

**Why**: You can't access the video. YouTube has removed it, it's private, or blocked in your region.

**Solution**: 
- Check if the URL is correct
- Try accessing the video in your browser first
- If it's geo-blocked, try a VPN
- If it's deleted, there's nothing to extract

---

### Error: "Network error. Retrying..."

**Problem**: Temporary network issue.

**Why**: Connection to YouTube failed (could be network, VPN, or rate limiting).

**Solution**:
- The tool retries automatically up to 3 times
- Wait a moment and try again
- Check your internet connection
- If it keeps happening, try with fewer requests in quick succession

**Duplicates**: Running same URL creates `(2).md` suffix - this prevents overwriting

**Invalid URL**: Use formats: `youtube.com/watch?v=ID` or `youtu.be/ID`

---

## How It Works

1. Extract metadata + transcript via yt-dlp
2. Analyze content with pattern_optimizer  
3. Run selected Fabric patterns via Groq API
4. Generate markdown with YAML frontmatter
5. Save to `$OBSVAULT/youtube/`

Time: 25-70 seconds depending on mode

---

## Obsidian Dataview Queries

```dataview
TABLE channel, duration, views
FROM #youtube
WHERE created > date(today) - dur(7 days)
SORT created DESC
- **Reliable**: Handles network errors with automatic retries
- **Compatible**: Works with Obsidian plugins like Dataview

---

## For Developers

This is Phase 1 of the YouTube to Obsidian project. See technical documentation for implementation details:

- **[CONTEXT.md](./CONTEXT.md)** - Project context and session history
- **[Architecture](./docs/ARCHITECTURE.md)** - System design
- **[Implementation Plan](./docs/PHASE1_IMPLEMENTATION_PLAN.md)** - Roadmap
- **[Schema](./docs/OBSIDIAN_SCHEMA.md)** - Front matter specification
- **[Technology Decision](./docs/TECHNOLOGY_DECISION.md)** - Why yt-dlp

---

## Contributing

This is a personal project in Phase 1 development. Not accepting contributions at this time, but feedback is welcome!

---

## License

Personal project. Use and modify for your own needs.

---

## Support

If you find issues:

1. Check the **Troubleshooting** section above
2. Verify `OBSVAULT` is set: `echo $OBSVAULT`
3. Verify yt-dlp is installed: `yt-dlp --version`
4. Try the command manually: `yt-dlp --dump-json --skip-download URL`

---

## Roadmap

### Phase 2: Transcripts
Extract and embed video transcripts in your notes.

### Phase 3: Audio
Download audio as Opus files linked to your notes.

### Phase 4: Batch Operations
Process multiple URLs, playlists, and channels at once.

---

## Next Steps

1. Set up `$OBSVAULT` environment variable (see Installation)
2. Run: `ytobs "https://youtu.be/dQw4w9WgXcQ"`
3. Check your Obsidian vault for the new note
4. Customize the note with your own observations
5. Use tags and Dataview to query your video collection

---

**Happy note-taking!** 🎥📝
```

---

## Architecture

- **yt-dlp** - Metadata & transcript extraction
- **pattern_optimizer** - Smart pattern selection  
- **Fabric** - AI analysis patterns (70+ available)
- **Groq API** - Fast LLM inference
- **Rate limiter** - Respects API limits

See `docs/` for detailed architecture and design decisions.

---

## Legacy Tools

Old multi-command interface moved to `_deprecated/`:
- `auto-analyze.py` - Now integrated into `yt`
- Session documentation - Historical context

Use `./ytobs` for new simplified interface.

---

**Happy note-taking!** 🎥📝
