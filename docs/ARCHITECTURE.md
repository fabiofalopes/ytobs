# System Architecture - YouTube to Obsidian Pipeline

**Created**: 2024-12-08  
**Phase**: 1 - Metadata Extraction  
**Status**: Design Complete, Ready for Implementation

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Component Specifications](#component-specifications)
5. [Error Handling](#error-handling)
6. [Configuration](#configuration)
7. [Testing Strategy](#testing-strategy)

---

## System Overview

### Purpose

Single-purpose script that extracts YouTube video metadata and generates Obsidian-compatible markdown files.

### Core Principle

**Simplicity First**: Linear workflow, minimal dependencies.

### Technology Stack

```
User Input (YouTube URL)
    ↓
Python Script (yt-obsidian.py)
    ↓ executes
yt-dlp (--dump-json --skip-download)
    ↓ returns
JSON Metadata
    ↓ transforms to
YAML Front Matter + Markdown
    ↓ writes
Obsidian Note (*.md)
```

---

## Component Architecture

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT (YouTube URL)                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              INPUT VALIDATION & SANITIZATION                 │
│  • URL format validation                                     │
│  • Extract video ID                                          │
│  • Normalize URL                                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                METADATA EXTRACTION (yt-dlp)                  │
│  Command: yt-dlp --dump-json --skip-download URL            │
│  Output: JSON object with 40+ fields                         │
│  Execution Time: 1-2 seconds                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              METADATA TRANSFORMATION LAYER                   │
│  • Parse JSON response                                       │
│  • Extract required fields                                   │
│  • Format timestamps (ISO 8601)                              │
│  • Sanitize text fields                                      │
│  • Calculate human-readable duration                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│            OBSIDIAN FRONT MATTER GENERATION                  │
│  • Generate YAML front matter                                │
│  • Create markdown structure                                 │
│  • Add creation timestamp                                    │
│  • Format description and notes sections                     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  FILE SYSTEM OPERATIONS                      │
│  • Generate safe filename from title/date                    │
│  • Create output directory if missing ($OBSVAULT/youtube)    │
│  • Handle filename collisions                                │
│  • Write markdown file                                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SUCCESS / ERROR OUTPUT                    │
│  • Report file location                                      │
│  • Display any warnings                                      │
│  • Suggest next steps                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Input Processing

```
User provides URL
    ↓
Validate format (regex: youtube.com/watch?v= or youtu.be/)
    ↓
Extract video_id (11-character alphanumeric)
    ↓
Normalize to standard format
    ↓
Pass to yt-dlp
```

### Metadata Extraction

```
Execute: yt-dlp --dump-json --skip-download URL
    ↓
Receive JSON on stdout
    ↓
Parse JSON → Python dict
    ↓
Validate required fields present
```

### Transformation

```
Raw yt-dlp JSON
    ↓
Map fields:
  • upload_date (YYYYMMDD) → ISO 8601 date
  • timestamp (unix) → Creation timestamp
  • duration (seconds) → HH:MM:SS format
  • tags (array) → YAML list
  • description (text) → Sanitized markdown
    ↓
Generate YAML front matter
    ↓
Build markdown template
```

### File Writing

```
Generate filename:
  YYYY-MM-DD - {sanitized_title}.md
    ↓
Check if file exists
  → If exists: Append counter (2), (3), etc.
    ↓
Write to $OBSVAULT/youtube/ directory
    ↓
Return file path
```

---

## Component Specifications

### Component 1: Input Validator

**File**: `lib/validator.py`  
**Responsibility**: Validate and normalize YouTube URLs

```python
def validate_url(url: str) -> tuple[bool, str, Optional[str]]:
    """
    Validates YouTube URL and extracts video ID.
    
    Args:
        url: Raw input URL
        
    Returns:
        (is_valid, normalized_url, video_id)
        
    Examples:
        >>> validate_url("https://youtu.be/dQw4w9WgXcQ")
        (True, "https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")
        
        >>> validate_url("https://example.com")
        (False, "", None)
    """
```

**Supported URL Formats**:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/watch?v=VIDEO_ID&t=123s` (strips params)
- `https://m.youtube.com/watch?v=VIDEO_ID` (mobile)

**Validation Logic**:
1. Check URL contains youtube.com or youtu.be
2. Extract video_id using regex: `[a-zA-Z0-9_-]{11}`
3. Normalize to canonical format
4. Return validation result

**Error Cases**:
- Invalid URL format → `(False, "", None)` + error message
- Non-YouTube URL → Clear rejection message
- Playlist URL → Error (Phase 1 is single-video only)

---

### Component 2: Metadata Extractor

**File**: `lib/extractor.py`  
**Responsibility**: Execute yt-dlp and parse JSON response

```python
def extract_metadata(
    url: str, 
    cookies_browser: Optional[str] = None
) -> dict:
    """
    Extracts metadata using yt-dlp.
    
    Args:
        url: Normalized YouTube URL
        cookies_browser: Optional browser for cookie extraction
        
    Returns:
        Parsed JSON metadata dictionary
        
    Raises:
        ExtractionError: If yt-dlp fails
        VideoUnavailableError: If video is deleted/private
        AgeRestrictedError: If age-gated without cookies
    """
```

**yt-dlp Command**:
```bash
yt-dlp \
  --dump-json \
  --skip-download \
  --no-warnings \
  --cookies-from-browser {browser} \  # Optional
  {url}
```

**Key Metadata Fields Extracted**:
```json
{
  "id": "VIDEO_ID",
  "title": "Video Title",
  "uploader": "Channel Name",
  "uploader_id": "@channel_handle",
  "channel_id": "UC...",
  "upload_date": "20231208",
  "timestamp": 1701993600,
  "duration": 1234,
  "view_count": 50000,
  "like_count": 1500,
  "description": "Full description...",
  "tags": ["tag1", "tag2"],
  "categories": ["Education"],
  "thumbnail": "https://...",
  "webpage_url": "https://...",
  "availability": "public",
  "age_limit": 0
}
```

**Error Handling**:
- yt-dlp exit code 1 → Parse stderr for reason
- "Video unavailable" → Raise VideoUnavailableError
- "Sign in to confirm" → Raise AgeRestrictedError (suggest cookies)
- HTTP 429 → Raise RateLimitError (trigger retry)
- Network error → Raise NetworkError (trigger retry)

**Retry Logic**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def extract_with_retry(url: str) -> dict:
    return extract_metadata(url)
```

---

### Component 3: Front Matter Generator

**File**: `lib/formatter.py`  
**Responsibility**: Transform yt-dlp JSON into Obsidian YAML front matter

```python
def generate_frontmatter(metadata: dict) -> str:
    """
    Generates Obsidian-compatible YAML front matter.
    
    Args:
        metadata: Parsed yt-dlp JSON
        
    Returns:
        YAML front matter as string (including --- delimiters)
    """
```

**Output Format**:
```yaml
---
# Identification
url: https://youtube.com/watch?v=VIDEO_ID
video_id: VIDEO_ID
title: Video Title Here
channel: Channel Name
channel_id: "@channel_handle"

# Metadata
upload_date: 2023-12-08
created: 2024-12-08T15:30:00-05:00  # ISO 8601 with timezone
duration: 20:34
duration_seconds: 1234

# Engagement Metrics (as of extraction date)
views: 50000
likes: 1500

# Organization
tags: 
  - youtube
  - video-note
  - {category-tag}
categories:
  - Education
  
# Status
status: raw  # raw | processed | archived
---
```

**Timestamp Formatting**:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

# Parse upload_date (YYYYMMDD)
upload_dt = datetime.strptime(metadata['upload_date'], '%Y%m%d')
upload_str = upload_dt.strftime('%Y-%m-%d')

# Current timestamp with timezone
created = datetime.now(ZoneInfo('America/New_York')).isoformat()

# Duration formatting
def format_duration(seconds: int) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
```

**Text Sanitization**:
```python
def sanitize_for_yaml(text: str) -> str:
    """Escape special YAML characters"""
    # Escape quotes, colons, newlines
    # Wrap in quotes if contains special chars
    return yaml.safe_dump(text).strip()
```

**Tag Sanitization** (Critical for Obsidian Compatibility):
```python
def sanitize_tag(tag: str) -> str:
    """
    Sanitize tags to be Obsidian-compatible.
    
    Obsidian tags must:
    - Be lowercase
    - Contain no spaces (replaced with hyphens)
    - Only include: a-z, 0-9, -, _, /
    - Have at least one non-numeric character
    
    Examples:
        "Chinese AI" → "chinese-ai"
        "who is minimax" → "who-is-minimax"
        "AI--Research" → "ai-research"
    """
    # Convert to lowercase
    tag = tag.lower()
    
    # Replace spaces with hyphens
    tag = tag.replace(" ", "-")
    
    # Remove invalid characters (keep: a-z, 0-9, -, _, /)
    tag = re.sub(r'[^a-z0-9\-_/]', '', tag)
    
    # Remove duplicate hyphens
    tag = re.sub(r'-+', '-', tag)
    
    # Remove leading/trailing hyphens
    tag = tag.strip('-')
    
    return tag
```

All YouTube tags are automatically sanitized before being written to YAML front matter.
This ensures tags are properly recognized and linkable in Obsidian.

---

### Component 4: Markdown Generator

**File**: `lib/formatter.py`  
**Responsibility**: Create complete markdown file with structure

```python
def generate_markdown(frontmatter: str, metadata: dict) -> str:
    """
    Generates complete markdown file content.
    
    Args:
        frontmatter: Generated YAML front matter
        metadata: Original yt-dlp JSON
        
    Returns:
        Complete markdown file as string
    """
```

**Template**:
````markdown
---
{YAML FRONT MATTER}
---

# {title}

**Channel:** [{channel}]({channel_url})  
**Published:** {upload_date}  
**Duration:** {duration}  

---

## Description

{description}

---

## Notes

<!-- Add your notes here -->

---

## Transcript

<!-- Phase 2: Transcript will be inserted here -->

---

## Related

<!-- Links to related notes -->

---

## Metadata

**Video ID:** `{video_id}`  
**Views:** {views:,} (as of {extraction_date})  
**Likes:** {likes:,}  
**Tags:** {tags_comma_separated}
````

---

### Component 5: File System Manager

**File**: `lib/filesystem.py`  
**Responsibility**: Handle file naming, creation, and collision resolution

```python
def save_markdown(
    content: str, 
    title: str, 
    upload_date: str,
    output_dir: Path = None  # Defaults to $OBSVAULT/youtube if None
) -> Path:
    """
    Saves markdown file to filesystem.
    
    Args:
        content: Complete markdown content
        title: Video title (for filename)
        upload_date: YYYYMMDD format
        output_dir: Target directory (defaults to $OBSVAULT/youtube)
        
    Returns:
        Path to created file
        
    Raises:
        FileSystemError: If write fails
    """
```

**Filename Generation**:
```python
def generate_filename(title: str, upload_date: str) -> str:
    """
    Format: YYYY-MM-DD - {sanitized_title}.md
    Example: 2023-12-08 - How to Use yt-dlp.md
    """
    # Sanitize title
    safe_title = sanitize_title(title)
    
    # Format date
    date_obj = datetime.strptime(upload_date, '%Y%m%d')
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # Truncate if too long
    max_title_length = 100
    if len(safe_title) > max_title_length:
        safe_title = safe_title[:max_title_length].rsplit(' ', 1)[0]
    
    return f"{date_str} - {safe_title}.md"

def sanitize_title(title: str) -> str:
    """Remove filesystem-unsafe characters"""
    # Remove: / \ : * ? " < > |
    unsafe_chars = r'[/\\:*?"<>|]'
    clean = re.sub(unsafe_chars, '', title)
    # Replace multiple spaces with single
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
```

**Collision Handling**:
```python
def resolve_collision(filepath: Path) -> Path:
    """
    If file exists, append counter.
    
    Example:
        2023-12-08 - Video Title.md (exists)
        → 2023-12-08 - Video Title (2).md
        → 2023-12-08 - Video Title (3).md
    """
    if not filepath.exists():
        return filepath
    
    counter = 2
    stem = filepath.stem
    parent = filepath.parent
    suffix = filepath.suffix
    
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
```

---

## Error Handling

### Error Taxonomy

| Error Type | Exception Class | Handling Strategy | User Message |
|------------|----------------|-------------------|--------------|
| Invalid URL | `ValueError` | Reject immediately | "Invalid YouTube URL. Expected: https://youtube.com/watch?v=..." |
| Video unavailable | `VideoUnavailableError` | Check reason, report | "Video unavailable: {private/deleted/geo-blocked}" |
| Age-restricted | `AgeRestrictedError` | Suggest cookies | "Age-restricted. Retry with: --cookies firefox" |
| Network error | `NetworkError` | Retry with backoff | "Network error. Retrying in {seconds}s..." |
| Rate limiting | `RateLimitError` | Exponential backoff | "Rate limited. Waiting {seconds}s..." |
| File write error | `FileSystemError` | Check permissions | "Cannot write to {path}. Check permissions." |
| yt-dlp not found | `CommandNotFoundError` | Installation guide | "yt-dlp not installed. Run: pip install yt-dlp" |

### Retry Strategy

```python
# Network errors: 3 attempts, exponential backoff
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((NetworkError, RateLimitError))
)
def extract_with_retry(url: str) -> dict:
    pass

# Rate limiting: Special handling
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(RateLimitError)
)
def extract_rate_limited(url: str) -> dict:
    pass
```

---

## Configuration

### Configuration File: `config.yaml`

```yaml
# Output settings
output:
  directory: $OBSVAULT/youtube  # Uses OBSVAULT environment variable
  filename_format: "{date} - {title}.md"
  max_title_length: 100

# yt-dlp settings
ytdlp:
  cookies_browser: firefox  # firefox | chrome | safari | null
  user_agent: null           # null = default
  proxy: null                # null | socks5://127.0.0.1:1080
  rate_limit: null           # null | "5M"

# Metadata settings
metadata:
  include_description: true
  include_tags: true
  include_metrics: true       # views, likes
  timestamp_format: iso8601   # iso8601 | unix
  timezone: America/New_York

# Advanced
advanced:
  retry_attempts: 3
  retry_backoff: exponential
  verbose: false
  dry_run: false
```

### Configuration Loading

```python
from pathlib import Path
import yaml

DEFAULT_CONFIG = {
    "output": {
        "directory": None,  # Will use $OBSVAULT/youtube if not set
        "filename_format": "{date} - {title}.md",
        "max_title_length": 100
    },
    "ytdlp": {
        "cookies_browser": "firefox",
        "user_agent": None,
        "proxy": None,
        "rate_limit": None
    },
    "metadata": {
        "include_description": True,
        "include_tags": True,
        "include_metrics": True,
        "timestamp_format": "iso8601",
        "timezone": "America/New_York"
    },
    "advanced": {
        "retry_attempts": 3,
        "retry_backoff": "exponential",
        "verbose": False,
        "dry_run": False
    }
}

def load_config() -> dict:
    """Load config with fallback to defaults"""
    config_path = Path.home() / ".config" / "yt-obsidian" / "config.yaml"
    
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f)
        # Merge with defaults (deep merge)
        config = deep_merge(DEFAULT_CONFIG, user_config)
    else:
        config = DEFAULT_CONFIG
    
    # Resolve output directory: use $OBSVAULT/youtube if not set
    if config["output"]["directory"] is None:
        obsvault = os.getenv("OBSVAULT")
        if obsvault:
            config["output"]["directory"] = Path(obsvault) / "youtube"
    
    return config
```

---

## Testing Strategy

### Test Cases

| Test ID | Scenario | Input | Expected Output | Pass Criteria |
|---------|----------|-------|-----------------|---------------|
| T01 | Standard public video | Valid URL | Markdown with front matter | File created, valid YAML |
| T02 | Age-restricted video | Age-gated URL | Error prompt | Clear message with fix |
| T03 | Invalid URL | `https://example.com` | Error | "Invalid YouTube URL" |
| T04 | Unavailable video | Deleted video URL | Error | "Video unavailable: deleted" |
| T05 | Filename collision | Same video twice | Two files | `(2)` suffix added |
| T06 | Long title | 200-char title | Truncated filename | Max 100 chars |
| T07 | Special characters | Title with `/\:*?` | Sanitized | Safe filename |
| T08 | Duration formatting | 3661 seconds | `1:01:01` | Correct format |
| T09 | Timestamp accuracy | Current time | ISO 8601 + TZ | Correct timezone |
| T10 | YAML validity | All test cases | Valid YAML | Parseable in Obsidian |

### Test Implementation

```python
# tests/test_validator.py
def test_validate_standard_url():
    is_valid, normalized, video_id = validate_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert is_valid
    assert video_id == "dQw4w9WgXcQ"

# tests/test_extractor.py
@pytest.mark.integration
def test_extract_public_video():
    metadata = extract_metadata("https://youtu.be/dQw4w9WgXcQ")
    assert metadata["title"]
    assert metadata["duration"] > 0

# tests/test_formatter.py
def test_generate_frontmatter():
    metadata = {"title": "Test", "upload_date": "20231208", ...}
    yaml_str = generate_frontmatter(metadata)
    # Parse to verify validity
    parsed = yaml.safe_load(yaml_str.split("---")[1])
    assert parsed["title"] == "Test"
```

---

## Performance Considerations

### Execution Time

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| URL validation | <1ms | Regex matching |
| yt-dlp extraction | 1-2s | Network dependent |
| JSON parsing | <10ms | Standard library |
| Front matter generation | <50ms | String formatting |
| File writing | <100ms | Disk I/O |
| **Total** | **~2-3s** | Acceptable for single video |

### Optimization Opportunities (Future)

- Batch processing: Process multiple URLs in parallel
- Caching: Store metadata for duplicate requests
- Async I/O: Non-blocking file operations

---

## Security Considerations

### Input Validation

- **URL sanitization**: Prevent command injection
- **Path traversal**: Ensure output stays in $OBSVAULT/youtube directory
- **Environment variable**: Validate $OBSVAULT is set before execution
- **Filename safety**: Remove/escape dangerous characters

### yt-dlp Execution

```python
# Safe command construction
import subprocess
import shlex

def execute_ytdlp(url: str) -> str:
    """Execute yt-dlp safely"""
    # Validate URL first
    if not is_valid_youtube_url(url):
        raise ValueError("Invalid URL")
    
    # Build command with explicit args (no shell=True)
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        "--no-warnings",
        url  # URL is NOT passed through shell
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,  # Prevent hanging
        check=False  # Handle errors manually
    )
    
    if result.returncode != 0:
        raise ExtractionError(result.stderr)
    
    return result.stdout
```

---

## Future Extensibility

### Phase 2: Transcript Integration

**Changes Required**:
1. Add transcript extraction to `extractor.py`
2. Extend markdown template with transcript section
3. Add transcript formatting logic

**Minimal Impact**: Core architecture remains unchanged

### Phase 3: Audio Download

**Changes Required**:
1. Add audio download function to `extractor.py`
2. Add file management for audio files
3. Link audio file in markdown front matter

**Minimal Impact**: Extends existing components without modification

---

## Summary

**Architecture Characteristics**:
- ✅ Simple: Linear workflow, 5 clear components
- ✅ Fast: ~2-3 seconds per video
- ✅ Reliable: Comprehensive error handling
- ✅ Testable: Clear component boundaries
- ✅ Extensible: Easy to add Phase 2/3 features
- ✅ Maintainable: Well-documented, typed Python

**Ready for Implementation**: All components specified, error cases handled, testing strategy defined.

---

**Next Steps**: Create implementation plan ([PHASE1_IMPLEMENTATION_PLAN.md](./PHASE1_IMPLEMENTATION_PLAN.md))
