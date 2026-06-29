"""
Status display for video processing state.

Provides `yt status VIDEO` functionality to show what has been analyzed
for a video and what patterns have been run.
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .cache_manager import CacheManager, CacheEntry


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from URL or return ID directly.
    
    Args:
        url_or_id: YouTube URL or video ID
        
    Returns:
        Video ID string
    """
    # Common YouTube URL patterns
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    # Return as-is if no pattern matches (let caller handle invalid IDs)
    return url_or_id


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "5:23" or "1:23:45"
    """
    if seconds < 0:
        return "unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to human-readable format.
    
    Args:
        iso_timestamp: ISO format timestamp
        
    Returns:
        Human-readable date string
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_timestamp or "unknown"


def verify_note_exists(cache_entry: CacheEntry) -> bool:
    """Verify that the cached note file still exists.
    
    Args:
        cache_entry: Cache entry to verify
        
    Returns:
        True if note file exists
    """
    note_path = Path(cache_entry.markdown_path).expanduser()
    return note_path.exists()


def display_video_status(url_or_id: str, cache_dir: Path, verbose: bool = False) -> Dict[str, Any]:
    """Display status of a processed video.
    
    Args:
        url_or_id: YouTube URL or video ID
        cache_dir: Path to cache directory
        verbose: Show extra details
        
    Returns:
        Dict with status info (for programmatic use)
    """
    video_id = extract_video_id(url_or_id)
    cache_manager = CacheManager(cache_dir)
    
    result = {
        'video_id': video_id,
        'found': False,
        'note_exists': False,
        'patterns_run': [],
        'cache_entry': None
    }
    
    # Check if video is in cache
    if not cache_manager.exists(video_id):
        print(f"\n  Video not found in cache: {video_id}")
        print(f"  Run: ./yt \"https://youtube.com/watch?v={video_id}\" to process")
        return result
    
    # Load cache entry
    cache = cache_manager.get_cache(video_id)
    if not cache:
        print(f"\n  Cache corrupted for: {video_id}")
        print(f"  Run: ./yt --force \"URL\" to re-process")
        return result
    
    result['found'] = True
    result['cache_entry'] = cache
    result['patterns_run'] = cache.patterns_run
    
    # Verify note still exists
    note_exists = verify_note_exists(cache)
    result['note_exists'] = note_exists
    
    # Display status
    print(f"\n  Video Status: {video_id}")
    print(f"  {'=' * 50}")
    print(f"  Title: {cache.title}")
    print(f"  Duration: {format_duration(cache.duration_seconds)}")
    print(f"  Upload Date: {cache.upload_date}")
    print(f"  Words: {cache.transcript_word_count:,}")
    print()
    
    # Note status
    if note_exists:
        print(f"  Note: {cache.markdown_path}")
    else:
        print(f"  Note: MISSING (was: {cache.markdown_path})")
        print(f"        Cache exists but note was deleted.")
        print(f"        Run: ./yt --force \"URL\" to regenerate")
    print()
    
    # Patterns run
    print(f"  Patterns Run ({len(cache.patterns_run)}):")
    if cache.patterns_run:
        for i, pattern in enumerate(cache.patterns_run, 1):
            print(f"    {i:2}. {pattern}")
    else:
        print(f"    (none)")
    print()
    
    # Last updated
    print(f"  Last Updated: {format_timestamp(cache.last_updated)}")
    
    # Verbose: show processing history
    if verbose and cache.processing_history:
        print()
        print(f"  Processing History:")
        for i, event in enumerate(cache.processing_history, 1):
            mode = event.get('mode', 'unknown')
            timestamp = format_timestamp(event.get('timestamp', ''))
            success = "" if event.get('success', True) else " (FAILED)"
            print(f"    {i}. [{timestamp}] {mode}{success}")
            
            if event.get('patterns_run'):
                print(f"       Patterns: {len(event['patterns_run'])}")
            if event.get('patterns_appended'):
                print(f"       Appended: {', '.join(event['patterns_appended'])}")
            if event.get('tokens_used'):
                print(f"       Tokens: {event['tokens_used']:,}")
    
    print()
    
    # Suggestions
    if note_exists:
        print(f"  Actions:")
        print(f"    Add patterns:  ./yt --append --patterns PATTERN \"{video_id}\"")
        print(f"    Re-analyze:    ./yt --force \"URL\"")
    
    print()
    
    return result


def display_status_compact(url_or_id: str, cache_dir: Path) -> Optional[str]:
    """Display compact one-line status for a video.
    
    Args:
        url_or_id: YouTube URL or video ID
        cache_dir: Path to cache directory
        
    Returns:
        Status line or None if not found
    """
    video_id = extract_video_id(url_or_id)
    cache_manager = CacheManager(cache_dir)
    
    if not cache_manager.exists(video_id):
        return None
    
    cache = cache_manager.get_cache(video_id)
    if not cache:
        return f"{video_id}: CACHE_CORRUPT"
    
    note_status = "" if verify_note_exists(cache) else " [NOTE_MISSING]"
    pattern_count = len(cache.patterns_run)
    
    # Truncate title if too long
    title = cache.title
    if len(title) > 40:
        title = title[:37] + "..."
    
    return f"{video_id}: {title} ({pattern_count} patterns){note_status}"
