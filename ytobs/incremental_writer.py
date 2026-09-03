"""
Incremental note writer for appending sections to existing markdown notes

This module allows adding new AI analysis sections to existing Obsidian notes
without re-running the entire analysis.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import yaml

from .exceptions import FileSystemError
from .formatter import format_pattern_meta_line

_AI_ANALYSIS_HEADING_RE = re.compile(r"^## AI Analysis[ \t]*$", re.MULTILINE)
_TRANSCRIPT_HEADING_RE = re.compile(r"^## Transcript[ \t]*$", re.MULTILINE)
# A section boundary is the next column-0 H2 heading or horizontal rule
# (formatter output separates sections with `---` rules)
_SECTION_BOUNDARY_RE = re.compile(r"^(?:## .+|---)[ \t]*$", re.MULTILINE)


class IncrementalWriter:
    """Append sections to existing markdown notes"""

    def __init__(self, note_path: Path):
        """Initialize incremental writer.

        Args:
            note_path: Path to existing markdown note

        Raises:
            FileNotFoundError: If note doesn't exist.
            FileSystemError: If note can't be read (EPERM, iCloud lock, etc.).
        """
        self.note_path = Path(note_path).expanduser()
        try:
            if not self.note_path.exists():
                raise FileNotFoundError(f"Note not found: {note_path}")
        except OSError as e:
            raise FileSystemError(f"Cannot access note path {note_path}: {e}") from e

        self.content = self._load_note()
        self.frontmatter, self.body = self._parse_note()

    def _load_note(self) -> str:
        """Load existing note, raising FileSystemError on failure."""
        try:
            return self.note_path.read_text(encoding="utf-8")
        except OSError as e:
            raise FileSystemError(f"Cannot read note {self.note_path}: {e}") from e

    def _parse_note(self) -> tuple[str, str]:
        """Split frontmatter and body

        Returns:
            Tuple of (frontmatter_text, body_text)
        """
        # Match YAML frontmatter block
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", self.content, re.DOTALL)
        if match:
            return match.group(1), match.group(2)

        # No frontmatter found
        return "", self.content

    def append_section(self, heading: str, content: str, level: int = 2) -> None:
        """Append new section to note

        Args:
            heading: Section heading text
            content: Section content
            level: Heading level (2 for ##, 3 for ###, etc.)
        """
        heading_prefix = "#" * level
        section = f"\n\n{heading_prefix} {heading}\n\n{content}\n"
        self.body += section

    def update_frontmatter_field(self, field: str, value: Any) -> None:
        """Update a single field in frontmatter

        Args:
            field: YAML field name
            value: New value for field
        """
        # Parse current frontmatter
        try:
            fm_dict = yaml.safe_load(self.frontmatter) if self.frontmatter else {}
        except yaml.YAMLError:
            fm_dict = {}

        # Update field
        fm_dict[field] = value

        # Convert back to YAML (sort_keys=False preserves original key
        # order — safe_load keeps insertion order, so re-dump is stable)
        self.frontmatter = yaml.dump(
            fm_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).strip()

    def append_to_frontmatter_list(self, field: str, new_items: List[Any]) -> None:
        """Append items to a list field in frontmatter

        Args:
            field: YAML field name (must be a list)
            new_items: Items to append
        """
        # Parse current frontmatter
        try:
            fm_dict = yaml.safe_load(self.frontmatter) if self.frontmatter else {}
        except yaml.YAMLError:
            fm_dict = {}

        # Get existing list or create new one
        existing_list = fm_dict.get(field, [])
        if not isinstance(existing_list, list):
            existing_list = [existing_list]

        # Append new items (avoid duplicates)
        for item in new_items:
            if item not in existing_list:
                existing_list.append(item)

        fm_dict[field] = existing_list

        # Convert back to YAML (sort_keys=False preserves original key
        # order — safe_load keeps insertion order, so re-dump is stable)
        self.frontmatter = yaml.dump(
            fm_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).strip()

    def save(self) -> None:
        """Save updated note, raising FileSystemError on failure."""
        new_content = f"---\n{self.frontmatter}\n---\n{self.body}"
        try:
            self.note_path.write_text(new_content, encoding="utf-8")
        except OSError as e:
            raise FileSystemError(f"Cannot write to {self.note_path}: {e}") from e

    def preview(self) -> str:
        """Preview updated note content without saving

        Returns:
            Complete note content as string
        """
        return f"---\n{self.frontmatter}\n---\n{self.body}"


def _insert_into_ai_analysis(body: str, blocks: str) -> str:
    """Insert new `### ` blocks inside the note's `## AI Analysis` section.

    Matches the formatter output shape: blocks go under the existing
    `## AI Analysis` heading (before the section's end boundary — the next
    column-0 H2 heading or `---` rule). If the note has no such section,
    one is created after the transcript section (or at the end of the
    body when there is no transcript section either).

    Args:
        body: Note body (without frontmatter)
        blocks: Pre-rendered `### {Pattern}` blocks (each ending in a
            blank line)

    Returns:
        Updated body text
    """
    ai_heading = _AI_ANALYSIS_HEADING_RE.search(body)
    if ai_heading is None:
        section = "## AI Analysis\n\n" + blocks
        transcript_heading = _TRANSCRIPT_HEADING_RE.search(body)
        if transcript_heading is None:
            return body.rstrip("\n") + "\n\n---\n\n" + section
        boundary = _SECTION_BOUNDARY_RE.search(body, transcript_heading.end())
        if boundary is None:
            return body.rstrip("\n") + "\n\n---\n\n" + section
        insert_at = boundary.start()
    else:
        boundary = _SECTION_BOUNDARY_RE.search(body, ai_heading.end())
        if boundary is None:
            return body.rstrip("\n") + "\n\n" + blocks
        insert_at = boundary.start()

    # Ensure exactly one blank line before the insertion point
    prefix = "" if insert_at == 0 or body[:insert_at].endswith("\n\n") else "\n"
    return body[:insert_at] + prefix + blocks + body[insert_at:]


def append_patterns_to_note(
    note_path: Path,
    pattern_outputs: Dict[str, str],
    update_frontmatter: bool = True,
    pattern_meta: Optional[Dict[str, dict]] = None,
) -> List[str]:
    """Append pattern outputs inside the note's `## AI Analysis` section.

    Patterns with empty/whitespace-only output are skipped (they must not
    produce empty sections or be marked as run). Blocks are inserted as
    `### {Pattern Name}` sections matching the formatter's output shape;
    each heading gets a model-provenance metadata line when pattern_meta
    provides one.

    Args:
        note_path: Path to existing note
        pattern_outputs: Dict mapping pattern names to their outputs
        update_frontmatter: Whether to update patterns list in frontmatter
        pattern_meta: Optional dict of pattern_name -> {models_used,
            timestamp} provenance for the metadata lines (W1)

    Returns:
        List of pattern names actually appended (skipped empties excluded)
    """
    writer = IncrementalWriter(note_path)

    # Render blocks; skip patterns with empty/whitespace-only output
    appended: List[str] = []
    blocks: List[str] = []
    for pattern_name, output in pattern_outputs.items():
        if not output or not output.strip():
            continue
        display_name = pattern_name.replace("_", " ").title()
        block = f"### {display_name}\n\n"
        meta = (pattern_meta or {}).get(pattern_name)
        if meta:
            meta_line = format_pattern_meta_line(meta)
            if meta_line:
                block += f"{meta_line}\n\n"
        block += f"{output}\n\n"
        blocks.append(block)
        appended.append(pattern_name)

    if not appended:
        return []

    writer.body = _insert_into_ai_analysis(writer.body, "".join(blocks))

    # Update frontmatter with new patterns
    if update_frontmatter:
        writer.append_to_frontmatter_list("fabric_patterns", appended)

    writer.save()
    return appended
