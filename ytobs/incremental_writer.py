"""
Incremental note writer for appending sections to existing markdown notes

This module allows adding new AI analysis sections to existing Obsidian notes
without re-running the entire analysis.
"""

from pathlib import Path
from typing import Dict, List, Any
import re
import yaml

from .exceptions import FileSystemError


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

        # Convert back to YAML
        self.frontmatter = yaml.dump(
            fm_dict, default_flow_style=False, allow_unicode=True
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

        # Convert back to YAML
        self.frontmatter = yaml.dump(
            fm_dict, default_flow_style=False, allow_unicode=True
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


def append_patterns_to_note(
    note_path: Path, pattern_outputs: Dict[str, str], update_frontmatter: bool = True
) -> None:
    """High-level function to append pattern outputs to existing note

    Args:
        note_path: Path to existing note
        pattern_outputs: Dict mapping pattern names to their outputs
        update_frontmatter: Whether to update patterns list in frontmatter
    """
    writer = IncrementalWriter(note_path)

    # Append each pattern as a new section
    for pattern_name, output in pattern_outputs.items():
        heading = f"AI Analysis - {pattern_name}"
        writer.append_section(heading, output, level=2)

    # Update frontmatter with new patterns
    if update_frontmatter:
        writer.append_to_frontmatter_list(
            "fabric_patterns", list(pattern_outputs.keys())
        )

    writer.save()
