"""URL validation utilities for the yt-obsidian pipeline."""

from __future__ import annotations

import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .exceptions import ValidationError

_VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")
_ALLOWED_HOSTS = {"youtube.com", "m.youtube.com"}
_SHORT_HOST = "youtu.be"
_CANONICAL_URL = "https://youtube.com/watch?v={video_id}"


def _normalize_netloc(netloc: str) -> str:
    """Return a lowercase host without leading www. or port information."""
    host = netloc.split(":", 1)[0].lower()
    if host.startswith("www."):
        return host[4:]
    return host


def _parse_url(raw_url: str) -> Tuple[str, str, str, str]:
    """Parse the raw URL, adding https:// if missing, and return components."""
    parsed = urlparse(raw_url)
    if not parsed.scheme:
        parsed = urlparse(f"https://{raw_url}")
    if not parsed.netloc and parsed.path:
        parsed = urlparse(f"https://{raw_url}")
    return parsed.scheme, parsed.netloc, parsed.path, parsed.query


def validate_url(url: str) -> tuple[bool, str, Optional[str]]:
    """Validate a YouTube URL, returning canonical form and video ID."""
    normalized = url.strip()
    if not normalized:
        raise ValidationError("YouTube URL is required.")

    scheme, netloc, path, query = _parse_url(normalized)
    if not netloc:
        raise ValidationError("URL is missing a host component.")

    host = _normalize_netloc(netloc)

    if host not in _ALLOWED_HOSTS and host != _SHORT_HOST:
        raise ValidationError("Only youtube.com and youtu.be links are supported.")

    if path.lower().startswith("/playlist"):
        raise ValidationError("Playlist URLs are not supported in Phase 1.")

    query_params = parse_qs(query)
    if "list" in query_params and "v" not in query_params:
        raise ValidationError("Playlist URLs are not supported in Phase 1.")

    video_id: Optional[str] = None

    if host == _SHORT_HOST:
        trimmed_path = path.lstrip("/")
        if trimmed_path:
            video_id = trimmed_path.split("/", 1)[0]
    else:
        video_values = query_params.get("v")
        if video_values:
            video_id = video_values[0]

    if not video_id:
        raise ValidationError("Unable to extract a YouTube video ID from the URL.")

    if not _VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValidationError("YouTube video IDs must be 11 characters long.")

    normalized_url = _CANONICAL_URL.format(video_id=video_id)
    return True, normalized_url, video_id
