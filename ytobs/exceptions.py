"""
Custom exceptions for YouTube to Obsidian pipeline.

All exceptions inherit from YTObsidianError for easy catching.
"""


class YTObsidianError(Exception):
    """Base exception for all yt-obsidian errors."""
    pass


class VideoUnavailableError(YTObsidianError):
    """Video is deleted, private, or geo-blocked."""
    pass


class AgeRestrictedError(YTObsidianError):
    """Video requires age verification (cookies needed)."""
    pass


class NetworkError(YTObsidianError):
    """Network connection issue."""
    pass


class RateLimitError(YTObsidianError):
    """YouTube rate limiting detected."""
    pass


class ExtractionError(YTObsidianError):
    """General yt-dlp extraction failure."""
    pass


class FileSystemError(YTObsidianError):
    """File system operation failed."""
    pass


class CommandNotFoundError(YTObsidianError):
    """Required command (yt-dlp) not found."""
    pass


class ValidationError(YTObsidianError):
    """Input validation failed."""
    pass
