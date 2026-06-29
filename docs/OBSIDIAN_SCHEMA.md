# Obsidian Front Matter Schema

**Created**: 2024-12-08  
**Purpose**: Define exact YAML front matter structure for YouTube video notes  
**Status**: Specification Complete

---

## Schema Overview

This document defines the YAML front matter structure for YouTube video notes in Obsidian. The schema is designed to be:
- **Obsidian-native**: Uses standard YAML front matter
- **Queryable**: Fields support Dataview queries
- **Extensible**: Easy to add Phase 2/3 fields
- **Valid**: All fields follow YAML specifications

---

## Complete Schema Definition

```yaml
---
# ═══════════════════════════════════════════════════════════════
# IDENTIFICATION (Required)
# ═══════════════════════════════════════════════════════════════
url: string            # Full YouTube URL
video_id: string       # 11-character video ID
title: string          # Video title
channel: string        # Channel display name
channel_id: string     # @handle or UC... ID

# ═══════════════════════════════════════════════════════════════
# TIMESTAMPS (Required)
# ═══════════════════════════════════════════════════════════════
upload_date: date      # YYYY-MM-DD format
created: datetime      # ISO 8601 with timezone (extraction time)

# ═══════════════════════════════════════════════════════════════
# DURATION (Required)
# ═══════════════════════════════════════════════════════════════
duration: string       # HH:MM:SS or MM:SS format
duration_seconds: int  # Integer seconds

# ═══════════════════════════════════════════════════════════════
# ENGAGEMENT METRICS (Optional)
# ═══════════════════════════════════════════════════════════════
views: int             # View count (snapshot)
likes: int             # Like count (snapshot)
metrics_date: date     # When metrics were captured

# ═══════════════════════════════════════════════════════════════
# ORGANIZATION (Required)
# ═══════════════════════════════════════════════════════════════
tags: array[string]    # Obsidian tags
categories: array[string]  # YouTube categories

# ═══════════════════════════════════════════════════════════════
# STATUS (Required)
# ═══════════════════════════════════════════════════════════════
status: enum           # raw | processed | archived

# ═══════════════════════════════════════════════════════════════
# TRANSCRIPT (Phase 1B - Added 2025-12-08)
# ═══════════════════════════════════════════════════════════════
transcript_available: bool       # Whether transcript was extracted
transcript_language: string      # Language code (e.g., 'en', 'pt')
transcript_type: enum            # auto | manual
transcript_word_count: int       # Word count for discovery

# ═══════════════════════════════════════════════════════════════
# EXTENDED METADATA (Optional)
# ═══════════════════════════════════════════════════════════════
thumbnail: string      # Thumbnail URL
age_restricted: bool   # Age restriction flag
availability: string   # public | unlisted | private

# ═══════════════════════════════════════════════════════════════
# FUTURE PHASES
# ═══════════════════════════════════════════════════════════════
audio_file: string     # Phase 3 - Audio download
---
```

---

## Field Specifications

### Required Fields

| Field | Type | Format | Example | Validation |
|-------|------|--------|---------|------------|
| `url` | string | Full URL | `https://youtube.com/watch?v=dQw4w9WgXcQ` | Must match YouTube URL pattern |
| `video_id` | string | 11 chars | `dQw4w9WgXcQ` | `^[a-zA-Z0-9_-]{11}$` |
| `title` | string | UTF-8 | `"Rick Astley - Never Gonna Give You Up"` | Max 200 chars |
| `channel` | string | UTF-8 | `"Rick Astley"` | Max 100 chars |
| `channel_id` | string | @handle or UC ID | `"@RickAstleyYT"` or `"UCuAXFkgsw1L7xaCfnd5JJOw"` | Starts with @ or UC |
| `upload_date` | date | YYYY-MM-DD | `2009-10-25` | ISO 8601 date |
| `created` | datetime | ISO 8601 + TZ | `2024-12-08T15:30:00-05:00` | Full timestamp |
| `duration` | string | HH:MM:SS or MM:SS | `3:32` or `1:02:15` | `^\d{1,2}:\d{2}(:\d{2})?$` |
| `duration_seconds` | int | Seconds | `212` | ≥ 0 |
| `tags` | array | YAML list | `[youtube, music, 80s]` | At least `[youtube]` |
| `categories` | array | YAML list | `[Music]` | From YouTube categories |
| `status` | enum | Fixed values | `raw` | `raw | processed | archived` |

### Optional Fields

| Field | Type | Format | Example | When to Include |
|-------|------|--------|---------|-----------------|
| `views` | int | Number | `50000` | If available (public videos) |
| `likes` | int | Number | `1500` | If available (public videos) |
| `metrics_date` | date | YYYY-MM-DD | `2024-12-08` | Same as extraction date |
| `thumbnail` | string | URL | `https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg` | For embedding |
| `age_restricted` | bool | true/false | `false` | If age-gated |
| `availability` | string | enum | `public` | `public | unlisted | private` |

---

## Data Type Standards

### String Fields

```yaml
# Simple strings (no special characters)
title: Video Title Here

# Strings with special characters (quoted)
title: "Video: Special Characters & Quotes"

# Multi-line strings (literal block)
description: |
  First paragraph of description.
  
  Second paragraph.
```

### Date/DateTime Fields

```yaml
# Date only (upload_date)
upload_date: 2023-12-08  # YYYY-MM-DD

# Full timestamp with timezone (created)
created: 2024-12-08T15:30:00-05:00  # ISO 8601
```

**Python Generation**:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

# Upload date from yt-dlp (YYYYMMDD)
upload_str = datetime.strptime(
    metadata['upload_date'], '%Y%m%d'
).strftime('%Y-%m-%d')

# Created timestamp
created_str = datetime.now(
    ZoneInfo('America/New_York')
).isoformat()
```

### Duration Fields

```yaml
# Human-readable (required for display)
duration: "3:32"      # MM:SS for < 1 hour
duration: "1:02:15"   # HH:MM:SS for ≥ 1 hour

# Machine-readable (required for calculations)
duration_seconds: 212
```

**Python Generation**:
```python
def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
```

### Array Fields

```yaml
# Tags (always include 'youtube')
tags:
  - youtube
  - video-note
  - music
  - 80s

# Categories (from YouTube)
categories:
  - Music
  - Entertainment
```

#### Tag Sanitization (Critical for Obsidian Compatibility)

**Obsidian Tag Requirements:**
- No spaces (tags terminate at whitespace)
- Only lowercase letters, numbers, hyphens (`-`), underscores (`_`), forward slashes (`/`)
- Must contain at least one non-numeric character

**Automatic Sanitization Applied:**

All tags from YouTube are automatically sanitized to meet Obsidian requirements:

| YouTube Tag | Sanitized Tag | Rules Applied |
|-------------|---------------|---------------|
| `Chinese AI` | `chinese-ai` | Lowercase + spaces → hyphens |
| `who is minimax` | `who-is-minimax` | Lowercase + spaces → hyphens |
| `minimax M2` | `minimax-m2` | Lowercase + spaces → hyphens |
| `it's great` | `its-great` | Lowercase + apostrophe removed + hyphen |
| `ai--research` | `ai-research` | Duplicate hyphens removed |

**Python Implementation:**

```python
def sanitize_tag(tag: str) -> str:
    """Sanitize tag to be Obsidian-compatible."""
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

**Result:**
- All tags are guaranteed to be valid Obsidian tags
- Tags are properly recognized and linkable in Obsidian
- Tag search and graph view work correctly

### Enum Fields

```yaml
# Status (workflow tracking)
status: raw          # New note, not yet processed
status: processed    # Reviewed, annotated
status: archived     # Completed, filed away

# Availability
availability: public    # Most videos
availability: unlisted  # Hidden from search
availability: private   # Requires auth
```

---

## Example Front Matter

### Complete Example

```yaml
---
# Identification
url: https://youtube.com/watch?v=dQw4w9WgXcQ
video_id: dQw4w9WgXcQ
title: "Rick Astley - Never Gonna Give You Up (Official Video)"
channel: Rick Astley
channel_id: "@RickAstleyYT"

# Metadata
upload_date: 2009-10-25
created: 2024-12-08T15:30:00-05:00
duration: "3:32"
duration_seconds: 212

# Engagement Metrics (as of 2024-12-08)
views: 1456789012
likes: 16234567
metrics_date: 2024-12-08

# Organization
tags:
  - youtube
  - video-note
  - music
  - 80s
  - rickroll
categories:
  - Music

# Status
status: raw

# Extended
thumbnail: https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg
age_restricted: false
availability: public
---
```

### Minimal Example

```yaml
---
url: https://youtube.com/watch?v=abc123
video_id: abc123
title: Example Video
channel: Example Channel
channel_id: "@example"
upload_date: 2024-12-08
created: 2024-12-08T15:30:00-05:00
duration: "10:30"
duration_seconds: 630
tags: [youtube, video-note]
categories: [Education]
status: raw
---
```

---

## Validation Rules

### Pydantic Schema

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import date, datetime
from typing import Optional, List
from enum import Enum

class Status(str, Enum):
    RAW = "raw"
    PROCESSED = "processed"
    ARCHIVED = "archived"

class Availability(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"

class YouTubeFrontMatter(BaseModel):
    """YouTube video front matter schema"""
    
    # Identification (Required)
    url: HttpUrl
    video_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str = Field(min_length=1, max_length=200)
    channel: str = Field(min_length=1, max_length=100)
    channel_id: str = Field(pattern=r'^(@[a-zA-Z0-9_-]+|UC[a-zA-Z0-9_-]{22})$')
    
    # Timestamps (Required)
    upload_date: date
    created: datetime
    
    # Duration (Required)
    duration: str = Field(pattern=r'^\d{1,2}:\d{2}(:\d{2})?$')
    duration_seconds: int = Field(ge=0)
    
    # Organization (Required)
    tags: List[str] = Field(min_length=1)  # Must include at least 'youtube'
    categories: List[str] = Field(min_length=1)
    status: Status
    
    # Engagement Metrics (Optional)
    views: Optional[int] = Field(None, ge=0)
    likes: Optional[int] = Field(None, ge=0)
    metrics_date: Optional[date] = None
    
    # Extended (Optional)
    thumbnail: Optional[HttpUrl] = None
    age_restricted: Optional[bool] = False
    availability: Optional[Availability] = Availability.PUBLIC
    
    # Phase 2/3 (Future)
    transcript_available: Optional[bool] = None
    audio_file: Optional[str] = None
    
    class Config:
        use_enum_values = True
```

### Validation Function

```python
def validate_frontmatter(yaml_text: str) -> tuple[bool, Optional[str]]:
    """
    Validates YAML front matter against schema.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        data = yaml.safe_load(yaml_text)
        YouTubeFrontMatter(**data)
        return (True, None)
    except ValidationError as e:
        return (False, str(e))
    except yaml.YAMLError as e:
        return (False, f"Invalid YAML: {e}")
```

---

## Obsidian Integration

### Dataview Queries

The schema enables powerful Dataview queries:

```dataview
# All YouTube videos
LIST
FROM #youtube
WHERE status = "raw"
SORT upload_date DESC

# Videos by channel
TABLE duration, views, upload_date
FROM #youtube
WHERE channel = "Example Channel"

# Recently extracted
LIST
FROM #youtube
WHERE created > date(today) - dur(7 days)
SORT created DESC

# Long videos
TABLE channel, duration, views
FROM #youtube
WHERE duration_seconds > 3600
SORT duration_seconds DESC
```

### Templater Integration

```javascript
<%*
// Create note from YouTube URL
const url = await tp.system.prompt("YouTube URL");
// Call yt-obsidian script
const result = await tp.system.suggester(["Extract"], [url]);
%>
```

---

## Phase 2/3 Extensions

### Phase 2: Transcript Fields

```yaml
# Add to front matter
transcript_available: true
transcript_language: en
transcript_type: auto  # auto | manual
transcript_word_count: 1234
```

### Phase 3: Audio Fields

```yaml
# Add to front matter
audio_file: "2024-12-08 - Video Title.opus"
audio_size_mb: 2.5
audio_bitrate: "24k"
```

---

## Migration Strategy

If schema changes in future:

1. **Backward Compatible**: Add new optional fields
2. **Version Field**: Consider adding `schema_version: 1.0`
3. **Migration Script**: Update existing notes if needed

```python
def migrate_schema_v1_to_v2(filepath: Path):
    """Migrate front matter to new schema version"""
    with open(filepath) as f:
        content = f.read()
    
    # Parse front matter
    parts = content.split('---', 2)
    frontmatter = yaml.safe_load(parts[1])
    
    # Add new fields
    frontmatter['schema_version'] = '2.0'
    frontmatter['new_field'] = default_value
    
    # Write back
    new_yaml = yaml.dump(frontmatter, sort_keys=False)
    new_content = f"---\n{new_yaml}---{parts[2]}"
    
    with open(filepath, 'w') as f:
        f.write(new_content)
```

---

## Summary

**Schema Characteristics**:
- ✅ Obsidian-compatible YAML
- ✅ Fully validated with Pydantic
- ✅ Supports Dataview queries
- ✅ Extensible for Phase 2/3
- ✅ Clear field types and formats
- ✅ Example implementations provided

**Ready for Implementation**: Schema is complete and validated.

---

**Next**: Implement in `lib/formatter.py` following this specification.
