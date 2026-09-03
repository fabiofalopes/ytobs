"""
Duplicate note detection and marking for ``ytobs dedupe``.

Vault policy (AGENTS.md): agents must NEVER delete or move notes without
human approval. This module therefore only MARKS duplicates in place:

* frontmatter: ``status: duplicate`` + ``duplicate_of: <canonical stem>``
* body: a ``> [!warning] Duplicate of [[<canonical stem>]]`` callout
  inserted directly under the ``# `` title line.

All edits go through ``frontmatter_editor`` (surgical line-level updates
+ atomic writes with backup), so every other byte of a marked note —
frontmatter key order, quoting, body content — survives verbatim.

Canonical-note selection (locked user decision, 2026-09-03), in order:
1. Count of FILLED ``## AI Analysis`` subsections (desc)
2. Frontmatter ``transcript_word_count`` (desc)
3. File mtime (newest first)
4. Filename WITHOUT a `` (n)`` collision suffix preferred over suffixed

The command is idempotent: re-running ``--apply`` never re-writes a note
that is already correctly marked and never stacks a second callout.

Pure stdlib + PyYAML. No network, no fabric calls. No bare excepts.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import Config, resolve_output_dir
from .exceptions import FileSystemError
from .frontmatter_editor import atomic_write_note, split_note, update_frontmatter

# Sentinel key under which group_by_video_id parks notes that have no
# video_id in their frontmatter. The characters "<" and ">" can never
# appear in a real 11-char YouTube video_id, so it cannot collide.
NO_VIDEO_ID_KEY = "<no-video-id>"

# ``## AI Analysis`` heading — same tolerant shape as incremental_writer.
_AI_ANALYSIS_HEADING_RE = re.compile(r"^## AI Analysis[ \t]*$", re.MULTILINE)
# A section boundary is the next column-0 H2 heading or horizontal rule
# (formatter output separates sections with ``---`` rules).
_SECTION_BOUNDARY_RE = re.compile(r"^(?:## .+|---)[ \t]*$", re.MULTILINE)
# Filename collision suffix produced by filesystem.resolve_collision,
# e.g. ``some note (2).md``.
_COLLISION_SUFFIX_RE = re.compile(r" \(\d+\)$")

_STATUS_MARKED = "duplicate"


# ---------------------------------------------------------------------------
# Note scanning / grouping
# ---------------------------------------------------------------------------


def count_filled_sections(body: str) -> int:
    """Count FILLED subsections under ``## AI Analysis`` in a note body.

    Mirrors the filled/empty classification the retro pass uses: locate
    the ``## AI Analysis`` H2, take content up to the next column-0 H2
    heading or ``---`` rule, split on ``### `` subsection headings; a
    subsection is FILLED when it has non-whitespace content after its
    heading line. Returns 0 when the section (or any subsection content)
    is absent.
    """
    match = _AI_ANALYSIS_HEADING_RE.search(body)
    if not match:
        return 0

    tail = body[match.end() :]
    boundary = _SECTION_BOUNDARY_RE.search(tail)
    section = tail[: boundary.start()] if boundary else tail

    filled = 0
    for part in section.split("### ")[1:]:
        lines = part.splitlines()
        # lines[0] is the subsection heading text itself — content is
        # whatever follows it.
        content = "\n".join(lines[1:])
        if content.strip():
            filled += 1
    return filled


def _to_int(value: Any) -> int:
    """Coerce a frontmatter scalar to int, tolerating junk (never raises)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_note(path: Path) -> dict[str, Any] | None:
    """Read and parse one note into the dict shape used throughout.

    Returns None (after warning) if the file cannot be read. Frontmatter
    that fails to parse is treated as empty — the note is still listed,
    just with no video_id (it can never win canonical selection on
    criteria 1-2 and is reported for manual inspection).
    """
    try:
        content = path.read_text(encoding="utf-8")
        mtime = path.stat().st_mtime
    except OSError as e:
        print(f"⚠️  Skipping unreadable note {path.name}: {e}", file=sys.stderr)
        return None

    fm_text, body = split_note(content)
    fm: dict[str, Any] = {}
    if fm_text.strip():
        try:
            parsed = yaml.safe_load(fm_text)
            if isinstance(parsed, dict):
                fm = parsed
        except yaml.YAMLError as e:
            print(f"⚠️  Unparseable frontmatter in {path.name}: {e}", file=sys.stderr)

    return {
        "path": path,
        "stem": path.stem,
        "filename": path.name,
        "content": content,
        "frontmatter": fm,
        "body": body,
        "video_id": fm.get("video_id") if isinstance(fm.get("video_id"), str) else None,
        "status": fm.get("status"),
        "duplicate_of": fm.get("duplicate_of"),
        "word_count": _to_int(fm.get("transcript_word_count")),
        "mtime": mtime,
        "filled_sections": count_filled_sections(body),
    }


def group_by_video_id(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Group all notes in the vault youtube dir by their video_id.

    Globs ``*.md`` via pathlib (the vault path contains spaces). Notes
    whose frontmatter has no ``video_id`` land under the
    :data:`NO_VIDEO_ID_KEY` sentinel key — listed, never grouped. Notes
    already ``status: duplicate`` are still grouped and listed; marking
    logic treats them as "already marked" (idempotency).

    Returns:
        Mapping video_id -> list of note dicts (each group sorted by
        filename for deterministic output). Groups of size 1 are
        included here — the caller decides they are not duplicate work.
    """
    notes: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*.md")):
        note = _load_note(path)
        if note is not None:
            notes.append(note)

    groups: dict[str, list[dict[str, Any]]] = {}
    for note in notes:
        key = note["video_id"] if note["video_id"] else NO_VIDEO_ID_KEY
        groups.setdefault(key, []).append(note)

    for group in groups.values():
        group.sort(key=lambda n: n["filename"])
    return groups


# ---------------------------------------------------------------------------
# Canonical selection
# ---------------------------------------------------------------------------


def _sort_key(note: dict[str, Any]) -> tuple:
    """Total-order key implementing the locked canonical precedence."""
    return (
        -note["filled_sections"],  # 1) filled AI Analysis subsections
        -note["word_count"],  # 2) transcript_word_count
        -note["mtime"],  # 3) newest mtime
        # 4) suffixless filename preferred over " (n)" collision copies
        1 if _COLLISION_SUFFIX_RE.search(note["stem"]) else 0,
        note["stem"],  # deterministic final tiebreak
    )


def pick_canonical(notes: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list]:
    """Pick the canonical note for one video_id group.

    Notes already marked ``status: duplicate`` are NEVER canonical
    candidates: marking updates a note's mtime, so a just-marked dupe
    would otherwise look "newest" on the next run and flip the canonical
    choice (breaking idempotency with a duplicate_of cycle). When every
    note in the group is already marked, returns ``(None, notes)`` —
    nothing new to canonicalize.

    Returns:
        (canonical_note_or_None, remaining_notes) — remaining keeps the
        input order minus the canonical entry.
    """
    candidates = [n for n in notes if n["status"] != _STATUS_MARKED]
    if not candidates:
        return None, notes
    canonical = sorted(candidates, key=_sort_key)[0]
    rest = [n for n in notes if n is not canonical]
    return canonical, rest


def _canonical_reason(notes: list[dict[str, Any]], canonical: dict[str, Any]) -> str:
    """Human-readable reason string: full stats + the deciding criterion.

    A criterion "decided" only when the canonical strictly beats every
    other note on it (ties fall through to the next criterion).
    """
    others = [n for n in notes if n is not canonical]

    def _max_or(field: str, default: float) -> float:
        return max((n[field] for n in others), default=default)

    if canonical["filled_sections"] > _max_or("filled_sections", -1):
        decided = "filled AI sections"
    elif canonical["word_count"] > _max_or("word_count", -1):
        decided = "transcript_word_count"
    elif canonical["mtime"] > _max_or("mtime", -1.0):
        decided = "newest mtime"
    else:
        decided = "suffixless filename (tiebreak)"

    mtime_str = datetime.fromtimestamp(canonical["mtime"]).strftime("%Y-%m-%d")
    return (
        f"decided by {decided} · filled_sections={canonical['filled_sections']}"
        f" · transcript_word_count={canonical['word_count']} · mtime={mtime_str}"
    )


# ---------------------------------------------------------------------------
# Marking
# ---------------------------------------------------------------------------


def _insert_callout(body: str, canonical_stem: str) -> str:
    """Insert the duplicate callout directly under the ``# `` title line.

    Idempotent: if an identical callout line is already present anywhere
    in the body, the body is returned unchanged.
    """
    callout = f"> [!warning] Duplicate of [[{canonical_stem}]]"
    if any(line.strip() == callout for line in body.split("\n")):
        return body

    lines = body.split("\n")
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            break

    if insert_at < len(lines) and lines[insert_at].strip() == "":
        # Blank line already follows the title — it doubles as the
        # callout's trailing blank; insert the callout above it only.
        lines.insert(insert_at, callout)
    else:
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, callout)
        lines.insert(insert_at + 2, "")
    return "\n".join(lines)


def mark_duplicate(dup: dict[str, Any], canonical: dict[str, Any]) -> None:
    """Mark one note as a duplicate of the canonical note (in place).

    Surgical edits only, via ``frontmatter_editor``:

    * ``status: duplicate`` and ``duplicate_of: <canonical stem>`` (the
      filename stem WITHOUT ``.md``, no brackets) in the frontmatter;
    * ``> [!warning] Duplicate of [[<canonical stem>]]`` callout with a
      trailing blank line directly under the ``# `` title line.

    Written atomically with a timestamped backup. Never touches the
    canonical note, never deletes or moves anything.
    """
    canonical_stem = canonical["path"].stem

    try:
        content = dup["path"].read_text(encoding="utf-8")
    except OSError as e:
        raise FileSystemError(f"Cannot read note {dup['path']}: {e}") from e

    updated = update_frontmatter(
        content, {"status": _STATUS_MARKED, "duplicate_of": canonical_stem}
    )
    fm_text, body = split_note(updated)
    body = _insert_callout(body, canonical_stem)
    updated = f"---\n{fm_text}\n---\n{body}"

    atomic_write_note(dup["path"], updated, backup=True)


def _is_marked(note: dict[str, Any], canonical_stem: str) -> bool:
    """True when a note is already marked duplicate OF this canonical."""
    return note["status"] == _STATUS_MARKED and note["duplicate_of"] == canonical_stem


# ---------------------------------------------------------------------------
# Command entry point (contract: ytobs.cli handle_dedupe_command)
# ---------------------------------------------------------------------------


def run_dedupe(args: Any, config: Config) -> int:
    """``ytobs dedupe`` — detect duplicate notes per video_id and MARK them.

    Dry-run by default (``--apply`` writes). ``--limit N`` caps the
    number of duplicate GROUPS processed per run (largest first).

    Returns:
        0 on success (including dry-run and nothing-to-do-with-apply),
        1 on error, 2 when no duplicate groups were found.
    """
    apply = bool(getattr(args, "apply", False))
    limit = getattr(args, "limit", None)

    try:
        output_dir = resolve_output_dir(config)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    print(f"🔍 Scanning {output_dir} ...")
    try:
        groups = group_by_video_id(output_dir)
    except OSError as e:
        print(f"❌ Cannot scan {output_dir}: {e}", file=sys.stderr)
        return 1

    no_video_notes = groups.pop(NO_VIDEO_ID_KEY, [])
    dup_groups = {vid: notes for vid, notes in groups.items() if len(notes) > 1}
    single_count = len(groups) - len(dup_groups)

    if not dup_groups:
        print("✅ No duplicate groups found.")
        print(
            f"   {single_count} unique-video notes · "
            f"{len(no_video_notes)} notes without video_id"
        )
        return 2

    ordered = sorted(dup_groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if limit is not None:
        ordered = ordered[: max(0, limit)]

    print(
        f"   {len(dup_groups)} duplicate groups · {single_count} single-note"
        f" groups · {len(no_video_notes)} notes without video_id\n"
    )

    marked_count = 0
    already_count = 0
    error_count = 0

    for video_id, notes in ordered:
        canonical, dupes = pick_canonical(notes)

        if canonical is None:
            already_count += len(notes)
            print(
                f"▶ {video_id[:8]}  ×{len(notes)}  — all already marked, nothing to do"
            )
            for note in notes:
                print(f"      - {note['filename']}  [already marked]")
            print()
            continue

        reason = _canonical_reason(notes, canonical)
        canonical_stem = canonical["path"].stem

        print(f"▶ {video_id[:8]}  ×{len(notes)}")
        print(f"    canonical : {canonical['filename']}")
        print(f"    reason    : {reason}")
        for dup in dupes:
            if _is_marked(dup, canonical_stem):
                already_count += 1
                print(f"      - {dup['filename']}  [already marked]")
            elif apply:
                try:
                    mark_duplicate(dup, canonical)
                    marked_count += 1
                    print(f"      - {dup['filename']}  [marked]")
                except (FileSystemError, OSError) as e:
                    error_count += 1
                    print(f"      - {dup['filename']}  [ERROR: {e}]", file=sys.stderr)
            else:
                print(f"      - {dup['filename']}  [would mark]")
        print()

    if not apply:
        print("DRY RUN — no files written. Re-run with --apply to mark duplicates.")
        return 0

    if no_video_notes:
        print("ℹ️  Notes without video_id (never grouped, listed only):")
        for note in no_video_notes:
            print(f"      - {note['filename']}")
        print()

    print("📊 Summary:")
    print(f"   Groups processed : {len(ordered)}")
    print(f"   Notes marked     : {marked_count}")
    print(f"   Already marked   : {already_count}")
    print(f"   No video_id      : {len(no_video_notes)}")
    print(f"   Errors           : {error_count}")

    return 1 if error_count else 0
