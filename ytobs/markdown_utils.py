"""Markdown utilities for formatting and normalizing output.

This module provides non-LLM tools for cleaning up markdown structure,
particularly heading hierarchy issues from combining multiple outputs.
"""

import re
from typing import Optional


def normalize_headings(
    text: str,
    base_level: int = 3,
    max_level: int = 6
) -> str:
    """Normalize markdown heading levels to fit within a hierarchy.
    
    When combining multiple Fabric outputs, each may have its own # H1 headings.
    This function shifts all headings to start at a specified level.
    
    Example:
        Input (base_level=3):
            # Main Title
            ## Section
            ### Subsection
        
        Output:
            ### Main Title
            #### Section
            ##### Subsection
    
    Args:
        text: Markdown text with headings
        base_level: Target level for H1 headings (default: 3 for ###)
        max_level: Maximum heading level (default: 6)
    
    Returns:
        str: Text with normalized heading levels
    """
    if not text:
        return text
    
    lines = text.split('\n')
    result = []
    
    # Offset to add to each heading level
    # If base_level=3, H1 (#) becomes H3 (###), so offset = 2
    offset = base_level - 1
    
    for line in lines:
        # Match heading lines: one or more # at start, followed by space
        match = re.match(r'^(#{1,6})\s+(.*)$', line)
        
        if match:
            current_hashes = match.group(1)
            heading_text = match.group(2)
            current_level = len(current_hashes)
            
            # Calculate new level
            new_level = min(current_level + offset, max_level)
            new_hashes = '#' * new_level
            
            result.append(f"{new_hashes} {heading_text}")
        else:
            result.append(line)
    
    return '\n'.join(result)


def fix_duplicate_headings(text: str) -> str:
    """Remove or merge duplicate section headings.
    
    When combining chunked outputs, we may get repeated headings like:
        ## Key Points
        - point 1
        ## Key Points
        - point 2
    
    This function merges content under duplicate headings.
    
    Args:
        text: Markdown text potentially with duplicate headings
    
    Returns:
        str: Text with duplicate headings merged
    """
    if not text:
        return text
    
    lines = text.split('\n')
    
    # Track seen headings and their content
    sections: dict[str, list[str]] = {}
    current_heading: Optional[str] = None
    current_content: list[str] = []
    heading_order: list[str] = []
    
    for line in lines:
        # Check if this is a heading
        match = re.match(r'^(#{1,6})\s+(.*)$', line)
        
        if match:
            # Save previous section
            if current_heading:
                if current_heading not in sections:
                    sections[current_heading] = []
                    heading_order.append(current_heading)
                sections[current_heading].extend(current_content)
            
            # Start new section
            current_heading = line
            current_content = []
        else:
            current_content.append(line)
    
    # Save final section
    if current_heading:
        if current_heading not in sections:
            sections[current_heading] = []
            heading_order.append(current_heading)
        sections[current_heading].extend(current_content)
    
    # Rebuild document in order
    result = []
    for heading in heading_order:
        result.append(heading)
        result.extend(sections[heading])
    
    return '\n'.join(result)


def clean_horizontal_rules(text: str) -> str:
    """Remove excessive horizontal rules (---).
    
    Chunk outputs often end with ---, and combining creates multiple
    consecutive rules. This cleans them up.
    
    Args:
        text: Markdown text with potential excessive rules
    
    Returns:
        str: Text with cleaned up horizontal rules
    """
    if not text:
        return text
    
    # Replace multiple consecutive --- lines with single one
    text = re.sub(r'(\n---\s*\n)+', '\n\n---\n\n', text)
    
    # Remove --- at very start or end
    text = re.sub(r'^---\s*\n', '', text)
    text = re.sub(r'\n---\s*$', '', text)
    
    return text.strip()


def remove_chunk_markers(text: str) -> str:
    """Remove chunk part markers from combined output.
    
    Removes lines like:
        ## Part 1/10
        *Timestamp: 00:00:00 - 00:34:31*
    
    These are useful for debugging but clutter the final note.
    
    Args:
        text: Markdown text with chunk markers
    
    Returns:
        str: Text with chunk markers removed
    """
    if not text:
        return text
    
    lines = text.split('\n')
    result = []
    skip_next = False
    
    for line in lines:
        # Skip "Part X/Y" headers
        if re.match(r'^#{1,6}\s+Part\s+\d+/\d+', line):
            skip_next = True  # Skip the timestamp line too
            continue
        
        # Skip timestamp lines after Part headers
        if skip_next and line.strip().startswith('*Timestamp:'):
            skip_next = False
            continue
        
        skip_next = False
        result.append(line)
    
    return '\n'.join(result)


def format_combined_output(
    text: str,
    base_heading_level: int = 4,
    keep_chunk_markers: bool = False,
    clean_rules: bool = True
) -> str:
    """Apply all formatting fixes to combined Fabric output.
    
    This is the main entry point for cleaning up multi-chunk outputs.
    
    Pipeline:
    1. Optionally remove chunk markers (Part X/Y)
    2. Normalize heading levels
    3. Clean up horizontal rules
    
    Note: Duplicate heading merging is disabled as it's too aggressive
    and loses content structure from individual chunks.
    
    Args:
        text: Raw combined Fabric output
        base_heading_level: Target level for top headings (default: 4 for ####)
        keep_chunk_markers: Whether to keep Part X/Y markers (default: False)
        clean_rules: Whether to clean up --- rules (default: True)
    
    Returns:
        str: Cleaned and formatted markdown
    """
    if not text:
        return text
    
    # Step 1: Remove chunk markers if requested
    if not keep_chunk_markers:
        text = remove_chunk_markers(text)
    
    # Step 2: Normalize heading levels
    text = normalize_headings(text, base_level=base_heading_level)
    
    # Step 3: Clean horizontal rules
    if clean_rules:
        text = clean_horizontal_rules(text)
    
    # Note: We intentionally skip fix_duplicate_headings() here
    # as it's too aggressive and loses structure from chunks
    
    return text.strip()
