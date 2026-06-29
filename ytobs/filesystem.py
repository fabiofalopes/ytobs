"""Filesystem utilities for writing Obsidian-ready markdown files."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .exceptions import FileSystemError

_FALLBACK_TITLE = "Untitled Video"
_MAX_TITLE_LENGTH = 100


def sanitize_title(title: str) -> str:
    """Return a filesystem-safe title string."""

    unsafe_chars = r"[/\\:*?\"<>|]"
    clean = re.sub(unsafe_chars, "", title)
    clean = re.sub(r"\s+", " ", clean)
    sanitized = clean.strip()
    return sanitized or _FALLBACK_TITLE


def slugify_title(title: str) -> str:
    """Convert title to URL-friendly slug format.
    
    Converts title to lowercase, replaces spaces with underscores,
    removes special characters, and limits length.
    
    Args:
        title: Original title string
        
    Returns:
        Slugified title suitable for filenames and URLs
        
    Examples:
        "The Chinese AI Iceberg" -> "the_chinese_ai_iceberg"
        "How to Use GPT-4!" -> "how_to_use_gpt_4"
    """
    # Convert to lowercase
    slug = title.lower()
    
    # Replace spaces and hyphens with underscores
    slug = re.sub(r'[\s-]+', '_', slug)
    
    # Remove all non-alphanumeric characters except underscores
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    
    # Remove duplicate underscores
    slug = re.sub(r'_+', '_', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    
    # Limit length
    if len(slug) > _MAX_TITLE_LENGTH:
        # Truncate at underscore boundary
        truncated = slug[:_MAX_TITLE_LENGTH]
        if '_' in truncated:
            slug = truncated.rsplit('_', 1)[0]
        else:
            slug = truncated
    
    return slug or "untitled_video"


def generate_filename(title: str, upload_date: str, use_slug: bool = True) -> str:
    """Generate sanitized filename including formatted upload date.
    
    Args:
        title: Video title
        upload_date: Upload date in YYYYMMDD format
        use_slug: If True, use slugified title (default). If False, use sanitized title.
        
    Returns:
        Filename string (e.g., "2025-12-08_the_chinese_ai_iceberg.md")
    """

    date_obj = datetime.strptime(upload_date, "%Y%m%d")
    date_str = date_obj.strftime("%Y-%m-%d")

    if use_slug:
        safe_title = slugify_title(title)
        separator = "_"
    else:
        safe_title = sanitize_title(title)
        separator = " - "
        if len(safe_title) > _MAX_TITLE_LENGTH:
            truncated = safe_title[:_MAX_TITLE_LENGTH]
            safe_title = truncated.rsplit(" ", 1)[0] or truncated

    return f"{date_str}{separator}{safe_title}.md"


def resolve_collision(filepath: Path) -> Path:
    """Return a non-conflicting path by appending counters if necessary."""

    if not filepath.exists():
        return filepath

    counter = 2
    stem = filepath.stem
    parent = filepath.parent
    suffix = filepath.suffix

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def save_markdown(
    content: str,
    title: str,
    upload_date: str,
    output_dir: Optional[Path] = None,
) -> Path:
    """Write markdown content to disk, returning the created file path."""

    target_dir = _resolve_output_dir(output_dir)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - platform dependent
        raise FileSystemError(f"Cannot create directory {target_dir}: {exc}") from exc

    try:
        filename = generate_filename(title, upload_date)
    except ValueError as exc:
        raise FileSystemError(f"Invalid upload date '{upload_date}': {exc}") from exc
    candidate_path = target_dir / filename
    final_path = resolve_collision(candidate_path)

    try:
        final_path.write_text(content, encoding="utf-8")
    except OSError as exc:  # pragma: no cover - platform dependent
        raise FileSystemError(f"Cannot write to {final_path}: {exc}") from exc

    return final_path


def _resolve_output_dir(provided_dir: Optional[Path]) -> Path:
    """Determine the output directory, validating OBSVAULT when needed."""

    if provided_dir is not None:
        return provided_dir.expanduser().resolve()

    obs_vault = os.getenv("OBSVAULT")
    if not obs_vault:
        raise FileSystemError("OBSVAULT environment variable is not set")

    base_dir = Path(obs_vault).expanduser()
    return base_dir / "youtube"
