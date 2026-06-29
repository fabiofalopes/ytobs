"""
Cache management for video processing state

Provides intelligent caching to:
- Prevent duplicate processing of the same video
- Enable incremental pattern additions
- Track processing history and token usage

All file operations are resilient to transient filesystem errors
(macOS/iCloud EPERM, concurrent access) — cache failures never
crash the tool; they degrade gracefully with warnings.
"""

from pathlib import Path
import json
import os
import tempfile
import time
import shutil
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict


_MAX_WRITE_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 0.2


def _atomic_write(path: Path, data: str) -> bool:
    """Write data to path atomically via temp file + rename.

    Handles transient macOS/iCloud EPERM errors with retries.
    Returns True on success, False on failure (caller handles).
    """
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    for attempt in range(_MAX_WRITE_RETRIES):
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(parent),
                prefix=f".{path.name}.tmp.",
                suffix=".tmp",
            )
            with os.fdopen(fd, "w") as f:
                f.write(data)

            os.replace(tmp_path, str(path))
            return True

        except (OSError, PermissionError) as e:
            try:
                locals().get("tmp_path") and os.unlink(locals()["tmp_path"])
            except Exception:
                pass

            if attempt < _MAX_WRITE_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (2**attempt))
                continue

            print(f"  ⚠️  Cache write failed ({path.name}): {e}")
            return False

        except Exception as e:
            try:
                locals().get("tmp_path") and os.unlink(locals()["tmp_path"])
            except Exception:
                pass
            print(f"  ⚠️  Cache write error ({path.name}): {e}")
            return False

    return False


def _atomic_read(path: Path) -> Optional[str]:
    """Read file contents with transient error handling.

    Returns file content string, or None on failure.
    """
    for attempt in range(_MAX_WRITE_RETRIES):
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, PermissionError) as e:
            if attempt < _MAX_WRITE_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (2**attempt))
                continue
            return None
        except Exception:
            return None
    return None


@dataclass
class ProcessingEvent:
    """Single processing event in history"""

    timestamp: str
    mode: str
    patterns_run: List[str]
    chunks_created: int
    api_calls: int
    tokens_used: int
    processing_time_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class CacheEntry:
    """Complete cache entry for a video"""

    video_id: str
    video_url: str
    title: str
    upload_date: str
    duration_seconds: int
    transcript_word_count: int
    markdown_path: str
    last_updated: str
    patterns_run: List[str]
    processing_history: List[Dict[str, Any]]
    chunks: Optional[List[Dict[str, Any]]] = None
    phase1_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create CacheEntry from dict, with graceful field handling."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {
            k: v
            for k, v in data.items()
            if k in {f.name for f in cls.__dataclass_fields__.values()}
        }
        for field in cls.__dataclass_fields__.values():
            if field.name not in filtered:
                if field.default is not None:
                    filtered[field.name] = field.default
                elif field.default_factory is not None:
                    filtered[field.name] = field.default_factory()
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return asdict(self)


class CacheManager:
    """Manages video processing cache with resilience to filesystem errors."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache files.
                       Defaults to ~/.yt-obsidian/cache/ to avoid iCloud issues.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".yt-obsidian" / "cache"
        self.cache_dir = Path(cache_dir).expanduser()
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.index_file = self.cache_dir / "index.json"
        self._load_index()

    def exists(self, video_id: str) -> bool:
        """Check if video already processed."""
        return video_id in self.index.get("videos", {})

    def get_cache(self, video_id: str) -> Optional[CacheEntry]:
        """Load cache entry for video."""
        if not self.exists(video_id):
            return None

        cache_file = self.cache_dir / f"{video_id}.json"
        try:
            raw = _atomic_read(cache_file)
            if raw is None:
                print(f"  ⚠️  Failed to read cache for {video_id}, will re-process")
                self.invalidate(video_id)
                return None
            data = json.loads(raw)
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  ⚠️  Corrupt cache for {video_id}: {e}")
            self.invalidate(video_id)
            return None

    def save_cache(self, video_id: str, entry: CacheEntry) -> bool:
        """Save cache entry. Returns True on success, never crashes."""
        cache_file = self.cache_dir / f"{video_id}.json"

        ok = _atomic_write(cache_file, json.dumps(entry.to_dict(), indent=2))
        if not ok:
            print(
                f"  ⚠️  Could not save cache for {video_id}, will re-process next time"
            )
            return False

        if "videos" not in self.index:
            self.index["videos"] = {}
        self.index["videos"][video_id] = {
            "title": entry.title,
            "markdown_path": entry.markdown_path,
            "last_processed": entry.last_updated,
            "patterns_count": len(entry.patterns_run),
        }

        self._save_index()
        return True

    def get_note_path(self, video_id: str) -> Optional[str]:
        """Get markdown note path for video."""
        cache = self.get_cache(video_id)
        return cache.markdown_path if cache else None

    def get_patterns_run(self, video_id: str) -> List[str]:
        """Get patterns already run on video."""
        cache = self.get_cache(video_id)
        return cache.patterns_run if cache else []

    def append_patterns(self, video_id: str, new_patterns: List[str]) -> bool:
        """Append new patterns to cache. Returns True on success."""
        cache = self.get_cache(video_id)
        if not cache:
            return False

        cache.patterns_run.extend(new_patterns)
        cache.last_updated = datetime.now().isoformat()
        cache.processing_history.append(
            {
                "timestamp": cache.last_updated,
                "mode": "append",
                "patterns_appended": new_patterns,
                "success": True,
            }
        )

        return self.save_cache(video_id, cache)

    def invalidate(self, video_id: str) -> None:
        """Delete cache for video."""
        cache_file = self.cache_dir / f"{video_id}.json"
        try:
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            pass

        if video_id in self.index.get("videos", {}):
            del self.index["videos"][video_id]
            self._save_index()

    def list_all(self) -> List[Dict[str, Any]]:
        """List all cached videos."""
        return list(self.index.get("videos", {}).items())

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_videos = len(self.index.get("videos", {}))
        total_patterns = 0
        total_tokens = 0

        for video_id in self.index.get("videos", {}).keys():
            cache = self.get_cache(video_id)
            if cache:
                total_patterns += len(cache.patterns_run)
                for event in cache.processing_history:
                    total_tokens += event.get("tokens_used", 0)

        return {
            "total_videos": total_videos,
            "total_patterns": total_patterns,
            "total_tokens_used": total_tokens,
            "cache_directory": str(self.cache_dir),
        }

    def _load_index(self) -> None:
        """Load index file, rebuilding if corrupt."""
        raw = _atomic_read(self.index_file)
        if raw is None:
            self._create_new_index()
            return

        try:
            self.index = json.loads(raw)
            # Validate structure
            if not isinstance(self.index, dict) or "videos" not in self.index:
                print(f"  ⚠️  Corrupt cache index, creating new one")
                self._create_new_index()
        except (json.JSONDecodeError, Exception):
            print(f"  ⚠️  Corrupt cache index, creating new one")
            self._create_new_index()

    def _create_new_index(self) -> None:
        """Create new index and persist to disk."""
        self.index = {
            "version": "3.0",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "videos": {},
        }
        self._save_index()

    def _save_index(self) -> bool:
        """Save index file atomically. Returns True on success."""
        self.index["last_updated"] = datetime.now().isoformat()
        return _atomic_write(self.index_file, json.dumps(self.index, indent=2))
