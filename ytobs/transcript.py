"""
Transcript extraction and parsing utilities for YouTube videos.

This module provides functions to extract transcripts from YouTube videos using
yt-dlp library mode, fetch subtitle content, parse JSON3 format, and generate
transcript metadata for Obsidian front matter.

Phase: 1B - Transcript Integration
Status: Implementation skeleton (ready for development)
"""

from typing import Dict, List, Optional, Any
import requests
import re


def extract_transcript_from_info(
    info: Dict[str, Any],
    lang: str = 'en',
    prefer_manual: bool = True
) -> Optional[str]:
    """
    Extract transcript text from yt-dlp info dictionary.
    
    Attempts to extract transcript in the following order:
    1. Manual subtitles (if prefer_manual=True)
    2. Auto-generated captions
    
    Args:
        info: yt-dlp info dictionary containing subtitle metadata
        lang: Language code (e.g., 'en', 'pt') (default: 'en')
        prefer_manual: Prefer manual captions over auto-generated (default: True)
        
    Returns:
        Plain text transcript or None if unavailable
        
    Example:
        >>> info = ydl.extract_info(url, download=False)
        >>> transcript = extract_transcript_from_info(info, lang='en')
        >>> print(transcript[:100])
        'In this video we're exploring the landscape of Chinese AI research...'
    """
    try:
        # Try manual subtitles first (if preferred)
        if prefer_manual:
            subtitles = info.get('subtitles', {})
            if lang in subtitles:
                url = get_best_subtitle_url(subtitles[lang])
                if url:
                    data = fetch_subtitle_content(url)
                    if data:
                        text = parse_json3_to_text(data)
                        if text:
                            return sanitize_transcript_text(text)
        
        # Try auto-generated captions
        auto_captions = info.get('automatic_captions', {})
        if lang in auto_captions:
            url = get_best_subtitle_url(auto_captions[lang])
            if url:
                data = fetch_subtitle_content(url)
                if data:
                    text = parse_json3_to_text(data)
                    if text:
                        return sanitize_transcript_text(text)
        
        # Try manual subtitles as fallback (if we tried auto first)
        if not prefer_manual:
            subtitles = info.get('subtitles', {})
            if lang in subtitles:
                url = get_best_subtitle_url(subtitles[lang])
                if url:
                    data = fetch_subtitle_content(url)
                    if data:
                        text = parse_json3_to_text(data)
                        if text:
                            return sanitize_transcript_text(text)
        
        # Not available
        return None
        
    except Exception as e:
        # Log but don't crash - graceful degradation
        return None


def fetch_subtitle_content(subtitle_url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch subtitle JSON from URL.
    
    Downloads subtitle content from YouTube's subtitle API. Prefers JSON3 format
    for easier parsing.
    
    Args:
        subtitle_url: URL to subtitle file (JSON3 format preferred)
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        Parsed JSON data (dictionary) or None if fetch fails
        
    Raises:
        requests.RequestException: If fetch fails (network error, timeout)
        requests.HTTPError: If HTTP error occurs (404, 403, etc.)
        ValueError: If response is not valid JSON
        
    Example:
        >>> url = "https://www.youtube.com/api/timedtext?v=VIDEO_ID&lang=en&fmt=json3"
        >>> data = fetch_subtitle_content(url)
        >>> print(data.keys())
        dict_keys(['events', 'pens', 'wsWinStyles'])
    """
    try:
        response = requests.get(subtitle_url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise SubtitleFetchError(f"Failed to fetch subtitle: {e}")
    except ValueError as e:
        raise SubtitleParseError(f"Invalid JSON in subtitle response: {e}")


def parse_json3_to_text(json_data: Dict[str, Any]) -> Optional[str]:
    """
    Convert JSON3 subtitle format to plain text.
    
    JSON3 format structure:
        {
            "events": [
                {
                    "tStartMs": 1000,      # Start time in milliseconds
                    "dDurationMs": 5000,   # Duration in milliseconds
                    "segs": [              # Text segments
                        {"utf8": "Hello "},
                        {"utf8": "world"}
                    ]
                },
                ...
            ]
        }
    
    This function extracts all text segments and joins them into a single
    readable string, preserving natural line breaks.
    
    Args:
        json_data: Parsed JSON3 subtitle data
        
    Returns:
        Plain text transcript with newlines preserved, or None if parsing fails
        
    Example:
        >>> json_data = {"events": [{"segs": [{"utf8": "Hello"}, {"utf8": " world"}]}]}
        >>> text = parse_json3_to_text(json_data)
        >>> print(text)
        'Hello world'
    """
    try:
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
        return ' '.join(text_parts) if text_parts else None
        
    except Exception as e:
        raise SubtitleParseError(f"Failed to parse JSON3 format: {e}")


def get_best_subtitle_url(
    subtitle_formats: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Select best subtitle format URL (prefer json3).
    
    Subtitle formats are provided by yt-dlp as a list of available formats.
    This function selects the most suitable format for parsing, preferring
    JSON3 over other formats (VTT, SRT, TTML).
    
    Args:
        subtitle_formats: List of subtitle format dictionaries
            Example: [
                {'ext': 'json3', 'url': 'https://...'},
                {'ext': 'vtt', 'url': 'https://...'},
                {'ext': 'srv1', 'url': 'https://...'}
            ]
    
    Returns:
        URL string or None if no suitable format found
        
    Example:
        >>> formats = [
        ...     {'ext': 'vtt', 'url': 'https://example.com/sub.vtt'},
        ...     {'ext': 'json3', 'url': 'https://example.com/sub.json3'}
        ... ]
        >>> url = get_best_subtitle_url(formats)
        >>> print(url)
        'https://example.com/sub.json3'
    """
    if not subtitle_formats:
        return None
    
    # Priority order (best to worst)
    priority = ['json3', 'srv3', 'vtt', 'srt', 'ttml', 'srv1', 'srv2']
    
    # Try each format in priority order
    for ext in priority:
        for fmt in subtitle_formats:
            if fmt.get('ext') == ext:
                return fmt.get('url')
    
    # Fallback: return first available format
    return subtitle_formats[0].get('url') if subtitle_formats else None


def get_transcript_metadata(
    info: Dict[str, Any],
    transcript: Optional[str],
    lang: str = 'en'
) -> Dict[str, Any]:
    """
    Generate transcript metadata for YAML front matter.
    
    Creates metadata fields that describe the transcript for use in Obsidian
    front matter. Includes availability, language, type (auto/manual), and
    word count.
    
    Args:
        info: yt-dlp info dictionary (contains subtitle metadata)
        transcript: Extracted transcript text (or None)
        lang: Language code used for extraction (default: 'en')
        
    Returns:
        Dictionary with transcript metadata fields:
            {
                'transcript_available': bool,
                'transcript_language': str,        # e.g., 'en'
                'transcript_type': str,            # 'auto' | 'manual'
                'transcript_word_count': int
            }
            
    Example:
        >>> info = {'subtitles': {'en': [...]}}
        >>> transcript = "This is a test transcript with ten words here."
        >>> metadata = get_transcript_metadata(info, transcript)
        >>> print(metadata)
        {
            'transcript_available': True,
            'transcript_language': 'en',
            'transcript_type': 'manual',
            'transcript_word_count': 10
        }
    """
    if not transcript:
        return {'transcript_available': False}
    
    # Determine transcript type (manual vs auto-generated)
    subtitles = info.get('subtitles', {})
    has_manual = lang in subtitles
    
    # Count words
    word_count = len(transcript.split())
    
    return {
        'transcript_available': True,
        'transcript_language': lang,
        'transcript_type': 'manual' if has_manual else 'auto',
        'transcript_word_count': word_count
    }


def sanitize_transcript_text(text: str) -> Optional[str]:
    """
    Clean up transcript text for readability.
    
    Removes common artifacts from auto-generated transcripts:
    - Multiple consecutive spaces
    - Unusual Unicode characters
    - Music/sound effect markers (e.g., "[Music]", "(applause)")
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned transcript text, or None if sanitization fails
        
    Example:
        >>> text = "Hello  world [Music] this is  a test"
        >>> clean = sanitize_transcript_text(text)
        >>> print(clean)
        'Hello world this is a test'
    """
    if not text:
        return None
    
    try:
        # Remove common sound/music markers
        markers = [
            r'\[Music\]', r'\[music\]', r'\[MUSIC\]',
            r'\[Applause\]', r'\[applause\]', r'\[APPLAUSE\]',
            r'\[Laughter\]', r'\[laughter\]', r'\[LAUGHTER\]',
            r'\(Music\)', r'\(music\)', r'\(MUSIC\)',
            r'\(Applause\)', r'\(applause\)', r'\(APPLAUSE\)',
            r'\(Laughter\)', r'\(laughter\)', r'\(LAUGHTER\)',
        ]
        
        for marker in markers:
            text = re.sub(marker, '', text)
        
        # Remove multiple consecutive spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text if text else None
        
    except Exception:
        return text  # Return original if sanitization fails


# Error classes for transcript operations
class TranscriptError(Exception):
    """Base exception for transcript-related errors."""
    pass


class TranscriptNotAvailableError(TranscriptError):
    """Raised when video has no transcript in requested language."""
    pass


class SubtitleFetchError(TranscriptError):
    """Raised when subtitle content cannot be fetched."""
    pass


class SubtitleParseError(TranscriptError):
    """Raised when subtitle content cannot be parsed."""
    pass


class LanguageNotFoundError(TranscriptError):
    """Raised when requested language is not available."""
    pass
