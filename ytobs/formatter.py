"""
Front matter and markdown formatter for YouTube video metadata.

This module generates Obsidian-compatible YAML front matter and markdown content
from yt-dlp metadata following the OBSIDIAN_SCHEMA.md specification.
"""

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yaml


def format_duration(seconds: int) -> str:
    """
    Convert seconds to HH:MM:SS or MM:SS format.
    
    Args:
        seconds: Total duration in seconds
        
    Returns:
        Formatted duration string (HH:MM:SS if >= 1 hour, else MM:SS)
        
    Raises:
        ValueError: If seconds is negative
    """
    if seconds < 0:
        raise ValueError("Duration seconds must be non-negative")
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_timestamp(dt_str: str, fmt: str) -> str:
    """
    Parse yt-dlp date and generate formatted timestamp.
    
    Args:
        dt_str: Date string in YYYYMMDD format (from yt-dlp)
        fmt: Output format - "date" for YYYY-MM-DD, "iso" for ISO 8601 with timezone
        
    Returns:
        Formatted timestamp string
    """
    # Parse upload_date (YYYYMMDD format)
    parsed_date = datetime.strptime(dt_str, "%Y%m%d")
    
    if fmt == "date":
        return parsed_date.strftime("%Y-%m-%d")
    elif fmt == "iso":
        # Use current time with timezone for created timestamp
        now = datetime.now(ZoneInfo("America/New_York"))
        return now.isoformat()
    else:
        raise ValueError(f"Unknown format: {fmt}")


def sanitize_tag(tag: str) -> str:
    """
    Sanitize tag to be Obsidian-compatible.
    
    Converts to lowercase, replaces spaces with hyphens, removes invalid characters.
    
    Args:
        tag: Original tag string
        
    Returns:
        Sanitized tag string
    """
    # Convert to lowercase
    tag = tag.lower()
    
    # Replace spaces with hyphens
    tag = tag.replace(" ", "-")
    
    # Remove all characters except alphanumeric, hyphen, underscore, forward slash
    tag = re.sub(r'[^a-z0-9\-_/]', '', tag)
    
    # Remove duplicate hyphens
    tag = re.sub(r'-+', '-', tag)
    
    # Remove leading/trailing hyphens
    tag = tag.strip('-')
    
    return tag


def _ensure_required_tags(tags: list[str] | None) -> list[str]:
    """
    Ensure required tags (youtube, video-note) are present and sanitize all tags.
    
    Args:
        tags: Original tag list or None
        
    Returns:
        Tag list with required tags included and all tags sanitized
    """
    result = ["youtube", "video-note"]
    
    if tags:
        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean:
                # Sanitize the tag
                sanitized = sanitize_tag(tag_clean)
                # Only add if valid and not duplicate
                if sanitized and sanitized not in result:
                    result.append(sanitized)
    
    return result


def generate_frontmatter(metadata: dict[str, Any]) -> str:
    """
    Generate YAML front matter from yt-dlp metadata.
    
    Args:
        metadata: Dictionary containing yt-dlp JSON output
        
    Returns:
        Complete YAML front matter string including --- delimiters
        
    Raises:
        ValueError: If required fields are missing
    """
    # Validate required fields
    if not metadata.get("upload_date"):
        raise ValueError("Missing required field: upload_date")
    if metadata.get("duration") is None:
        raise ValueError("Missing required field: duration")
    
    # Build front matter dictionary in order
    frontmatter_data: dict[str, Any] = {}
    
    # Identification (Required)
    frontmatter_data["url"] = metadata.get("webpage_url", "")
    frontmatter_data["video_id"] = metadata.get("id", "")
    frontmatter_data["title"] = metadata.get("title", "")
    frontmatter_data["channel"] = metadata.get("channel", "")
    frontmatter_data["channel_id"] = metadata.get("channel_id", "")
    
    # Timestamps (Required)
    upload_date_str = metadata["upload_date"]
    frontmatter_data["upload_date"] = format_timestamp(upload_date_str, "date")
    frontmatter_data["created"] = format_timestamp(upload_date_str, "iso")
    
    # Duration (Required)
    duration_seconds = int(metadata["duration"])
    frontmatter_data["duration"] = format_duration(duration_seconds)
    frontmatter_data["duration_seconds"] = duration_seconds
    
    # Engagement Metrics (Optional)
    if "view_count" in metadata and metadata["view_count"] is not None:
        frontmatter_data["views"] = metadata["view_count"]
    if "like_count" in metadata and metadata["like_count"] is not None:
        frontmatter_data["likes"] = metadata["like_count"]
    
    # Only include metrics_date if we have metrics
    if "views" in frontmatter_data or "likes" in frontmatter_data:
        frontmatter_data["metrics_date"] = format_timestamp(upload_date_str, "date")
    
    # Organization (Required)
    frontmatter_data["tags"] = _ensure_required_tags(metadata.get("tags"))
    frontmatter_data["categories"] = metadata.get("categories", [])
    
    # Status (Required)
    frontmatter_data["status"] = metadata.get("status", "raw")
    
    # Transcript (Phase 1B)
    if "transcript_available" in metadata:
        frontmatter_data["transcript_available"] = metadata["transcript_available"]
    if "transcript_language" in metadata:
        frontmatter_data["transcript_language"] = metadata["transcript_language"]
    if "transcript_type" in metadata:
        frontmatter_data["transcript_type"] = metadata["transcript_type"]
    if "transcript_word_count" in metadata:
        frontmatter_data["transcript_word_count"] = metadata["transcript_word_count"]
    
    # Extended Metadata (Optional)
    if "thumbnail" in metadata and metadata["thumbnail"]:
        frontmatter_data["thumbnail"] = metadata["thumbnail"]
    
    if "age_limit" in metadata and metadata["age_limit"]:
        frontmatter_data["age_restricted"] = metadata["age_limit"] >= 18
    
    if "availability" in metadata and metadata["availability"]:
        frontmatter_data["availability"] = metadata["availability"]
    
    # Generate YAML with proper formatting
    yaml_content = yaml.safe_dump(
        frontmatter_data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False
    )
    
    return f"---\n{yaml_content}---"


def generate_markdown(
    frontmatter: str, 
    metadata: dict[str, Any],
    transcript: str | None = None,
    ai_analysis: dict[str, str] | None = None
) -> str:
    """
    Generate complete markdown file content.
    
    Args:
        frontmatter: Generated YAML front matter (with delimiters)
        metadata: Original yt-dlp metadata dictionary
        transcript: Optional transcript text to include
        ai_analysis: Optional dict of pattern_name -> analysis_text (Phase 1C)
        
    Returns:
        Complete markdown file content
    """
    # Extract key fields
    title = metadata.get("title", "Untitled Video")
    channel = metadata.get("channel", "Unknown Channel")
    channel_url = metadata.get("channel_url", "")
    
    upload_date = format_timestamp(
        metadata.get("upload_date", "19700101"), 
        "date"
    )
    
    duration_seconds = int(metadata.get("duration", 0))
    duration = format_duration(duration_seconds)
    
    description = metadata.get("description", "")
    
    # Build metadata section
    video_id = metadata.get("id", "")
    view_count = metadata.get("view_count")
    like_count = metadata.get("like_count")
    tags = _ensure_required_tags(metadata.get("tags"))
    
    metadata_lines = [f"**Video ID:** `{video_id}`  "]
    
    if view_count is not None:
        metadata_lines.append(f"**Views:** {view_count:,}  ")
    
    if like_count is not None:
        metadata_lines.append(f"**Likes:** {like_count:,}  ")
    
    metadata_lines.append(f"**Tags:** {', '.join(tags)}")
    
    # Add transcript info if available
    if metadata.get("transcript_available"):
        word_count = metadata.get("transcript_word_count", 0)
        transcript_type = metadata.get("transcript_type", "unknown")
        metadata_lines.append(f"**Transcript:** {word_count:,} words ({transcript_type})")
    
    # Build transcript section
    if transcript:
        transcript_section = f"""## Transcript

{transcript}"""
    else:
        transcript_section = """## Transcript

<!-- Transcript not available for this video -->"""
    
    # Build AI analysis section (Phase 1C) - appended at the END
    ai_analysis_section = ""
    if ai_analysis:
        ai_parts = []
        ai_parts.append("\n---\n")
        ai_parts.append("## AI Analysis\n")
        
        for pattern_name, analysis_text in ai_analysis.items():
            # Format pattern name for display
            display_name = pattern_name.replace('_', ' ').title()
            ai_parts.append(f"### {display_name}\n")
            ai_parts.append(f"{analysis_text}\n")
        
        ai_analysis_section = "\n".join(ai_parts)
    
    # Build complete markdown
    # Order: metadata → description → notes → transcript → AI analysis → related → metadata
    markdown_content = f"""{frontmatter}

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

{transcript_section}
{ai_analysis_section}

---

## Related

<!-- Links to related notes -->

---

## Metadata

{chr(10).join(metadata_lines)}
"""
    
    return markdown_content
