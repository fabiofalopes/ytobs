"""Enriched packet builder for context-aware Fabric processing.

This module creates "enriched packets" - chunks of content wrapped with
contextual metadata that helps AI models understand position and broader
context when processing segments of longer content.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, List


@dataclass
class VideoContext:
    """Raw YouTube metadata context for packet enrichment.
    
    This provides YouTube-specific context that helps AI models:
    - Correctly spell technical terms (from tags)
    - Attribute speaker/creator context (from channel)
    - Understand video focus (from description excerpt)
    
    Attributes:
        video_id: YouTube video ID
        video_url: Full YouTube URL
        channel_name: Channel/creator name
        channel_url: Channel URL (optional)
        upload_date: Upload date as YYYY-MM-DD
        tags: List of video tags (first 10)
        description_excerpt: First ~150 words of description
        duration_formatted: Duration as HH:MM:SS
    """
    video_id: str
    video_url: str
    channel_name: str
    upload_date: str
    tags: List[str] = field(default_factory=list)
    description_excerpt: str = ""
    duration_formatted: str = ""
    channel_url: str = ""
    
    @classmethod
    def from_video_info(cls, video_info: dict, max_tags: int = 10, description_words: int = 150) -> "VideoContext":
        """Create VideoContext from extractor's video_info dict.
        
        Args:
            video_info: Dict from extractor.extract_metadata()
            max_tags: Maximum number of tags to include (default: 10)
            description_words: Max words from description (default: 150)
        
        Returns:
            VideoContext: Populated context object
        """
        # Extract tags (limit to max_tags)
        tags = video_info.get('tags', []) or []
        if isinstance(tags, list):
            tags = tags[:max_tags]
        else:
            tags = []
        
        # Extract description excerpt (first N words)
        description = video_info.get('description', '') or ''
        words = description.split()
        if len(words) > description_words:
            description_excerpt = ' '.join(words[:description_words]) + '...'
        else:
            description_excerpt = description
        
        # Format duration
        duration_seconds = video_info.get('duration', 0) or 0
        duration_formatted = _seconds_to_timestamp(duration_seconds)
        
        # Format upload date
        upload_date_raw = video_info.get('upload_date', '') or ''
        if len(upload_date_raw) == 8:  # YYYYMMDD format
            upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"
        else:
            upload_date = upload_date_raw
        
        return cls(
            video_id=video_info.get('id', ''),
            video_url=video_info.get('webpage_url', video_info.get('url', '')),
            channel_name=video_info.get('channel', video_info.get('uploader', 'Unknown')),
            channel_url=video_info.get('channel_url', video_info.get('uploader_url', '')),
            upload_date=upload_date,
            tags=tags,
            description_excerpt=description_excerpt,
            duration_formatted=duration_formatted
        )
    
    def to_preamble_section(self) -> str:
        """Generate VIDEO CONTEXT section for preamble.
        
        Returns:
            str: Formatted VIDEO CONTEXT block
        """
        tags_str = ', '.join(self.tags) if self.tags else 'None'
        
        lines = [
            "VIDEO CONTEXT:",
            f"- Channel: {self.channel_name}",
            f"- Published: {self.upload_date}",
            f"- Duration: {self.duration_formatted}",
            f"- Tags: {tags_str}",
        ]
        
        if self.description_excerpt:
            # Truncate very long excerpts for display
            excerpt = self.description_excerpt[:300] + '...' if len(self.description_excerpt) > 300 else self.description_excerpt
            lines.append(f"- Description: {excerpt}")
        
        return '\n'.join(lines)


def _seconds_to_timestamp(seconds: int) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class EnrichedPacket:
    """Context-enriched chunk for Fabric AI processing.
    
    An enriched packet contains a chunk of transcript plus metadata about:
    - Video context (channel, tags, description) - NEW in V4.0
    - Global context (video title, summary, key topics from Phase 1 AI)
    - Position in sequence (beginning/middle/end)
    - Temporal context (timestamp range)
    
    The packet can generate a Fabric-compatible input string that includes
    a preamble with this context, followed by the actual content.
    
    Attributes:
        video_title: Title of the video/content
        video_summary: 1-2 sentence overview of full content
        key_topics: Comma-separated list of main topics/entities
        chunk_id: Unique identifier (e.g., "chunk_001")
        chunk_index: Zero-based index in sequence
        total_chunks: Total number of chunks in sequence
        position: Position category ("single", "beginning", "middle", "end")
        timestamp_range: Tuple of (start_time, end_time) as HH:MM:SS strings
        transcript_segment: The actual chunk text content
        token_count: Number of tokens in transcript_segment
        video_context: Optional VideoContext with YouTube metadata (V4.0)
    """
    
    # Global context metadata (from Phase 1 AI analysis)
    video_title: str
    video_summary: str
    key_topics: str
    
    # Chunk metadata
    chunk_id: str
    chunk_index: int
    total_chunks: int
    position: str
    timestamp_range: Tuple[str, str]
    
    # Content
    transcript_segment: str
    token_count: int = 0
    
    # YouTube metadata context (V4.0 - optional for backward compatibility)
    video_context: Optional[VideoContext] = None
    
    def to_fabric_input(self) -> str:
        """Format packet as Fabric-compatible input.
        
        Generates a complete input string with:
        1. Contextual preamble (metadata)
        2. Content separator
        3. Actual transcript segment
        
        This string is meant to be passed to fabric-ai via stdin after
        the pattern's system prompt.
        
        Returns:
            str: Complete input string ready for Fabric processing
        """
        preamble = self._generate_preamble()
        return f"{preamble}\n\n{self.transcript_segment}"
    
    def _generate_preamble(self) -> str:
        """Generate contextual preamble header.
        
        Creates a structured metadata block that provides:
        - VIDEO CONTEXT: YouTube metadata (channel, tags, description) - V4.0
        - CONTENT CONTEXT: AI-analyzed overview
        - CHUNK INFORMATION: Position and temporal details
        
        Returns:
            str: Markdown-formatted preamble
        """
        position_note = self._get_position_note()
        
        # Format chunk position display
        chunk_display = f"chunk {self.chunk_index + 1} of {self.total_chunks}"
        
        # Build preamble sections
        sections = ["---"]
        
        # Add VIDEO CONTEXT if available (V4.0)
        if self.video_context:
            sections.append(self.video_context.to_preamble_section())
            sections.append("")  # Blank line between sections
        
        # Add CONTENT CONTEXT (AI-analyzed)
        sections.append(f"""CONTENT CONTEXT:
- Title: {self.video_title}
- Overview: {self.video_summary}
- Key Topics: {self.key_topics}""")
        
        # Add CHUNK INFORMATION
        sections.append(f"""
CHUNK INFORMATION:
- Position: {self.position} ({chunk_display})
- Timestamp Range: {self.timestamp_range[0]} - {self.timestamp_range[1]}
- Processing Note: {position_note}""")
        
        sections.append("\n---")
        
        return '\n'.join(sections)
    
    def _get_position_note(self) -> str:
        """Generate position-specific processing instruction.
        
        Provides guidance to the AI model on how to approach this chunk
        based on its position in the sequence.
        
        Returns:
            str: Position-appropriate processing note
        """
        notes = {
            "single": (
                "This is the complete content. Analyze comprehensively."
            ),
            
            "beginning": (
                "This is the opening segment. Focus on introductions, setup, "
                "and initial themes. Establish context for what follows."
            ),
            
            "middle": (
                "This is a middle segment continuing from previous content. "
                "Focus on development, details, and progression of established themes."
            ),
            
            "end": (
                "This is the final segment concluding previous content. "
                "Focus on conclusions, resolutions, and final takeaways."
            )
        }
        
        return notes.get(self.position, notes["middle"])


def determine_position(chunk_index: int, total_chunks: int) -> str:
    """Determine position category for a chunk.
    
    Logic:
    - If only 1 chunk total: "single"
    - First chunk of multi-chunk: "beginning"
    - Last chunk of multi-chunk: "end"
    - Any middle chunk: "middle"
    
    Args:
        chunk_index: Zero-based index of current chunk
        total_chunks: Total number of chunks
    
    Returns:
        str: Position category ("single", "beginning", "middle", "end")
    
    Examples:
        >>> determine_position(0, 1)
        'single'
        >>> determine_position(0, 3)
        'beginning'
        >>> determine_position(1, 3)
        'middle'
        >>> determine_position(2, 3)
        'end'
    """
    if total_chunks == 1:
        return "single"
    elif chunk_index == 0:
        return "beginning"
    elif chunk_index == total_chunks - 1:
        return "end"
    else:
        return "middle"


def create_packet(
    video_title: str,
    video_summary: str,
    key_topics: str,
    chunk_id: str,
    chunk_index: int,
    total_chunks: int,
    timestamp_range: Tuple[str, str],
    transcript_segment: str,
    token_count: Optional[int] = None,
    video_context: Optional[VideoContext] = None
) -> EnrichedPacket:
    """Factory function to create an enriched packet.
    
    Convenience function that handles position determination and
    provides a clean interface for packet creation.
    
    Args:
        video_title: Title of video/content
        video_summary: Brief 1-2 sentence overview
        key_topics: Comma-separated topics
        chunk_id: Unique identifier (e.g., "chunk_001")
        chunk_index: Zero-based chunk index
        total_chunks: Total chunk count
        timestamp_range: (start, end) timestamps as HH:MM:SS
        transcript_segment: Actual text content
        token_count: Optional pre-calculated token count
        video_context: Optional VideoContext with YouTube metadata (V4.0)
    
    Returns:
        EnrichedPacket: Configured packet ready for Fabric processing
    """
    position = determine_position(chunk_index, total_chunks)
    
    # Use provided token count or default to 0
    # (token counting will be done by chunker module)
    final_token_count = token_count if token_count is not None else 0
    
    return EnrichedPacket(
        video_title=video_title,
        video_summary=video_summary,
        key_topics=key_topics,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        position=position,
        timestamp_range=timestamp_range,
        transcript_segment=transcript_segment,
        token_count=final_token_count,
        video_context=video_context
    )
