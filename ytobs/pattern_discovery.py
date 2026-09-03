"""
Pattern discovery for the ``ytobs patterns`` command family.

Enumerates fabric patterns WITHOUT running any AI calls:

* ``fabric -l`` — primary source (authoritative; includes custom patterns
  discovered via ``CUSTOM_PATTERNS_DIRECTORY``)
* filesystem scan fallback — ``~/.config/fabric/patterns/`` plus the custom
  patterns directory parsed from ``~/.config/fabric/.env`` — used when the
  fabric CLI is missing or fails

Actions:
  ytobs patterns                              list all patterns
  ytobs patterns search QUERY                 case-insensitive substring filter
  ytobs patterns describe NAME                pattern path + description
  ytobs patterns suggest --content-type TYPE  static recommendations, filtered
                                              to patterns that actually exist

Pure stdlib + subprocess. No network, no fabric pattern execution, no bare
excepts. Description extraction never raises: malformed system.md yields an
empty description string.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

PATTERNS_DIR = Path.home() / ".config" / "fabric" / "patterns"
FABRIC_ENV = Path.home() / ".config" / "fabric" / ".env"

CONTENT_TYPE_SUGGESTIONS: Dict[str, List[str]] = {
    "video": [
        "extract_wisdom",
        "summarize",
        "extract_ideas",
        "extract_insights",
        "create_summary",
    ],
    "podcast": [
        "extract_wisdom",
        "summarize",
        "extract_questions",
        "extract_ideas",
        "create_show_notes",
    ],
    "tutorial": [
        "extract_wisdom",
        "summarize",
        "extract_steps",
        "extract_recommendations",
        "create_reading_plan",
    ],
    "talk": [
        "extract_wisdom",
        "summarize",
        "extract_insights",
        "extract_core_message",
        "create_sigma_hq_presentation",
    ],
    "interview": [
        "extract_wisdom",
        "summarize",
        "extract_questions",
        "extract_insights",
        "create_ask_the_expert_answers",
    ],
    "news": [
        "summarize",
        "extract_wisdom",
        "analyze_tariffs",
        "analyze_military_intelligence",
        "analyze_paper",
    ],
}


def _custom_patterns_dir() -> Optional[Path]:
    """Return the custom patterns directory from ``~/.config/fabric/.env``.

    Returns None when the env file or the variable is missing. Supports
    ``~`` and ``$HOME`` expansion so both spellings resolve.
    """
    try:
        if not FABRIC_ENV.is_file():
            return None
        for line in FABRIC_ENV.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            line = line.strip()
            if line.startswith("CUSTOM_PATTERNS_DIRECTORY="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                if not raw:
                    return None
                expanded = os.path.expanduser(os.path.expandvars(raw))
                return Path(expanded)
    except OSError:
        return None
    return None


def _patterns_from_filesystem() -> List[str]:
    """Enumerate patterns by scanning the fabric patterns directories.

    A pattern is any subdirectory containing a ``system.md`` file.
    """
    names: List[str] = []
    roots = [PATTERNS_DIR]
    custom = _custom_patterns_dir()
    if custom is not None:
        roots.append(custom)
    for root in roots:
        try:
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and (entry / "system.md").is_file():
                    if entry.name not in names:
                        names.append(entry.name)
        except OSError:
            continue
    return sorted(names)


def list_patterns() -> List[str]:
    """Return all available fabric pattern names.

    Tries ``fabric -l`` first (one name per line); falls back to a
    filesystem scan when the CLI is unavailable or fails.
    """
    try:
        result = subprocess.run(
            ["fabric", "-l"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            names = [line.strip() for line in result.stdout.splitlines()]
            names = [n for n in names if n and not n.startswith("Available")]
            if names:
                return sorted(names)
    except (OSError, subprocess.SubprocessError):
        pass
    return _patterns_from_filesystem()


def search_patterns(query: str, patterns: Optional[List[str]] = None) -> List[str]:
    """Return patterns whose names contain ``query`` (case-insensitive)."""
    source = patterns if patterns is not None else list_patterns()
    needle = query.lower()
    return [name for name in source if needle in name.lower()]


def describe_pattern(name: str) -> Optional[Dict[str, str]]:
    """Describe a pattern: its on-disk path and a short description.

    The description is the ``description:`` line from the pattern's YAML
    frontmatter when present, otherwise the first non-heading paragraph of
    ``system.md``, truncated to ~200 characters. Returns None when the
    pattern cannot be found on disk.
    """
    candidates = [PATTERNS_DIR / name]
    custom = _custom_patterns_dir()
    if custom is not None:
        candidates.append(custom / name)
    system_md = next(
        (p / "system.md" for p in candidates if (p / "system.md").is_file()), None
    )
    if system_md is None:
        return None
    return {
        "name": name,
        "path": str(system_md.parent),
        "description": _extract_description(system_md),
    }


def _extract_description(system_md: Path) -> str:
    """Extract a short description from a pattern's ``system.md``.

    Preference order: YAML frontmatter ``description:`` value, then the
    first non-heading paragraph. Never raises; malformed files yield "".
    """
    try:
        text = system_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if text.startswith("---"):
        match = re.search(r"^description:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()[:200]
    for block in text.split("\n\n"):
        stripped = block.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        flat = " ".join(stripped.split())
        return flat[:200]
    return ""


def suggest_patterns(
    content_type: str, patterns: Optional[List[str]] = None
) -> List[str]:
    """Return recommended patterns for ``content_type`` that actually exist.

    Unknown content types raise ValueError; the CLI validates against the
    same table keys before calling.
    """
    if content_type not in CONTENT_TYPE_SUGGESTIONS:
        raise ValueError(
            f"unknown content type: {content_type!r} "
            f"(choose from {', '.join(sorted(CONTENT_TYPE_SUGGESTIONS))})"
        )
    source = patterns if patterns is not None else list_patterns()
    available = set(source)
    return [p for p in CONTENT_TYPE_SUGGESTIONS[content_type] if p in available]


def run_patterns(args, config) -> int:  # noqa: ARG001 (config kept for symmetry)
    """Entry point for the ``ytobs patterns`` command family."""
    action = getattr(args, "action", "list") or "list"
    query = getattr(args, "query", None)
    content_type = getattr(args, "content_type", None) or query

    if action == "list":
        patterns = list_patterns()
        if not patterns:
            print(
                "ytobs patterns: no patterns found (fabric CLI missing and "
                "no patterns directory present)",
                file=sys.stderr,
            )
            return 1
        print(f"📋 {len(patterns)} fabric patterns available:\n")
        for name in patterns:
            print(name)
        return 0

    if action == "search":
        if not query:
            print("ytobs patterns search: missing QUERY argument", file=sys.stderr)
            return 1
        patterns = list_patterns()
        matches = search_patterns(query, patterns)
        if not matches:
            print(f"No patterns matching {query!r}")
            return 0
        print(f"🔍 {len(matches)} pattern(s) matching {query!r}:\n")
        for name in matches:
            print(name)
        return 0

    if action == "describe":
        if not query:
            print("ytobs patterns describe: missing NAME argument", file=sys.stderr)
            return 1
        info = describe_pattern(query)
        if info is None:
            print(
                f"ytobs patterns describe: pattern {query!r} not found on disk",
                file=sys.stderr,
            )
            return 1
        print(f"Pattern:  {info['name']}")
        print(f"Path:     {info['path']}")
        print(f"Description: {info['description'] or '(none)'}")
        return 0

    if action == "suggest":
        if not content_type:
            print("ytobs patterns suggest: missing --content-type", file=sys.stderr)
            return 1
        try:
            suggestions = suggest_patterns(content_type)
        except ValueError as exc:
            print(f"ytobs patterns suggest: {exc}", file=sys.stderr)
            return 1
        if not suggestions:
            print(f"No recommended patterns for {content_type!r} are installed")
            return 0
        print(f"💡 Recommended patterns for {content_type!r}:\n")
        for name in suggestions:
            print(name)
        return 0

    print(f"ytobs patterns: unknown action {action!r}", file=sys.stderr)
    return 1
