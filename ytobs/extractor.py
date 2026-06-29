"""
Metadata and transcript extraction via yt-dlp library mode.

Uses yt-dlp Python API for unified extraction with error handling and retry logic.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import yt_dlp  # type: ignore[import]

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)  # type: ignore[import]

from .exceptions import (
    AgeRestrictedError,
    ExtractionError,
    NetworkError,
    RateLimitError,
    VideoUnavailableError,
)
from .transcript import extract_transcript_from_info, get_transcript_metadata


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((NetworkError, RateLimitError)),
    reraise=True,
)
def extract_metadata(
    url: str,
    cookies_browser: Optional[str] = None,
    extract_transcript: bool = True,
    transcript_lang: str = "en",
) -> Dict[str, Any]:
    """
    Extract video metadata and transcript using yt-dlp library mode.

    Args:
        url: YouTube video URL (must be normalized)
        cookies_browser: Optional browser to extract cookies from
                        (e.g., "firefox", "chrome") for age-restricted videos
        extract_transcript: Whether to extract transcript (default: True)
        transcript_lang: Preferred transcript language (default: 'en')

    Returns:
        Dictionary containing:
            - 'metadata': All video metadata fields
            - 'transcript': Transcript text or None
            - 'transcript_info': Transcript metadata dict

    Raises:
        CommandNotFoundError: yt-dlp not found
        VideoUnavailableError: Video is deleted, private, or geo-blocked
        AgeRestrictedError: Video requires age verification
        RateLimitError: YouTube rate limiting detected (triggers retry)
        NetworkError: Network connection issue (triggers retry)
        ExtractionError: Other yt-dlp failures

    Example:
        >>> result = extract_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(result['metadata']["title"])
        "Rick Astley - Never Gonna Give You Up"
        >>> print(result['transcript'][:100] if result['transcript'] else "No transcript")
    """
    # Build yt-dlp options
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    # Add subtitle extraction if requested
    if extract_transcript:
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True

    # Add cookies if specified
    if cookies_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_browser, None)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ExtractionError("yt-dlp returned empty metadata.")

        # Extract transcript if requested
        transcript = None
        transcript_info: Dict[str, Any] = {"transcript_available": False}

        if extract_transcript:
            try:
                transcript = extract_transcript_from_info(info, lang=transcript_lang)
                transcript_info = get_transcript_metadata(
                    info, transcript, lang=transcript_lang
                )
            except Exception as e:
                # Graceful degradation: continue even if transcript fails
                pass

        return {
            "metadata": info,
            "transcript": transcript,
            "transcript_info": transcript_info,
        }

    except Exception as e:
        error_msg = str(e).lower()

        # Map common yt-dlp errors to our exception types
        if any(p in error_msg for p in ["age", "sign in", "restricted"]):
            raise AgeRestrictedError(
                "Video is age restricted. Retry with --cookies-from-browser to provide cookies."
            )
        elif any(p in error_msg for p in ["unavailable", "private", "deleted"]):
            raise VideoUnavailableError(
                "Video is unavailable, private, or geo-blocked."
            )
        elif any(p in error_msg for p in ["429", "rate limit", "too many requests"]):
            raise RateLimitError("YouTube rate limit detected. Please retry later.")
        elif any(p in error_msg for p in ["network", "connection", "timeout", "ssl"]):
            raise NetworkError("Network error while contacting YouTube.")
        else:
            raise ExtractionError(f"Failed to extract metadata: {e}")
