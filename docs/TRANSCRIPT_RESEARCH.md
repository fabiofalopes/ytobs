# Transcript Research - yt-dlp API Reference

**Created**: 2025-12-08  
**Purpose**: Technical reference for yt-dlp transcript/subtitle extraction  
**Status**: Reference document for developers

---

## Table of Contents

1. [Overview](#overview)
2. [yt-dlp Library Mode](#yt-dlp-library-mode)
3. [Subtitle Metadata Structure](#subtitle-metadata-structure)
4. [Subtitle Formats](#subtitle-formats)
5. [Code Examples](#code-examples)
6. [Common Issues](#common-issues)

---

## Overview

### Key Insights

- **yt-dlp library mode** returns subtitle URLs, not content
- Subtitle content must be **fetched separately** via HTTP requests
- **JSON3 format** is easiest to parse (structured data)
- **Manual subtitles** (human-created) are preferred over auto-generated
- **Language fallback** is necessary (not all videos have all languages)

---

## yt-dlp Library Mode

### Basic Usage

```python
import yt_dlp

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'writesubtitles': True,        # Include manual captions
    'writeautomaticsub': True,     # Include auto-generated captions
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    
# info now contains subtitle metadata
```

### Options Reference

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `writesubtitles` | bool | Include manual subtitles metadata | False |
| `writeautomaticsub` | bool | Include auto-generated captions metadata | False |
| `subtitleslangs` | list | Specific languages to fetch | All |
| `subtitlesformat` | str | Preferred format | best |
| `skip_download` | bool | Don't download video | False |
| `cookiesfrombrowser` | str | Browser for cookies (age-gated videos) | None |

---

## Subtitle Metadata Structure

### Info Dictionary Structure

```python
info = {
    # Standard metadata
    'id': 'VIDEO_ID',
    'title': 'Video Title',
    # ...
    
    # Manual subtitles (human-created)
    'subtitles': {
        'en': [
            {'ext': 'json3', 'url': 'https://...'},
            {'ext': 'vtt', 'url': 'https://...'},
            {'ext': 'srv1', 'url': 'https://...'}
        ],
        'pt': [
            {'ext': 'json3', 'url': 'https://...'}
        ]
    },
    
    # Auto-generated captions
    'automatic_captions': {
        'en': [
            {'ext': 'json3', 'url': 'https://...'},
            {'ext': 'vtt', 'url': 'https://...'}
        ],
        'es': [...]
    }
}
```

### Subtitle Format Entry

```python
{
    'ext': 'json3',                              # Format extension
    'url': 'https://www.youtube.com/api/timedtext?v=VIDEO_ID&lang=en&fmt=json3',
    'name': 'English',                           # Optional: display name
}
```

---

## Subtitle Formats

### Available Formats

| Format | Extension | Structure | Best For | Parsing Difficulty |
|--------|-----------|-----------|----------|-------------------|
| **JSON3** | `json3` | Structured JSON with events/segments | Programmatic parsing | ⭐ Easy |
| VTT | `vtt` | WebVTT format with timestamps | Browser display | Medium |
| SRV1/SRV3 | `srv1`, `srv3` | YouTube's internal XML formats | Legacy | Hard |
| SRT | `srt` | SubRip text format | Media players | Medium |
| TTML | `ttml` | Timed Text Markup Language (XML) | Professional captioning | Hard |

### Format Selection Priority

```
json3 > vtt > srt > srv3 > srv1 > ttml
```

**Recommendation**: Always prefer JSON3 for programmatic parsing.

---

## JSON3 Format Specification

### Structure

```json
{
  "events": [
    {
      "tStartMs": 0,              // Start time (milliseconds)
      "dDurationMs": 5000,        // Duration (milliseconds)
      "segs": [                   // Text segments
        {"utf8": "Hello "},
        {"utf8": "world"}
      ]
    },
    {
      "tStartMs": 5000,
      "dDurationMs": 3000,
      "segs": [
        {"utf8": "This is "},
        {"utf8": "a test"}
      ]
    }
  ],
  "pens": {...},                  // Styling info (can be ignored)
  "wsWinStyles": [...]            // Window styles (can be ignored)
}
```

### Parsing Logic

```python
def parse_json3_to_text(json_data: dict) -> str:
    """Extract plain text from JSON3 format."""
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

## Code Examples

### Example 1: Extract Transcript (Complete Flow)

```python
import yt_dlp
import requests

def extract_transcript(url: str, lang: str = 'en') -> str:
    """Extract transcript from YouTube video."""
    
    # Step 1: Get video info with subtitle metadata
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    # Step 2: Try manual subtitles first
    subtitles = info.get('subtitles', {})
    if lang in subtitles:
        subtitle_url = get_json3_url(subtitles[lang])
        if subtitle_url:
            return fetch_and_parse(subtitle_url)
    
    # Step 3: Fallback to auto-generated
    auto_captions = info.get('automatic_captions', {})
    if lang in auto_captions:
        subtitle_url = get_json3_url(auto_captions[lang])
        if subtitle_url:
            return fetch_and_parse(subtitle_url)
    
    # Step 4: Not available
    raise TranscriptNotAvailableError(f"No transcript in language: {lang}")


def get_json3_url(formats: list) -> str | None:
    """Get JSON3 format URL from format list."""
    for fmt in formats:
        if fmt.get('ext') == 'json3':
            return fmt['url']
    return None


def fetch_and_parse(url: str) -> str:
    """Fetch subtitle content and parse to text."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    json_data = response.json()
    return parse_json3_to_text(json_data)
```

### Example 2: Get Transcript Metadata

```python
def get_transcript_info(info: dict, transcript: str | None) -> dict:
    """Generate transcript metadata for front matter."""
    
    if not transcript:
        return {'transcript_available': False}
    
    # Determine type (manual vs auto)
    lang = 'en'  # Assuming English for now
    is_manual = lang in info.get('subtitles', {})
    
    # Count words
    word_count = len(transcript.split())
    
    return {
        'transcript_available': True,
        'transcript_language': lang,
        'transcript_type': 'manual' if is_manual else 'auto',
        'transcript_word_count': word_count
    }
```

### Example 3: Graceful Error Handling

```python
def extract_transcript_safe(url: str, lang: str = 'en') -> tuple[str | None, dict]:
    """
    Extract transcript with graceful error handling.
    
    Returns:
        (transcript_text | None, metadata_dict)
    """
    try:
        # Attempt extraction
        info = get_video_info(url)
        transcript = extract_transcript_from_info(info, lang)
        metadata = get_transcript_info(info, transcript)
        return transcript, metadata
        
    except TranscriptNotAvailableError:
        return None, {'transcript_available': False}
        
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch transcript: {e}")
        return None, {'transcript_available': False}
        
    except Exception as e:
        logger.error(f"Unexpected error extracting transcript: {e}")
        return None, {'transcript_available': False}
```

---

## Common Issues

### Issue 1: Age-Restricted Videos

**Problem**: Cannot access subtitles for age-restricted videos without authentication.

**Solution**: Use `cookiesfrombrowser` option.

```python
ydl_opts = {
    'cookiesfrombrowser': 'firefox',  # or 'chrome', 'safari'
    'writesubtitles': True,
    'writeautomaticsub': True,
}
```

### Issue 2: No Transcript Available

**Problem**: Some videos simply don't have transcripts (especially older videos, music videos).

**Solution**: Graceful degradation - allow metadata extraction to succeed even if transcript fails.

```python
try:
    transcript = extract_transcript(url)
except TranscriptNotAvailableError:
    transcript = None
    # Continue with metadata extraction
```

### Issue 3: Empty Transcript Text

**Problem**: Subtitle track exists but contains no actual text.

**Solution**: Check word count before considering transcript valid.

```python
transcript = extract_transcript(url)
word_count = len(transcript.split())

if word_count < 10:  # Arbitrary threshold
    logger.warning("Transcript too short, may be invalid")
    transcript = None
```

### Issue 4: Non-English Videos

**Problem**: English transcript not available for non-English videos.

**Solution**: Language fallback logic.

```python
def extract_transcript_with_fallback(info: dict, preferred_lang: str = 'en'):
    """Try preferred language, then fallback to any available."""
    
    # Try preferred
    if preferred_lang in info.get('subtitles', {}):
        return extract_for_lang(info, preferred_lang)
    if preferred_lang in info.get('automatic_captions', {}):
        return extract_for_lang(info, preferred_lang)
    
    # Fallback to first available
    all_subtitles = {**info.get('subtitles', {}), **info.get('automatic_captions', {})}
    if all_subtitles:
        first_lang = list(all_subtitles.keys())[0]
        logger.info(f"Falling back to language: {first_lang}")
        return extract_for_lang(info, first_lang)
    
    return None
```

### Issue 5: Network Timeouts

**Problem**: Subtitle fetch times out on slow connections.

**Solution**: Configurable timeout with retry logic.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def fetch_subtitle_with_retry(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

---

## Performance Considerations

### Execution Time

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| yt-dlp info extraction | 1-2s | Network dependent |
| Subtitle URL fetch | 0.5-1s | Additional HTTP request |
| JSON3 parsing | <50ms | Pure Python, fast |
| **Total** | **~2-3s** | +1s compared to metadata-only |

### Optimization Opportunities

1. **Parallel fetching**: Fetch subtitle content while processing metadata
2. **Caching**: Cache transcript for repeated requests
3. **Streaming parsing**: Parse JSON3 incrementally (not necessary for typical transcript sizes)

---

## Testing Resources

### Test Videos

| Type | URL | Notes |
|------|-----|-------|
| Auto-captions | `https://youtube.com/watch?v=XFhUI1fphKU` | "The Chinese AI Iceberg" |
| Manual captions | `https://youtube.com/watch?v=dQw4w9WgXcQ` | Rick Astley (manual subs) |
| No transcript | TBD | Music video without captions |
| Non-English | TBD | Spanish/Portuguese video |

---

## References

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp API Reference](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)
- [YouTube Data API - Captions](https://developers.google.com/youtube/v3/docs/captions)
- [WebVTT Specification](https://www.w3.org/TR/webvtt1/)

---

**For implementation details, see**: `docs/TRANSCRIPT_IMPLEMENTATION_PLAN.md`
