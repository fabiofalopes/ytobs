"""
Surgical Obsidian frontmatter editing primitives.

The #1 hazard when editing vault notes (~148 existing notes with rich
~20-key YAML frontmatter) is a full yaml round-trip: it reorders keys,
coerces date-like strings into datetime objects, and re-quotes values.
This module therefore performs *surgical line-level edits* as the primary
strategy — only the `key:` lines that must change are touched; every
other byte of the note is preserved verbatim.

A yaml round-trip fallback exists but is only used when the existing
frontmatter is malformed YAML (safe_load fails) and the edit cannot be
performed reliably line-based.

Atomic writes mirror cache_manager._atomic_write semantics (tempfile in
the SAME directory + os.replace, 3 retries with exponential backoff) —
proven against transient macOS/iCloud EPERM errors.

Pure stdlib + PyYAML. CRLF-free text assumed. No classes — plain functions.
"""

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from .exceptions import FileSystemError

# Frontmatter is only recognized when anchored at the very start of the
# file: `---\n...\n---\n`. Body horizontal rules (`---`) can never confuse
# this because (a) `^` anchors at string start (no re.MULTILINE) so the
# opening `---` must be the first line of the file, and (b) the non-greedy
# body stops at the FIRST closing `\n---\n`, which is by definition the
# end of the frontmatter block. Horizontal rules appearing later in the
# body are simply part of group(2).
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

_MAX_WRITE_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 0.2

_BACKUP_DIR = Path.home() / ".yt-obsidian" / "backups"

_RUN_KEY_ORDER = ("pattern", "models_used", "timestamp", "source")


def _render_scalar(value: str) -> str:
    """Render a string scalar as a single safe YAML value.

    Uses yaml's scalar dumper (NOT a document round-trip) so strings that
    would otherwise coerce (dates, bools, numbers) or contain special
    characters (": ", "#", leading/trailing spaces, backslashes) are
    correctly quoted. PyYAML's trailing document-end marker ("...") on
    plain scalar documents is stripped. Multi-line values fall back to a
    json.dumps double-quoted scalar (valid single-line YAML).
    """
    value = str(value)
    if "\n" in value:
        return json.dumps(value)
    lines = yaml.safe_dump(value, default_flow_style=False, allow_unicode=True).split(
        "\n"
    )
    while lines and lines[-1] in ("", "..."):
        lines.pop()
    return lines[0] if lines else "''"


def _force_quoted(value: str) -> str:
    """Render a string as a single-quoted YAML scalar, always quoted.

    Guarantees values like timestamps stay strings on re-parse (no date
    coercion). Single quotes inside are escaped by doubling.
    """
    return "'" + str(value).replace("'", "''") + "'"


def split_note(text: str) -> tuple[str, str]:
    """Split a note into (frontmatter_text, body).

    Frontmatter is only recognized when anchored at file start
    (regex ``^---\\n(...)\\n---\\n``). Body horizontal rules (``---``)
    never confuse the split — see the comment above
    ``_FRONTMATTER_RE``.

    Args:
        text: Full note content.

    Returns:
        Tuple of (frontmatter_text, body). Frontmatter text is the raw
        block BETWEEN the ``---`` delimiters (delimiters not included).
        If no frontmatter is present, returns ``("", text)``.
    """
    match = _FRONTMATTER_RE.match(text)
    if match:
        return match.group(1), match.group(2)
    return "", text


def _replace_key_line(fm_lines: list[str], key: str, rendered_value: str) -> bool:
    """Replace an existing top-level ``key:`` line in fm_lines, in place.

    Only a line whose *entire* leading token is exactly ``key`` at column 0
    matches (``^key:``), so ``status`` never matches ``upload_status:``
    and indented sub-keys are never touched.

    Returns:
        True if an existing line was replaced, False if the key was absent.
    """
    pattern = re.compile(r"^" + re.escape(key) + r":")
    for i, line in enumerate(fm_lines):
        if pattern.match(line):
            # Lambda replacement: value is inserted literally (backslashes,
            # $ signs etc. in values are never interpreted as regex escapes).
            fm_lines[i] = f"{key}: {rendered_value}"
            return True
    return False


def _find_list_end(fm_lines: list[str], key: str) -> Optional[int]:
    """Locate where a new list item should be inserted under ``key:``.

    The list under ``key:`` consists of ``- `` items at column 0; each
    item may span indented continuation lines (sub-keys, sub-lists like
    ``  models_used:`` / ``  - model``). The list ends at the next
    column-0 key (or EOF). Blank lines are treated as continuations.

    Returns:
        Index where a new ``- `` item should be inserted, or None if the
        key does not exist at all.
    """
    key_pattern = re.compile(r"^" + re.escape(key) + r":")
    for i, line in enumerate(fm_lines):
        if key_pattern.match(line):
            j = i + 1
            while j < len(fm_lines):
                nxt = fm_lines[j]
                if nxt.startswith("- "):
                    j += 1
                elif nxt == "" or nxt[:1] in (" ", "\t"):
                    j += 1
                else:
                    break
            return j
    return None


def _yaml_roundtrip_edit(
    fm_text: str,
    updates: dict[str, str],
    append_keys: list[str] | None,
) -> str:
    """Last-resort fallback: full yaml round-trip edit.

    Only invoked when the existing frontmatter is malformed YAML and a
    reliable surgical edit is impossible. Key order of whatever parses
    is preserved (safe_load keeps insertion order; dump with
    sort_keys=False).
    """
    try:
        fm_dict: dict[str, Any] = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm_dict = {}
    if not isinstance(fm_dict, dict):
        fm_dict = {}
    for key, value in updates.items():
        if append_keys and key in append_keys:
            existing = fm_dict.get(key, [])
            if not isinstance(existing, list):
                existing = [existing]
            if value not in existing:
                existing.append(value)
            fm_dict[key] = existing
        else:
            fm_dict[key] = value
    return yaml.safe_dump(
        fm_dict, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).rstrip("\n")


def update_frontmatter(
    text: str,
    updates: dict[str, str],
    append_keys: list[str] | None = None,
) -> str:
    """Surgically update scalar keys / append list items in a note's frontmatter.

    The PRIMARY strategy is line-level regex editing: an existing
    ``^key:`` line is replaced in place and everything else — key order,
    quoting style, comments, blank lines, the entire body — survives
    byte-identical. Missing keys are appended as hand-rendered
    ``key: value`` lines at the end of the frontmatter block.
    ``append_keys`` (list-type keys like ``fabric_patterns``) get their
    values appended as new YAML list items under the existing key (or the
    key + list created); exact duplicates are skipped.

    A full yaml round-trip is used ONLY as a fallback when the existing
    frontmatter is malformed YAML (unparseable → list extents can't be
    located safely).

    Args:
        text: Full note content (with or without frontmatter).
        updates: Mapping of key -> new scalar value (for ``append_keys``,
            key -> single new list item value).
        append_keys: Keys in ``updates`` that are list-type and should be
            appended to rather than overwritten.

    Returns:
        The updated full note content. If ``text`` had no frontmatter, a
        new ``---``-delimited block is created from ``updates``.
    """
    if not updates:
        return text

    append_keys = append_keys or []
    fm_text, body = split_note(text)

    if fm_text == "":
        lines: list[str] = []
        for key, value in updates.items():
            if key in append_keys:
                lines.append(f"{key}:")
                lines.append(f"- {_render_scalar(value)}")
            else:
                lines.append(f"{key}: {_render_scalar(value)}")
        new_fm = "\n".join(lines)
        return f"---\n{new_fm}\n---\n{body}"

    # Fall back to a round-trip only if the block is malformed YAML —
    # with unparseable content we cannot trust line-based list surgery.
    try:
        yaml.safe_load(fm_text)
    except yaml.YAMLError:
        new_fm = _yaml_roundtrip_edit(fm_text, updates, append_keys)
        return f"---\n{new_fm}\n---\n{body}"

    fm_lines = fm_text.split("\n")
    for key, value in updates.items():
        rendered = _render_scalar(value)
        if key in append_keys:
            insert_at = _find_list_end(fm_lines, key)
            if insert_at is None:
                fm_lines.append(f"{key}:")
                fm_lines.append(f"- {rendered}")
            else:
                item_line = f"- {rendered}"
                if item_line not in fm_lines:
                    fm_lines.insert(insert_at, item_line)
        else:
            if not _replace_key_line(fm_lines, key, rendered):
                fm_lines.append(f"{key}: {rendered}")

    new_fm = "\n".join(fm_lines)
    return f"---\n{new_fm}\n---\n{body}"


def _render_run(run: dict) -> list[str]:
    """Render one pattern-run record as YAML lines with fixed key order.

    Fixed order: pattern, models_used, timestamp, source.
    ``models_used`` renders as an indented sub-list; ``timestamp`` is
    ALWAYS a quoted string (never date-coerced on re-parse).
    """
    lines: list[str] = []
    for key in _RUN_KEY_ORDER:
        if key not in run:
            continue
        if key == "models_used":
            models = run[key] if isinstance(run[key], list) else [run[key]]
            lines.append("  models_used:")
            for model in models:
                lines.append(f"    - {_render_scalar(str(model))}")
        elif key == "timestamp":
            lines.append(f"  timestamp: {_force_quoted(str(run[key]))}")
        else:
            lines.append(f"  {key}: {_render_scalar(str(run[key]))}")
    # First line is the item opener ("- " instead of "  ").
    if lines:
        lines[0] = "- " + lines[0][2:]
    return lines


def merge_pattern_runs(fm_text: str, new_runs: list[dict]) -> str:
    """Append pattern-run records to a frontmatter block's ``pattern_runs:``.

    Line-based append: existing entries are preserved VERBATIM (no
    re-parse of existing lines). Each run is rendered with fixed key
    order (pattern, models_used, timestamp, source), ``models_used`` as a
    YAML sub-list, and timestamps as quoted strings.

    Args:
        fm_text: Raw frontmatter text (between the ``---`` delimiters).
        new_runs: List of run dicts; each may contain pattern (str),
            models_used (str | list[str]), timestamp (str), source (str).

    Returns:
        Updated frontmatter text (delimiters still not included).

    Raises:
        ValueError: If ``fm_text`` is non-empty and not valid YAML, or a
            run dict contains none of the known keys.
    """
    # Sanity check (does not rewrite anything): refuse to append into a
    # malformed block rather than risk corrupting the note.
    if fm_text.strip():
        try:
            parsed = yaml.safe_load(fm_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Frontmatter is not valid YAML: {e}") from e
        if parsed is not None and not isinstance(parsed, dict):
            raise ValueError("Frontmatter does not parse to a mapping")

    fm_lines = fm_text.split("\n") if fm_text else []

    rendered_runs: list[list[str]] = []
    for run in new_runs:
        if not any(key in run for key in _RUN_KEY_ORDER):
            raise ValueError(f"Run dict has no known keys: {run!r}")
        rendered_runs.append(_render_run(run))

    insert_at = _find_list_end(fm_lines, "pattern_runs")
    if insert_at is None:
        fm_lines.append("pattern_runs:")
        insert_at = len(fm_lines)

    for run_lines in rendered_runs:
        for line in run_lines:
            fm_lines.insert(insert_at, line)
            insert_at += 1

    return "\n".join(fm_lines)


def atomic_write_note(path: Path | str, content: str, backup: bool = False) -> None:
    """Atomically write a note, mirroring cache_manager._atomic_write.

    Tempfile is created in the SAME directory as the target, then
    ``os.replace``d into place (atomic on POSIX). Transient filesystem
    errors (macOS/iCloud EPERM) are retried up to 3 times with
    exponential backoff (0.2s, 0.4s, 0.8s).

    Args:
        path: Target note path (str or Path; ``~`` expanded).
        content: Full note content to write (UTF-8).
        backup: If True and the file already exists, first copy the prior
            content to ``~/.yt-obsidian/backups/<unix_ts>_<filename>``.

    Raises:
        FileSystemError: If the parent directory can't be created, the
            backup can't be written, or all write retries fail.
    """
    path = Path(path).expanduser()
    parent = path.parent

    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise FileSystemError(f"Cannot create directory {parent}: {e}") from e

    if backup:
        try:
            prior = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            prior = None
        except OSError as e:
            raise FileSystemError(f"Cannot read note for backup {path}: {e}") from e
        if prior is not None:
            try:
                _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                ts = int(time.time())
                backup_path = _BACKUP_DIR / f"{ts}_{path.name}"
                backup_path.write_text(prior, encoding="utf-8")
            except OSError as e:
                raise FileSystemError(f"Cannot write backup for {path}: {e}") from e

    last_error: Exception | None = None
    for attempt in range(_MAX_WRITE_RETRIES):
        tmp_path: Optional[str] = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(parent),
                prefix=f".{path.name}.tmp.",
                suffix=".tmp",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            os.replace(tmp_path, str(path))
            return

        except (OSError, PermissionError) as e:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            last_error = e
            if attempt < _MAX_WRITE_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (2**attempt))
                continue
            break

    raise FileSystemError(
        f"Cannot write note {path} after {_MAX_WRITE_RETRIES} attempts: {last_error}"
    )
