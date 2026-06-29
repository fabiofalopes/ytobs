"""YouTube channel operations for yt-obsidian."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ChannelVideo:
    """Represents a single video from a channel."""

    video_id: str
    title: str
    duration: Optional[str]
    upload_date: str
    url: str
    view_count: Optional[int] = None

    @property
    def formatted_date(self) -> str:
        """Format upload date as YYYY-MM-DD."""
        if len(self.upload_date) == 8:
            return f"{self.upload_date[0:4]}-{self.upload_date[4:6]}-{self.upload_date[6:8]}"
        return self.upload_date


def is_channel_url(url: str) -> bool:
    """Check if URL is a channel URL (not a video URL)."""
    url_lower = url.lower()

    # Channel URL patterns
    channel_patterns = [
        "/@",
        "/c/",
        "/channel/",
        "/user/",
        "youtu.be/@",
    ]

    # Exclude video URLs
    if "watch?v=" in url_lower or "youtu.be/" in url_lower and "/@" not in url_lower:
        return False

    # Check for channel patterns
    return any(pattern in url_lower for pattern in channel_patterns)


def fetch_channel_videos(
    channel_url: str,
    order: str = "date",
    limit: Optional[int] = None,
    reverse: bool = False,
) -> List[ChannelVideo]:
    """
    Fetch all videos from a YouTube channel.

    Args:
        channel_url: Channel URL
        order: "date" or "views" (note: flat-playlist doesn't respect ordering,
              use reverse parameter for oldest/newest)
        limit: Maximum number of videos to fetch
        reverse: Reverse the order (for oldest-first)

    Returns:
        List of ChannelVideo objects
    """
    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(duration_string)s|%(upload_date)s|%(view_count)s",
        "--no-warnings",
    ]

    if reverse:
        cmd.append("--playlist-reverse")

    cmd.append(channel_url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise RuntimeError("yt-dlp command not found. Is yt-dlp installed?")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Fetching channel videos timed out after 60s")

    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch channel videos: {result.stderr}")

    # Parse output
    videos = []
    lines = result.stdout.strip().split("\n")

    for line in lines:
        if not line:
            continue

        parts = line.split("|")
        if len(parts) < 4:
            continue

        video_id = parts[0]
        title = parts[1]
        duration = parts[2] if len(parts) > 2 and parts[2] != "NA" else None
        upload_date = parts[3]
        view_count = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None

        videos.append(
            ChannelVideo(
                video_id=video_id,
                title=title,
                duration=duration,
                upload_date=upload_date,
                url=f"https://www.youtube.com/watch?v={video_id}",
                view_count=view_count,
            )
        )

        if limit and len(videos) >= limit:
            break

    return videos


def get_channel_info(channel_url: str) -> Dict[str, str]:
    """
    Get basic channel information.

    Returns:
        Dict with 'name' and 'id' keys
    """
    # Use --print to extract channel name and ID
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(channel)s|%(channel_id)s",
        "--no-warnings",
        channel_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"name": "Unknown", "id": "unknown"}
    except subprocess.TimeoutExpired:
        return {"name": "Unknown", "id": "unknown"}

    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split("|")
        if len(parts) >= 2:
            return {
                "name": parts[0] or "Unknown",
                "id": parts[1] or "unknown",
            }

    return {
        "name": "Unknown",
        "id": "unknown",
    }


def list_videos_table(videos: List[ChannelVideo], show_max: int = 50) -> str:
    """
    Format videos as a readable table.

    Args:
        videos: List of ChannelVideo objects
        show_max: Maximum videos to show

    Returns:
        Formatted string
    """
    lines = []
    show_count = min(show_max, len(videos))

    lines.append(f"📺 Channel Videos (showing {show_count} of {len(videos)})")
    lines.append("=" * 80)
    lines.append("")

    for i, video in enumerate(videos[:show_max], 1):
        lines.append(f"{i:3d}. {video.title}")
        lines.append(f"     🔗 {video.url}")
        lines.append(f"     📅 {video.formatted_date} | ⏱️  {video.duration or 'N/A'}")
        lines.append("")

    if len(videos) > show_max:
        lines.append(f"... and {len(videos) - show_max} more videos")
        lines.append("")

    return "\n".join(lines)


def export_videos_json(videos: List[ChannelVideo], output_path: Path) -> None:
    """
    Export videos to JSON file.

    Args:
        videos: List of ChannelVideo objects
        output_path: Path to output JSON file
    """
    import json

    data = [
        {
            "id": v.video_id,
            "title": v.title,
            "url": v.url,
            "duration": v.duration,
            "upload_date": v.upload_date,
            "formatted_date": v.formatted_date,
            "view_count": v.view_count,
        }
        for v in videos
    ]

    try:
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except OSError as e:
        raise RuntimeError(f"Cannot write export file {output_path}: {e}") from e
