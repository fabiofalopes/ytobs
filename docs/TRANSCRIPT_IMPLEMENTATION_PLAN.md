# Transcript Feature Implementation Plan

**Created**: 2025-12-08  
**Phase**: 1B - Transcript Extraction Integration  
**Status**: Ready for Implementation  
**Developer Handoff Document**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Decision](#architecture-decision)
3. [Implementation Tasks](#implementation-tasks)
4. [Code Specifications](#code-specifications)
5. [Testing Strategy](#testing-strategy)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Examples](#examples)

---

## Overview

### Goal

Add transcript extraction as a **default feature** of the yt-obsidian pipeline. Every generated markdown note should include the YouTube video transcript by default.

### Scope

**In Scope:**
- ✅ Extract English transcripts by default
- ✅ Support both auto-generated and manual captions
- ✅ Prefer manual captions over auto-generated
- ✅ Store transcript as plain text in markdown
- ✅ Add transcript metadata to YAML front matter
- ✅ Graceful degradation when transcript unavailable
- ✅ Optional `--no-transcript` CLI flag

**Out of Scope:**
- ❌ Multiple language support (Phase 2)
- ❌ Timestamp preservation (optional future feature)
- ❌ Transcript summarization (Phase 3)
- ❌ Separate transcript files (keep inline)

### Success Criteria

1. ✅ Transcripts extracted for 95%+ of public videos
2. ✅ Execution time increase < 2 seconds
3. ✅ Metadata extraction still works if transcript fails
4. ✅ Generated markdown is valid and Obsidian-compatible
5. ✅ All existing tests continue to pass

---

## Architecture Decision

### Chosen Approach: yt-dlp Library Mode

**Why Library Mode?**

Current implementation uses `subprocess.run()` to call yt-dlp. For transcripts, we need:
- Access to subtitle metadata (URLs) from yt-dlp
- Ability to fetch subtitle content separately
- Single unified extraction call

**Option Comparison:**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| Subprocess + post-process | Minimal code changes | Two-step process, complex | ❌ Rejected |
| **yt-dlp library mode** | Single call, cleaner code, better control | Refactor extractor.py | ✅ **Chosen** |
| Hybrid (both) | Backward compatible | More complexity | ❌ Unnecessary |

### Implementation Strategy

1. **Refactor `lib/extractor.py`** to use yt-dlp library (`yt_dlp.YoutubeDL()`)
2. **Add transcript extraction** to return dict with `metadata` + `transcript`
3. **Update `lib/formatter.py`** to handle transcript content
4. **Maintain backward compatibility** through error handling

---

## Implementation Tasks

### Phase 1: Core Implementation (2 hours)

#### Task 1.1: Refactor lib/extractor.py to Library Mode

**Current Function:**
```python
def extract_metadata(url: str, cookies_browser: Optional[str] = None) -> Dict[str, Any]:
    """Uses subprocess.run(['yt-dlp', '--dump-json', ...])"""
```

**New Function:**
```python
def extract_metadata(
    url: str, 
    cookies_browser: Optional[str] = None,
    extract_transcript: bool = True,
    transcript_lang: str = 'en'
) -> Dict[str, Any]:
    """
    Extract metadata AND transcript using yt-dlp library mode.
    
    Returns:
        {
            'metadata': {...},  # All video metadata
            'transcript': str | None,  # Transcript text or None
            'transcript_info': {
                'available': bool,
                'language': str,
                'type': 'auto' | 'manual',
                'word_count': int
            }
        }
    """
```

**Implementation Steps:**
1. Replace subprocess call with `yt_dlp.YoutubeDL()`
2. Set options: `skip_download=True`, `writeautomaticsub=True`, `writesubtitles=True`
3. Call `ydl.extract_info(url, download=False)`
4. Extract subtitle URLs from `info['subtitles']` or `info['automatic_captions']`
5. Fetch transcript content if available
6. Return unified dict

**Files to Modify:**
- `lib/extractor.py` (refactor main function)

---

#### Task 1.2: Create Transcript Extraction Functions

**New Module: `lib/transcript.py`**

```python
"""
Transcript extraction and parsing utilities.
"""

from typing import Dict, List, Optional, Any
import requests


def extract_transcript_from_info(
    info: Dict[str, Any],
    lang: str = 'en',
    prefer_manual: bool = True
) -> Optional[str]:
    """
    Extract transcript text from yt-dlp info dict.
    
    Args:
        info: yt-dlp info dictionary
        lang: Language code (e.g., 'en', 'pt')
        prefer_manual: Prefer manual captions over auto-generated
        
    Returns:
        Plain text transcript or None if unavailable
    """
    pass


def fetch_subtitle_content(subtitle_url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch subtitle JSON from URL.
    
    Args:
        subtitle_url: URL to subtitle file (JSON3 format preferred)
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON data
        
    Raises:
        requests.RequestException: If fetch fails
    """
    pass


def parse_json3_to_text(json_data: Dict[str, Any]) -> str:
    """
    Convert JSON3 subtitle format to plain text.
    
    JSON3 structure:
        {
            "events": [
                {
                    "tStartMs": 1000,
                    "dDurationMs": 5000,
                    "segs": [
                        {"utf8": "Hello "},
                        {"utf8": "world"}
                    ]
                },
                ...
            ]
        }
    
    Args:
        json_data: Parsed JSON3 subtitle data
        
    Returns:
        Plain text transcript with newlines preserved
    """
    pass


def get_best_subtitle_url(
    subtitle_formats: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Select best subtitle format URL (prefer json3).
    
    Args:
        subtitle_formats: List of subtitle format dicts
            [{'ext': 'json3', 'url': '...'}, {'ext': 'vtt', 'url': '...'}]
    
    Returns:
        URL string or None
    """
    pass


def get_transcript_metadata(
    info: Dict[str, Any],
    transcript: Optional[str]
) -> Dict[str, Any]:
    """
    Generate transcript metadata for front matter.
    
    Returns:
        {
            'transcript_available': bool,
            'transcript_language': str,
            'transcript_type': 'auto' | 'manual',
            'transcript_word_count': int
        }
    """
    pass
```

**Files to Create:**
- `lib/transcript.py` (new file)

---

#### Task 1.3: Update lib/formatter.py

**Modifications:**

1. **Update `generate_frontmatter()` to include transcript metadata:**

```python
def generate_frontmatter(metadata: dict[str, Any]) -> str:
    # ... existing fields ...
    
    # Transcript (Phase 1B - NEW)
    if "transcript_available" in metadata:
        frontmatter_data["transcript_available"] = metadata["transcript_available"]
    if "transcript_language" in metadata:
        frontmatter_data["transcript_language"] = metadata["transcript_language"]
    if "transcript_type" in metadata:
        frontmatter_data["transcript_type"] = metadata["transcript_type"]
    if "transcript_word_count" in metadata:
        frontmatter_data["transcript_word_count"] = metadata["transcript_word_count"]
    
    # ... rest of function ...
```

2. **Update `generate_markdown()` to include transcript content:**

```python
def generate_markdown(
    frontmatter: str, 
    metadata: dict[str, Any],
    transcript: Optional[str] = None  # NEW parameter
) -> str:
    # ... existing sections ...
    
    # Transcript section
    transcript_section = "## Transcript\n\n"
    if transcript:
        transcript_section += transcript + "\n"
    else:
        transcript_section += "<!-- Transcript not available for this video -->\n"
    
    # ... build complete markdown ...
```

**Files to Modify:**
- `lib/formatter.py` (add transcript handling)

---

#### Task 1.4: Update Main CLI (yt-obsidian.py)

**Add Optional Flag:**

```python
parser.add_argument(
    '--no-transcript',
    action='store_true',
    help='Skip transcript extraction (faster, metadata only)'
)

parser.add_argument(
    '--transcript-lang',
    default='en',
    help='Preferred transcript language (default: en)'
)
```

**Pass to Extractor:**

```python
result = extract_metadata(
    url,
    cookies_browser=args.cookies_browser,
    extract_transcript=not args.no_transcript,
    transcript_lang=args.transcript_lang
)

metadata = result['metadata']
transcript = result.get('transcript')
transcript_info = result.get('transcript_info', {})

# Merge transcript_info into metadata for front matter
metadata.update(transcript_info)

# Generate markdown with transcript
frontmatter = generate_frontmatter(metadata)
markdown = generate_markdown(frontmatter, metadata, transcript)
```

**Files to Modify:**
- `yt-obsidian.py` (add CLI args, pass through)

---

### Phase 2: Documentation (1 hour)

#### Task 2.1: Update OBSIDIAN_SCHEMA.md

Add to schema definition:

```yaml
# ═══════════════════════════════════════════════════════════════
# TRANSCRIPT (Phase 1B - Added 2025-12-08)
# ═══════════════════════════════════════════════════════════════
transcript_available: bool      # Whether transcript was extracted
transcript_language: string     # Language code (e.g., 'en')
transcript_type: enum           # auto | manual
transcript_word_count: int      # Word count for discovery
```

**Files to Modify:**
- `docs/OBSIDIAN_SCHEMA.md` (add transcript fields)

---

#### Task 2.2: Update ARCHITECTURE.md

Update Component 2 (Metadata Extractor) section to describe transcript extraction.

Update Component 3 (Formatter) section to describe transcript rendering.

**Files to Modify:**
- `docs/ARCHITECTURE.md` (update components)

---

#### Task 2.3: Create TRANSCRIPT_RESEARCH.md

Create reference document with yt-dlp API details, subtitle format specs, example code.

**Files to Create:**
- `docs/TRANSCRIPT_RESEARCH.md` (new reference doc)

---

### Phase 3: Testing (30 minutes)

#### Task 3.1: Create Test Suite

**New File: `tests/test_transcript.py`**

Test cases:
- Extract transcript from video with manual captions
- Extract transcript from video with auto-captions only
- Handle video with no transcript available
- Parse JSON3 format correctly
- Handle network errors gracefully
- Word count calculation

**Files to Create:**
- `tests/test_transcript.py` (new test file)

---

#### Task 3.2: Integration Testing

Test with real YouTube videos:
- Public video with auto-captions
- Public video with manual captions
- Video without transcript
- Age-restricted video (with cookies)

**Files to Modify:**
- `tests/test_integration.py` (add transcript tests)

---

## Code Specifications

### 3.1 Library Mode Implementation

**Replace subprocess call:**

```python
# OLD (subprocess)
command = ["yt-dlp", "--dump-json", "--skip-download", url]
process = subprocess.run(command, capture_output=True, text=True)
metadata = json.loads(process.stdout)

# NEW (library mode)
import yt_dlp

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'writesubtitles': True,        # Include manual subs
    'writeautomaticsub': True,     # Include auto-captions
    'cookiesfrombrowser': cookies_browser if cookies_browser else None,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

# info dict now contains:
# - All metadata fields (same as before)
# - info['subtitles'] - manual captions
# - info['automatic_captions'] - auto-generated
```

---

### 3.2 Transcript Extraction Flow

```python
def extract_transcript_from_info(info: Dict, lang: str = 'en') -> Optional[str]:
    # 1. Try manual subtitles first
    subtitles = info.get('subtitles', {})
    if lang in subtitles:
        url = get_best_subtitle_url(subtitles[lang])
        if url:
            data = fetch_subtitle_content(url)
            return parse_json3_to_text(data)
    
    # 2. Fallback to auto-generated
    auto_captions = info.get('automatic_captions', {})
    if lang in auto_captions:
        url = get_best_subtitle_url(auto_captions[lang])
        if url:
            data = fetch_subtitle_content(url)
            return parse_json3_to_text(data)
    
    # 3. Not available
    return None
```

---

### 3.3 JSON3 Parsing

```python
def parse_json3_to_text(json_data: Dict) -> str:
    """
    JSON3 format:
    {
        "events": [
            {
                "tStartMs": 1000,      # Start time in ms
                "dDurationMs": 5000,   # Duration in ms
                "segs": [
                    {"utf8": "Hello "},
                    {"utf8": "world"}
                ]
            },
            ...
        ]
    }
    """
    text_parts = []
    
    for event in json_data.get('events', []):
        if 'segs' not in event:
            continue
        
        # Concatenate all segments in this event
        line = ''.join(seg.get('utf8', '') for seg in event['segs']).strip()
        
        # Skip empty lines and standalone newlines
        if line and line != '\n':
            text_parts.append(line)
    
    # Join with spaces (preserves readability)
    return ' '.join(text_parts)
```

---

### 3.4 Front Matter Schema

**New Fields Added:**

```yaml
# Transcript metadata (always present after Phase 1B)
transcript_available: true
transcript_language: en
transcript_type: auto  # or 'manual'
transcript_word_count: 2847
```

**Conditional Logic:**

```python
# If transcript not available:
transcript_available: false
# (other transcript_* fields omitted)

# If transcript available:
transcript_available: true
transcript_language: en
transcript_type: auto
transcript_word_count: 1234
```

---

## Testing Strategy

### 4.1 Unit Tests

| Test | Function | Assertion |
|------|----------|-----------|
| `test_parse_json3_basic` | `parse_json3_to_text()` | Correctly extracts text from JSON3 |
| `test_parse_json3_empty` | `parse_json3_to_text()` | Returns empty string for empty events |
| `test_get_best_subtitle_url_json3` | `get_best_subtitle_url()` | Prefers json3 format |
| `test_get_best_subtitle_url_fallback` | `get_best_subtitle_url()` | Falls back to other formats |
| `test_word_count` | `get_transcript_metadata()` | Counts words correctly |

---

### 4.2 Integration Tests

| Test | Video Type | Expected |
|------|------------|----------|
| `test_extract_auto_caption` | Public video (auto-captions) | `transcript_type: auto` |
| `test_extract_manual_caption` | Video with manual captions | `transcript_type: manual` |
| `test_no_transcript` | Video without transcript | `transcript_available: false` |
| `test_age_restricted` | Age-gated video | Works with cookies |
| `test_network_failure` | Simulated network error | Graceful degradation |

**Test Videos:**

```python
TEST_VIDEOS = {
    'auto_caption': 'https://www.youtube.com/watch?v=XFhUI1fphKU',  # "The Chinese AI Iceberg"
    'manual_caption': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Astley (manual)
    'no_transcript': 'TBD',  # Find video without transcript
}
```

---

### 4.3 Edge Cases

1. **Empty transcript** - Some videos have subtitle tracks but no content
2. **Non-English only** - Video has transcript but not in English
3. **Multiple languages** - Prefer specified language
4. **Fetch timeout** - Handle network timeout gracefully
5. **Invalid JSON** - Handle malformed subtitle data

---

## Configuration

### 5.1 CLI Arguments

```bash
# Default behavior (extract transcript)
python yt-obsidian.py https://youtube.com/watch?v=VIDEO_ID

# Skip transcript (faster)
python yt-obsidian.py --no-transcript https://youtube.com/watch?v=VIDEO_ID

# Specify language (future)
python yt-obsidian.py --transcript-lang pt https://youtube.com/watch?v=VIDEO_ID
```

---

### 5.2 Config File (config.yaml)

**Future Extension:**

```yaml
transcript:
  enabled: true              # Default: extract transcripts
  language: en               # Preferred language
  prefer_manual: true        # Prefer manual over auto
  timeout: 10                # Subtitle fetch timeout (seconds)
  include_timestamps: false  # Future: include timestamps
```

---

## Error Handling

### 6.1 Error Taxonomy

| Error | Cause | Handling | User Message |
|-------|-------|----------|--------------|
| `TranscriptNotAvailableError` | Video has no transcript | Skip transcript, continue | "Transcript not available" |
| `SubtitleFetchError` | Network error fetching subtitle | Skip transcript, log warning | "Failed to fetch transcript" |
| `SubtitleParseError` | Invalid JSON3 format | Skip transcript, log error | "Transcript parsing failed" |
| `LanguageNotFoundError` | Requested language not available | Skip transcript | "Transcript not available in [lang]" |

---

### 6.2 Graceful Degradation

**Core Principle:** Metadata extraction ALWAYS succeeds, even if transcript fails.

```python
try:
    transcript = extract_transcript_from_info(info, lang='en')
    transcript_info = get_transcript_metadata(info, transcript)
except Exception as e:
    logger.warning(f"Transcript extraction failed: {e}")
    transcript = None
    transcript_info = {
        'transcript_available': False,
    }

# Metadata extraction continues regardless
return {
    'metadata': info,
    'transcript': transcript,
    'transcript_info': transcript_info,
}
```

---

## Examples

### 7.1 Example Front Matter (With Transcript)

```yaml
---
url: https://youtube.com/watch?v=XFhUI1fphKU
video_id: XFhUI1fphKU
title: The Chinese AI Iceberg
channel: bycloud
channel_id: UCgfe2ooZD3VJPB6aJAnuQng
upload_date: '2025-11-01'
created: '2025-12-08T14:46:59.154250-05:00'
duration: '27:06'
duration_seconds: 1626
views: 104210
likes: 3746
tags:
  - youtube
  - video-note
  - chinese-ai
  - ai-research
categories:
  - Science & Technology
status: raw

# Transcript (NEW)
transcript_available: true
transcript_language: en
transcript_type: auto
transcript_word_count: 4521
---
```

---

### 7.2 Example Front Matter (Without Transcript)

```yaml
---
url: https://youtube.com/watch?v=VIDEO_ID
video_id: VIDEO_ID
title: Video Without Transcript
# ... other fields ...
status: raw

# Transcript (NEW)
transcript_available: false
---
```

---

### 7.3 Example Markdown (With Transcript)

```markdown
---
# [Front matter here]
---

# The Chinese AI Iceberg

**Channel:** [bycloud](https://youtube.com/...)
**Published:** 2025-11-01
**Duration:** 27:06

---

## Description

[Description here]

---

## Notes

<!-- Add your notes here -->

---

## Transcript

In this video we're exploring the landscape of Chinese AI research and development. The field has seen rapid advancement in recent years, with companies like MiniMax and DeepSeek pushing boundaries. The Chinese AI ecosystem is complex and multilayered, much like an iceberg where the visible portion represents only a fraction of the total activity. At the surface level, we see consumer-facing applications...

[Full transcript continues...]

---

## Related

<!-- Links to related notes -->

---

## Metadata

**Video ID:** `XFhUI1fphKU`
**Views:** 104,210
**Likes:** 3,746
**Tags:** youtube, video-note, chinese-ai, ai-research
**Transcript:** 4,521 words (auto-generated)
```

---

### 7.4 Example Code Usage

```python
# Extract metadata + transcript
result = extract_metadata(
    url='https://youtube.com/watch?v=VIDEO_ID',
    cookies_browser='firefox',
    extract_transcript=True,
    transcript_lang='en'
)

metadata = result['metadata']
transcript = result['transcript']
transcript_info = result['transcript_info']

# Generate markdown
metadata.update(transcript_info)
frontmatter = generate_frontmatter(metadata)
markdown = generate_markdown(frontmatter, metadata, transcript)

# Write to file
save_markdown(markdown, title=metadata['title'], upload_date=metadata['upload_date'])
```

---

## Dependencies

### 8.1 Python Packages

```txt
# Already in requirements.txt
yt-dlp>=2023.3.0
pyyaml>=6.0
pydantic>=2.0
tenacity>=8.0

# NEW - Add to requirements.txt
requests>=2.28.0  # For fetching subtitle content
```

---

### 8.2 System Requirements

- Python 3.10+
- Internet connection (for subtitle fetching)
- yt-dlp installed and in PATH

---

## Migration Path

### 9.1 Backward Compatibility

**Existing Notes:**
- Old notes (without transcript fields) remain valid
- No migration needed for existing notes
- New notes include transcript fields

**Code Compatibility:**
- `extract_metadata()` signature changes but maintains backward compatibility through default args
- `generate_markdown()` accepts optional transcript parameter (defaults to None)

---

### 9.2 Rollout Strategy

1. **Phase 1**: Implement transcript extraction (this plan)
2. **Phase 2**: Monitor performance impact (1-2 weeks)
3. **Phase 3**: Gather user feedback
4. **Phase 4**: Iterate on format/features

---

## Performance Considerations

### 10.1 Expected Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Execution time | ~2-3s | ~3-4s | +1s (subtitle fetch) |
| Network requests | 1 | 2 | +1 (subtitle URL) |
| Memory usage | ~50MB | ~55MB | +5MB (transcript text) |
| File size | ~2KB | ~15KB | +13KB (transcript content) |

---

### 10.2 Optimization Opportunities (Future)

- **Async subtitle fetching** - Don't block on subtitle download
- **Caching** - Cache transcripts for repeated requests
- **Parallel extraction** - Batch process multiple videos

---

## Acceptance Criteria

### Implementation Complete When:

- [x] `lib/transcript.py` created with all functions
- [x] `lib/extractor.py` refactored to library mode
- [x] `lib/formatter.py` updated for transcripts
- [x] `yt-obsidian.py` has `--no-transcript` flag
- [x] `OBSIDIAN_SCHEMA.md` updated with transcript fields
- [x] `ARCHITECTURE.md` updated with transcript specs
- [x] `tests/test_transcript.py` created with full coverage
- [x] Integration tests pass for all video types
- [x] Example markdown files generated successfully
- [x] Performance impact < 2 seconds
- [x] Error handling gracefully degrades
- [x] Documentation complete

---

## Next Steps

1. **Review this plan** - Approve or request changes
2. **Create code stubs** - Set up file structure
3. **Implement core logic** - Follow tasks 1.1-1.4
4. **Write tests** - Ensure coverage
5. **Test with real videos** - Validate functionality
6. **Update documentation** - Keep docs in sync
7. **Commit and tag** - Mark Phase 1B completion

---

## References

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [YouTube Subtitle Formats](https://developers.google.com/youtube/v3/docs/captions)
- [Obsidian YAML Front Matter](https://help.obsidian.md/Editing+and+formatting/Properties)
- [TRANSCRIPT_RESEARCH.md](./TRANSCRIPT_RESEARCH.md) - Detailed yt-dlp API reference

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-08  
**Prepared By**: Planning Agent  
**Ready for Implementation**: ✅ YES
