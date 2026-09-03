"""Retroactive pattern backfill on existing vault notes (`ytobs retro`).

Scans the vault ($OBSVAULT/youtube — resolved exactly like every other
ytobs code path via config.resolve_output_dir) for notes whose `## AI
Analysis` sections are missing or empty (the residue of failed fabric
runs), re-runs the selected fabric patterns on the note's stored
transcript, and patches the note IN PLACE:

- empty/missing `### {Pattern}` sections get the fresh output + a model
  provenance line (formatter.format_pattern_meta_line);
- the raw `## Transcript` is fenced in place (formatter.fence_for) —
  content bytes are never touched, only wrapped;
- a `## Refined Transcript` section is added (fenced, regex-only
  backend) only when refinement actually changed the text;
- frontmatter: status raw/draft -> analyzed, `pattern_runs:` records
  appended (source: "retro"), `fabric_patterns:` appended (deduped);
- the per-video JSON cache is created/merged (processing_history
  preserved).

Everything is surgical (frontmatter_editor line-based edits +
line-based body splices): the rich ~20-key frontmatter and all other
body bytes survive verbatim. Files are NEVER created, renamed, or
deleted — only atomic_write_note(path, ..., backup=True) overwrites.

The fabric call goes through the module-level FabricOrchestrator import
so tests can monkeypatch ytobs.retro.FabricOrchestrator; same for
CacheManager.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import yaml

from .cache_manager import CacheEntry, CacheManager
from .config import Config, get_cache_dir, resolve_model, resolve_output_dir
from .fabric_orchestrator import FabricOrchestrator
from .formatter import fence_for, format_pattern_meta_line
from .frontmatter_editor import (
    atomic_write_note,
    merge_pattern_runs,
    split_note,
    update_frontmatter,
)
from .incremental_writer import _insert_into_ai_analysis
from .transcript_refiner import refine_transcript

# --- module-level regexes (mirror incremental_writer's shapes) -------------

# `^## Transcript\s*$` per spec (\s* tolerated trailing whitespace)
_TRANSCRIPT_HEADING_RE = re.compile(r"^## Transcript[ \t]*$")
_AI_ANALYSIS_HEADING_RE = re.compile(r"^## AI Analysis[ \t]*$")
_H2_RE = re.compile(r"^## ")
_SUBSECTION_HEADING_RE = re.compile(r"^### (.+?)[ \t]*$")
_RULE_RE = re.compile(r"^---[ \t]*$")
# Section boundary: next column-0 H2 heading or `---` rule (formatter
# output separates `## ` sections with rules).
_SECTION_BOUNDARY_RE = re.compile(r"^(?:## .+|---)[ \t]*$")

_FENCE_LINE_RE = re.compile(r"^`{3,}[ \t]*$")

# Section content that is nothing but whitespace and/or HTML comments
# (covers both `<!-- Transcript not available ... -->` and the legacy
# `<!-- Phase 2: Transcript will be inserted here -->` placeholder).
_COMMENT_ONLY_RE = re.compile(r"^(?:\s|<!--.*?-->)*$", re.DOTALL)

_DEFAULT_SCAN_PATTERNS = ("extract_wisdom", "summarize")

ExitCode = int


# ---------------------------------------------------------------------------
# Parsing / classification helpers
# ---------------------------------------------------------------------------


def _display_name(pattern: str) -> str:
    """Map a fabric pattern id to its note heading display name."""
    return pattern.replace("_", " ").title()


def _parse_frontmatter(fm_text: str) -> dict[str, Any]:
    """Safely parse frontmatter text; returns {} on malformed YAML."""
    try:
        parsed = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _strip_trailing_separator(lines: list[str]) -> tuple[list[str], bool]:
    """Drop a trailing section-boundary `---` rule (with blank padding).

    Formatter output separates `## ` sections with a column-0 `---`
    rule; slicing a section up to the next `^## ` heading therefore
    includes that rule. Returns (section_lines_without_rule, had_rule).
    """
    work = list(lines)
    while work and work[-1].strip() == "":
        work.pop()
    if work and _RULE_RE.match(work[-1]):
        work.pop()
        return work, True
    return work, False


def extract_transcript_from_body(body: str) -> Optional[str]:
    """Extract the raw transcript text from a note body.

    Slices from a `^## Transcript\\s*$` heading to the next `^## `
    heading, strips the trailing `---` separator rule, handles both
    unfenced (old notes) and fenced (new notes) storage — fence lines
    are stripped, content preserved — and returns None for empty
    sections or HTML-comment-only placeholders.
    """
    m = re.search(r"^## Transcript[ \t]*$", body, re.MULTILINE)
    if m is None:
        return None
    rest = body[m.end() :]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    section = rest[: nxt.start()] if nxt else rest

    lines, _ = _strip_trailing_separator(section.split("\n"))
    text = "\n".join(lines).strip()
    if not text:
        return None

    # Fenced transcripts: drop the opening fence line (```, ```text,
    # longer runs) and the matching closing fence line.
    if text.startswith("```"):
        fence_lines = text.split("\n")
        fence_lines = fence_lines[1:]
        while fence_lines and _FENCE_LINE_RE.match(fence_lines[-1]):
            fence_lines.pop()
        text = "\n".join(fence_lines).strip()

    if not text or _COMMENT_ONLY_RE.match(text):
        return None
    return text


def _classify_ai_analysis(body: str) -> tuple[str, list[tuple[str, bool]]]:
    """Classify the note's `## AI Analysis` section.

    Returns (state, subsections) where subsections is a list of
    (display_name, filled) in document order and state is one of
    "absent" | "all_empty" | "mixed" | "full".
    """
    lines = body.split("\n")
    n = len(lines)
    start = next(
        (i for i, line in enumerate(lines) if _AI_ANALYSIS_HEADING_RE.match(line)),
        None,
    )
    if start is None:
        return "absent", []

    subsections: list[tuple[str, bool]] = []
    i = start + 1
    while i < n:
        line = lines[i]
        if _H2_RE.match(line):
            break
        m = _SUBSECTION_HEADING_RE.match(line)
        if m:
            j = i + 1
            while j < n and not (
                _SUBSECTION_HEADING_RE.match(lines[j])
                or _H2_RE.match(lines[j])
                or _RULE_RE.match(lines[j])
            ):
                j += 1
            content = "\n".join(lines[i + 1 : j])
            subsections.append((m.group(1).strip(), bool(content.strip())))
            i = j
        else:
            i += 1

    if not subsections:
        return "absent", subsections
    filled_count = sum(1 for _, filled in subsections if filled)
    if filled_count == 0:
        return "all_empty", subsections
    if filled_count == len(subsections):
        return "full", subsections
    return "mixed", subsections


def _patterns_missing(
    patterns: Sequence[str], subsections: Sequence[tuple[str, bool]]
) -> list[str]:
    """Patterns absent from the section or present-but-empty.

    Heading matching is case-insensitive on the display name
    (pre-existing notes render e.g. `Youtube Summary` for
    youtube_summary; .title() reproduces that, case-folding is cheap
    insurance against hand-edited headings).
    """
    filled = {name.strip().lower() for name, is_filled in subsections if is_filled}
    missing = []
    for pattern in patterns:
        display = _display_name(pattern).strip().lower()
        if display not in filled:
            missing.append(pattern)
    return missing


def scan_vault(
    output_dir: Path, patterns: Sequence[str] = _DEFAULT_SCAN_PATTERNS
) -> list[dict[str, Any]]:
    """Scan the vault for retro-backfill candidates.

    Args:
        output_dir: The youtube notes directory (resolved by the caller
            via config.resolve_output_dir — same helper cli.py uses, so
            $OBSVAULT / config.output_dir semantics match exactly).
        patterns: Target pattern ids used to compute patterns_missing.

    Returns:
        Candidate dicts: {path, video_id, title, status, transcript,
        patterns_missing, word_count, ai_analysis_state}. Notes with
        status "duplicate" or without a video_id are skipped (the
        latter reported to stdout). Missing status is treated as raw.
    """
    candidates: list[dict[str, Any]] = []
    for path in sorted(Path(output_dir).glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"⚠️  Cannot read {path.name}: {e}", file=sys.stderr)
            continue

        fm_text, body = split_note(text)
        fm = _parse_frontmatter(fm_text)

        status = str(fm.get("status") or "raw").strip()
        if status == "duplicate":
            continue

        video_id = str(fm.get("video_id") or "").strip()
        if not video_id:
            print(f"⚠️  Skipping (no video_id in frontmatter): {path.name}")
            continue

        transcript = extract_transcript_from_body(body)
        state, subsections = _classify_ai_analysis(body)

        candidates.append(
            {
                "path": path,
                "video_id": video_id,
                "title": str(fm.get("title") or path.stem),
                "status": status,
                "transcript": transcript,
                "patterns_missing": _patterns_missing(patterns, subsections),
                "word_count": len(transcript.split()) if transcript else 0,
                "ai_analysis_state": state,
            }
        )
    return candidates


# ---------------------------------------------------------------------------
# Note editing (surgical, in place)
# ---------------------------------------------------------------------------


def _find_subsection(body: str, display: str) -> Optional[tuple[int, int, bool]]:
    """Locate a `### {display}` subsection inside `## AI Analysis`.

    Returns (content_start_line, content_end_line, filled) where the
    content span runs from the line after the heading up to (exclusive)
    the next boundary (### / ## / column-0 `---` rule), or None when
    the subsection does not exist.
    """
    lines = body.split("\n")
    n = len(lines)
    target = display.strip().lower()
    in_ai = False

    i = 0
    while i < n:
        line = lines[i]
        if _AI_ANALYSIS_HEADING_RE.match(line):
            in_ai = True
        elif _H2_RE.match(line):
            in_ai = False
        elif in_ai:
            m = _SUBSECTION_HEADING_RE.match(line)
            if m and m.group(1).strip().lower() == target:
                j = i + 1
                while j < n and not (
                    _SUBSECTION_HEADING_RE.match(lines[j])
                    or _H2_RE.match(lines[j])
                    or _RULE_RE.match(lines[j])
                ):
                    j += 1
                content = "\n".join(lines[i + 1 : j])
                return i + 1, j, bool(content.strip())
        i += 1
    return None


def _content_lines(meta_line: str, output: str) -> list[str]:
    """Render subsection content lines (heading body shape)."""
    lines = [""]
    if meta_line:
        lines += [meta_line, ""]
    lines += [output, ""]
    return lines


def _render_block(display: str, meta_line: str, output: str) -> str:
    """Render a fresh `### {Display}` block (mirrors incremental_writer)."""
    block = f"### {display}\n\n"
    if meta_line:
        block += f"{meta_line}\n\n"
    return f"{block}{output}\n\n"


def _create_ai_analysis_section(body: str, blocks: str) -> str:
    """Create a `## AI Analysis` section (after the transcript section).

    Local implementation instead of incremental_writer's helper: the
    upstream create-branch builds `"## AI Analysis\n\n" + blocks` but
    then splices in only `blocks`, silently dropping the section
    heading (reported; incremental_writer.py is read-only here).
    """
    lines = body.split("\n")
    ti = next(
        (k for k, line in enumerate(lines) if _TRANSCRIPT_HEADING_RE.match(line)),
        None,
    )
    if ti is not None:
        bi = next(
            (
                k
                for k in range(ti + 1, len(lines))
                if _SECTION_BOUNDARY_RE.match(lines[k])
            ),
            None,
        )
        if bi is not None:
            insert_at = sum(len(line) + 1 for line in lines[: bi + 1])
            return body[:insert_at] + "\n## AI Analysis\n\n" + blocks + body[insert_at:]
    return body.rstrip("\n") + "\n\n---\n\n## AI Analysis\n\n" + blocks


def _apply_pattern_outputs(
    body: str,
    pattern_outputs: dict[str, str],
    pattern_meta: dict[str, dict[str, Any]],
    force: bool,
) -> tuple[str, list[str]]:
    """Splice successful pattern outputs into the note body.

    - existing empty `### {Display}` heading -> fill with output;
    - existing filled heading -> replace only when force;
    - absent heading -> new block inserted inside `## AI Analysis`
      (section created when missing) via incremental_writer's
      _insert_into_ai_analysis.

    Returns (new_body, applied_patterns).
    """
    applied: list[str] = []
    new_blocks: list[str] = []

    for pattern, output in pattern_outputs.items():
        display = _display_name(pattern)
        meta_line = format_pattern_meta_line(pattern_meta.get(pattern) or {})
        span = _find_subsection(body, display)
        if span is not None:
            start, end, filled = span
            if filled and not force:
                continue
            lines = body.split("\n")
            lines[start:end] = _content_lines(meta_line, output)
            body = "\n".join(lines)
        else:
            new_blocks.append(_render_block(display, meta_line, output))
        applied.append(pattern)

    if new_blocks:
        if _AI_ANALYSIS_HEADING_RE.search(body, re.MULTILINE):
            # Heading exists: reuse incremental_writer's insertion
            # helper (same package, exercised by the --append flow) —
            # it inserts before the section's end boundary, which is
            # exactly the retro shape.
            body = _insert_into_ai_analysis(body, "".join(new_blocks))
        else:
            body = _create_ai_analysis_section(body, "".join(new_blocks))

    return body, applied


def _fence_transcript_in_place(
    body: str,
    raw_transcript: str,
    refined_text: Optional[str] = None,
    refinement_meta: Any = None,
) -> tuple[str, bool, bool]:
    """Fence the raw `## Transcript` content; optionally add refined section.

    NEVER modifies transcript content — unfenced text is wrapped in a
    fence_for()-safe code block; already-fenced sections are left
    alone. The `## Refined Transcript` section (fenced, with backend
    metadata line mirroring formatter.generate_markdown) is added right
    after the raw transcript section only when refined_text differs
    from the raw text.

    Returns (new_body, fenced_now, refined_added).
    """
    lines = body.split("\n")
    n = len(lines)
    i = next(
        (k for k, line in enumerate(lines) if _TRANSCRIPT_HEADING_RE.match(line)),
        None,
    )
    if i is None:
        return body, False, False

    j = next((k for k in range(i + 1, n) if _H2_RE.match(lines[k])), n)
    section_lines, had_rule = _strip_trailing_separator(lines[i + 1 : j])
    content = "\n".join(section_lines).strip()

    fenced_now = False
    new_section: list[str]
    if content.startswith("```"):
        new_section = ["", content, ""]
    else:
        fence = fence_for(raw_transcript)
        new_section = ["", f"{fence}text", raw_transcript, fence, ""]
        fenced_now = True

    refined_added = False
    already_has_refined = re.search(
        r"^## Refined Transcript[ \t]*$", body, re.MULTILINE
    )
    if (
        refined_text is not None
        and not already_has_refined
        and refined_text.strip()
        and refined_text.strip() != raw_transcript.strip()
    ):
        refined = refined_text.strip()
        rfence = fence_for(refined)
        backend = getattr(refinement_meta, "backend_used", "regex-only")
        changes = list(getattr(refinement_meta, "changes_made", None) or [])
        date = datetime.now().strftime("%Y-%m-%d")
        new_section += [
            "## Refined Transcript",
            "",
            f"{rfence}text",
            refined,
            rfence,
            "",
            f"*Refined via {backend} · {len(changes)} change(s) · {date}*",
            "",
        ]
        refined_added = True

    if had_rule:
        new_section += ["---", ""]

    lines[i + 1 : j] = new_section
    return "\n".join(lines), fenced_now, refined_added


def _duration_to_seconds(fm: dict[str, Any]) -> int:
    """'MM:SS' / 'HH:MM:SS' (or duration_seconds int) -> seconds."""
    raw = fm.get("duration_seconds")
    try:
        if raw is not None and int(raw) > 0:
            return int(raw)
    except (TypeError, ValueError):
        pass
    text = str(fm.get("duration") or "").strip()
    if not text:
        return 0
    try:
        parts = [int(p) for p in text.split(":")]
    except ValueError:
        return 0
    if not parts or len(parts) > 3:
        return 0
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def _compact_upload_date(fm: dict[str, Any]) -> str:
    """frontmatter 'YYYY-MM-DD' (or already-compact) -> 'YYYYMMDD'."""
    raw = str(fm.get("upload_date") or "").strip()
    compact = raw.replace("-", "")
    return compact if len(compact) == 8 else ""


def _build_video_info(fm: dict[str, Any], video_id: str, body: str) -> dict[str, Any]:
    """Minimal yt-dlp-shaped video_info for orchestrate/VideoContext.

    VideoContext.from_video_info is fully .get()-tolerant, so missing
    keys degrade gracefully (same approach cli.py's --append flow takes
    with {"id": video_id}).
    """
    description = ""
    lines = body.split("\n")
    n = len(lines)
    i = next(
        (
            k
            for k, line in enumerate(lines)
            if re.match(r"^## Description[ \t]*$", line)
        ),
        None,
    )
    if i is not None:
        j = next((k for k in range(i + 1, n) if _H2_RE.match(lines[k])), n)
        section_lines, _ = _strip_trailing_separator(lines[i + 1 : j])
        description = "\n".join(section_lines).strip()

    tags = fm.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    return {
        "id": video_id,
        "title": str(fm.get("title") or "Untitled"),
        "channel": str(fm.get("channel") or ""),
        "upload_date": _compact_upload_date(fm),
        "duration": _duration_to_seconds(fm),
        "tags": [str(t) for t in tags],
        "description": description,
    }


# ---------------------------------------------------------------------------
# Per-note retro run
# ---------------------------------------------------------------------------


def run_retro_note(
    candidate: dict[str, Any],
    patterns: Sequence[str],
    config: Config,
    model_alias: str,
    dry_run: bool = False,
    cache_manager_factory: Optional[Callable[[], CacheManager]] = None,
) -> dict[str, Any]:
    """Run the retro backfill on one candidate note, in place.

    Args:
        candidate: A scan_vault() candidate dict.
        patterns: The fabric patterns to run for THIS note (already
            intersected with patterns_missing / expanded by --force).
        config: Loaded Config.
        model_alias: Resolved model alias (fabric_orchestrator resolves
            it further against the registry).
        dry_run: When True, performs no I/O at all (defensive; run_retro
            never calls this in dry-run mode).
        cache_manager_factory: Optional factory returning a CacheManager
            (tests inject an isolated cache dir). Default: real
            ~/.yt-obsidian/cache manager.

    Returns:
        Report dict: {path, video_id, patterns_attempted,
        patterns_succeeded, models_used, refined, transcript_fenced,
        status_changed, cache_saved, skipped, error, success}.
    """
    path: Path = candidate["path"]
    report: dict[str, Any] = {
        "path": path,
        "video_id": candidate["video_id"],
        "patterns_attempted": list(patterns),
        "patterns_succeeded": [],
        "models_used": {},
        "refined": False,
        "transcript_fenced": False,
        "status_changed": False,
        "cache_saved": False,
        "skipped": None,
        "error": None,
        "success": False,
    }

    transcript = candidate.get("transcript")
    if not transcript:
        report["skipped"] = "no transcript"
        return report

    if dry_run:
        report["skipped"] = "dry run"
        return report

    text = path.read_text(encoding="utf-8")
    fm_text, body = split_note(text)
    fm = _parse_frontmatter(fm_text)

    # 1. Offline regex refinement (never raises, no network).
    refinement = refine_transcript(transcript, backend="regex-only")
    analysis_transcript = refinement.refined_text
    report["refined"] = analysis_transcript.strip() != transcript.strip()

    # 2. Fabric patterns via the module-level orchestrator (monkeypatch
    #    point: tests patch ytobs.retro.FabricOrchestrator).
    orchestrator = FabricOrchestrator(
        patterns=list(patterns),
        timeout=config.timeout_per_pattern,
        max_chunk_tokens=config.chunk_size,
        debug=False,
        stream=False,
        model=model_alias,
        config=config,
    )
    result = orchestrator.orchestrate(
        transcript=analysis_transcript,
        video_title=str(fm.get("title") or path.stem),
        video_duration_seconds=_duration_to_seconds(fm),
        video_info=_build_video_info(fm, candidate["video_id"], body),
    )

    # 3. Only successful patterns with non-empty output touch the note
    #    (failed patterns must stay re-runnable).
    pattern_outputs: dict[str, str] = {}
    pattern_meta: dict[str, dict[str, Any]] = {}
    new_runs: list[dict[str, Any]] = []
    for pattern in patterns:
        pr = result.pattern_results.get(pattern)
        if pr is None:
            continue
        if pr.success and pr.combined_output.strip():
            pattern_outputs[pattern] = pr.combined_output.strip()
            pattern_meta[pattern] = {
                "models_used": pr.models_used,
                "timestamp": pr.run_timestamp,
            }
            new_runs.append(
                {
                    "pattern": pattern,
                    "models_used": list(pr.models_used or []),
                    "timestamp": str(pr.run_timestamp or ""),
                    "source": "retro",
                }
            )
        else:
            report["models_used"][pattern] = list(pr.models_used or [])

    succeeded = list(pattern_outputs.keys())
    report["patterns_succeeded"] = succeeded
    report["models_used"].update({p: pattern_meta[p]["models_used"] for p in succeeded})

    if not succeeded:
        report["error"] = "no pattern produced output"
        return report

    # 4. Surgical body edits.
    body, _applied = _apply_pattern_outputs(
        body, pattern_outputs, pattern_meta, force=bool(candidate.get("_force"))
    )
    body, fenced_now, _ = _fence_transcript_in_place(
        body, transcript, analysis_transcript, refinement
    )
    report["transcript_fenced"] = fenced_now

    # 5. Frontmatter: pattern_runs (line-based append), then status +
    #    fabric_patterns via update_frontmatter (body stays verbatim).
    new_fm = merge_pattern_runs(fm_text, new_runs)

    new_text = f"---\n{new_fm}\n---\n{body}"
    status = str(fm.get("status") or "raw").strip()
    if status in ("raw", "draft"):
        new_text = update_frontmatter(new_text, {"status": "analyzed"})
        report["status_changed"] = True
    for pattern in succeeded:
        new_text = update_frontmatter(
            new_text,
            {"fabric_patterns": pattern},
            append_keys=["fabric_patterns"],
        )

    # 6. Atomic in-place write (with backup). NEVER creates files.
    atomic_write_note(path, new_text, backup=True)

    # 7. Cache merge (failures are non-fatal for the note itself).
    try:
        if cache_manager_factory is not None:
            cache = cache_manager_factory()
        else:
            cache = CacheManager(get_cache_dir())
        now = datetime.now().isoformat()
        event = {
            "timestamp": now,
            "mode": "retro",
            "model": model_alias,
            "patterns_run": succeeded,
            "pattern_runs": new_runs,
            "success": True,
        }
        existing = cache.get_cache(candidate["video_id"])
        if existing is not None:
            entry = CacheEntry(
                video_id=candidate["video_id"],
                video_url=existing.video_url
                or str(
                    fm.get("url")
                    or f"https://youtube.com/watch?v={candidate['video_id']}"
                ),
                title=existing.title or str(fm.get("title") or path.stem),
                upload_date=existing.upload_date or _compact_upload_date(fm),
                duration_seconds=existing.duration_seconds or _duration_to_seconds(fm),
                transcript_word_count=existing.transcript_word_count
                or len(transcript.split()),
                markdown_path=str(path),
                last_updated=now,
                patterns_run=list(
                    dict.fromkeys(list(existing.patterns_run or []) + succeeded)
                ),
                processing_history=list(existing.processing_history or []) + [event],
                chunks=existing.chunks,
                phase1_metadata=existing.phase1_metadata,
                refinement_backend=refinement.backend_used,
                refinement_fell_back=refinement.fell_back,
                refinement_changes=refinement.changes_made,
            )
        else:
            entry = CacheEntry(
                video_id=candidate["video_id"],
                video_url=str(
                    fm.get("url")
                    or f"https://youtube.com/watch?v={candidate['video_id']}"
                ),
                title=str(fm.get("title") or path.stem),
                upload_date=_compact_upload_date(fm),
                duration_seconds=_duration_to_seconds(fm),
                transcript_word_count=len(transcript.split()),
                markdown_path=str(path),
                last_updated=now,
                patterns_run=succeeded,
                processing_history=[event],
                refinement_backend=refinement.backend_used,
                refinement_fell_back=refinement.fell_back,
                refinement_changes=refinement.changes_made,
            )
        report["cache_saved"] = cache.save_cache(candidate["video_id"], entry)
    except Exception as e:  # cache is best-effort; note already saved
        print(f"   ⚠️  Cache update failed for {candidate['video_id']}: {e}")

    report["success"] = True
    return report


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


def _select_run_patterns(
    candidate: dict[str, Any], patterns: Sequence[str], force: bool
) -> list[str]:
    """Patterns to run for a note: missing ones, or all with --force."""
    if force:
        return list(patterns)
    return [p for p in patterns if p in candidate["patterns_missing"]]


def run_retro(args: Any, config: Config) -> ExitCode:
    """`ytobs retro` — backfill fabric patterns on existing notes.

    Returns:
        0 when at least one note was enriched (per-note errors are
          reported but non-fatal);
        1 when notes were attempted but every one failed;
        2 when no actionable targets were found.
    """
    patterns: list[str] = list(args.patterns)
    force = bool(getattr(args, "force", False))
    limit = int(getattr(args, "limit", 5))
    dry_run = bool(getattr(args, "dry_run", False))
    model_alias = resolve_model(
        args.model if getattr(args, "model", None) else config.model, config
    )

    try:
        output_dir = resolve_output_dir(config)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    print(f"🔍 Scanning vault: {output_dir}")
    candidates = scan_vault(output_dir, patterns=patterns)

    # Selection: a note is a target when any requested pattern is
    # missing (absent or present-but-empty), or always with --force.
    # Notes without a usable transcript cannot be backfilled — they are
    # reported and set aside instead of consuming batch slots (the
    # default --limit 5 would otherwise be eaten by the vault's 41
    # placeholder notes while doing zero work).
    targets: list[dict[str, Any]] = []
    no_transcript: list[dict[str, Any]] = []
    for c in candidates:
        if not _select_run_patterns(c, patterns, force):
            continue
        if c["transcript"]:
            targets.append(c)
        else:
            no_transcript.append(c)

    print(
        f"   {len(candidates)} candidate(s) scanned · "
        f"{len(targets)} actionable · {len(no_transcript)} without transcript"
    )

    if no_transcript:
        print("⏭️  Cannot backfill (no usable transcript):")
        for c in no_transcript[:10]:
            print(f"   - {c['path'].name}")
        if len(no_transcript) > 10:
            print(f"   ... and {len(no_transcript) - 10} more")

    if not targets:
        print("📭 No retro targets found — nothing to backfill.")
        return 2

    # Cheapest first (quota-friendly): shortest transcripts at the top.
    targets.sort(key=lambda c: c["word_count"])
    batch = targets[: max(limit, 0)] if limit else []
    if not batch:
        print(f"📭 Limit {limit} selected 0 notes.")
        return 2

    # Plan table.
    print(f"\n📋 Retro batch ({len(batch)} of {len(targets)} targets, cheapest first):")
    print(f"   {'WORDS':>6}  {'VIDEO_ID':<12}  {'STATE':<9}  MISSING PATTERNS / NOTE")
    for c in batch:
        run_set = ", ".join(_select_run_patterns(c, patterns, force)) or "(force)"
        print(
            f"   {c['word_count']:>6}  {c['video_id']:<12}  "
            f"{c['ai_analysis_state']:<9}  {run_set}"
        )
        print(f"          └─ {c['path'].name}")

    if dry_run:
        print("\n🧪 DRY RUN — no writes, no fabric calls, no cache updates.")
        print(f"   Would run patterns {patterns} with model '{model_alias}'")
        if force:
            print("   --force: existing filled sections would be replaced")
        return 0

    print(f"\n🚀 Running retro backfill with model '{model_alias}'...\n")

    succeeded = failed = 0
    models_seen: list[str] = []
    for i, c in enumerate(batch, 1):
        run_set = _select_run_patterns(c, patterns, force)
        print(
            f"[{i}/{len(batch)}] {c['path'].name} ({c['video_id']}, "
            f"{c['word_count']} words)"
        )
        try:
            c["_force"] = force
            report = run_retro_note(c, run_set, config, model_alias)
        except Exception as e:
            failed += 1
            print(f"   ❌ error: {e}")
            continue
        finally:
            c.pop("_force", None)

        if report["skipped"]:
            print(f"   ⏭️  skipped: {report['skipped']}")
            continue
        if not report["success"]:
            failed += 1
            detail = report.get("error") or "unknown failure"
            print(f"   ❌ {detail}")
            continue

        succeeded += 1
        for p in report["patterns_succeeded"]:
            models = report["models_used"].get(p) or ["unknown"]
            print(f"   ✅ {p} ← {', '.join(models)}")
            for m in models:
                if m not in models_seen:
                    models_seen.append(m)
        extras = []
        if report["refined"]:
            extras.append("refined")
        if report["transcript_fenced"]:
            extras.append("fenced transcript")
        if report["status_changed"]:
            extras.append("status → analyzed")
        if report["cache_saved"]:
            extras.append("cached")
        if extras:
            print(f"   📝 {', '.join(extras)}")
        print()

    print("=" * 60)
    print("📊 Retro summary:")
    print(
        f"   Processed: {len(batch)} · Succeeded: {succeeded} · "
        f"Failed: {failed} · Skipped (no transcript): {len(no_transcript)}"
    )
    if models_seen:
        print(f"   Models used: {', '.join(models_seen)}")

    if succeeded == 0 and failed > 0:
        return 1
    return 0
