"""Token counting utilities for intelligent content chunking.

This module provides token counting and text chunking functionality
using tiktoken (OpenAI's tokenizer). This enables size-aware splitting
of transcripts to stay within model context limits.
"""

import math
import tiktoken
from typing import List, Tuple


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text using specified model encoding.

    Uses tiktoken to get accurate token counts for various model families.
    Defaults to GPT-4 encoding which works well for most modern LLMs.

    Args:
        text: Text to count tokens for
        model: Model encoding to use (default: "gpt-4")

    Returns:
        int: Number of tokens in text

    Examples:
        >>> count_tokens("Hello world")
        2
        >>> count_tokens("The Chinese AI Iceberg")
        4
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base (GPT-4/GPT-3.5-turbo encoding)
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def calculate_optimal_chunk_size(
    total_tokens: int, max_chunk_tokens: int = 50000
) -> int:
    """Calculate optimal chunk size to distribute tokens evenly.

    Instead of creating uneven chunks (e.g., 8K + 5.3K), this calculates
    a chunk size that distributes content more evenly across all chunks.

    Args:
        total_tokens: Total tokens in full content
        max_chunk_tokens: Maximum tokens per chunk (default: 8000)

    Returns:
        int: Optimal chunk size in tokens

    Examples:
        >>> calculate_optimal_chunk_size(13310, 8000)
        6655  # Creates 2 chunks of ~6.6K each instead of 8K + 5.3K
        >>> calculate_optimal_chunk_size(5000, 8000)
        5000  # Single chunk, no splitting needed
    """
    if total_tokens <= max_chunk_tokens:
        return total_tokens

    # Calculate number of chunks needed
    num_chunks = math.ceil(total_tokens / max_chunk_tokens)

    # Distribute evenly
    optimal_size = math.ceil(total_tokens / num_chunks)

    # Don't exceed max
    return min(optimal_size, max_chunk_tokens)


def estimate_processing_time(token_count: int) -> float:
    """Estimate API call duration based on token count.

    Provides rough estimate for planning and progress reporting.
    Based on typical LLM API response times.

    Args:
        token_count: Number of tokens to process

    Returns:
        float: Estimated seconds for processing

    Examples:
        >>> estimate_processing_time(1000)
        2.0  # ~2 seconds for 1K tokens
        >>> estimate_processing_time(8000)
        16.0  # ~16 seconds for 8K tokens
    """
    # Conservative estimate: ~2 seconds per 1K tokens
    return (token_count / 1000) * 2


def chunk_text_by_sentences(
    text: str, max_tokens: int = 8000, overlap_tokens: int = 500
) -> List[dict]:
    """Split text into chunks respecting natural boundaries.

    Splits text into chunks while:
    - STRICTLY staying under token limit
    - Preserving complete sentences when punctuation exists
    - Falling back to word boundaries for unpunctuated text (auto-transcripts)
    - Adding overlap between chunks for context continuity

    Args:
        text: Full text to chunk
        max_tokens: Maximum tokens per chunk (HARD LIMIT)
        overlap_tokens: Tokens to overlap between chunks

    Returns:
        List[dict]: List of chunk dictionaries
    """
    import re

    # Check punctuation density - if too sparse, treat as unpunctuated
    word_count = len(text.split())
    punct_count = len(re.findall(r"[.!?]", text))

    # Threshold: at least 1 sentence-ending punct per 100 words (typical speech has ~20 per 100)
    has_sufficient_punctuation = (punct_count / max(word_count, 1)) > 0.01

    if has_sufficient_punctuation:
        # Split into sentences (original approach)
        segments = _split_into_sentences(text)
    else:
        # For unpunctuated/sparse text (auto-transcripts), split by word groups
        # Use smaller groups for finer-grained control
        segments = _split_into_word_groups(text, target_tokens=200)

    chunks = []
    current_chunk = []
    current_tokens = 0
    chunk_index = 0
    chunk_start_offset = 0

    for segment in segments:
        # Calculate what the new total would be
        test_text = " ".join(current_chunk + [segment])
        test_tokens = count_tokens(test_text)

        # HARD CHECK: If adding this segment exceeds limit, finalize current chunk
        if test_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunk_text = " ".join(current_chunk)
            actual_tokens = count_tokens(chunk_text)

            chunks.append(
                {
                    "id": f"chunk_{chunk_index + 1:03d}",
                    "index": chunk_index,
                    "text": chunk_text,
                    "token_count": actual_tokens,
                    "start_pos": chunk_start_offset,
                    "end_pos": chunk_start_offset + len(chunk_text),
                }
            )

            # Prepare for next chunk with overlap
            overlap_segments = _get_overlap_sentences(current_chunk, overlap_tokens)

            # Calculate new start position
            if overlap_segments:
                overlap_text = " ".join(overlap_segments)
                chunk_start_offset = (
                    chunk_start_offset + len(chunk_text) - len(overlap_text)
                )
            else:
                chunk_start_offset = chunk_start_offset + len(chunk_text) + 1

            current_chunk = overlap_segments.copy()
            current_tokens = (
                count_tokens(" ".join(current_chunk)) if current_chunk else 0
            )
            chunk_index += 1

        # Add segment to current chunk
        current_chunk.append(segment)
        current_tokens = count_tokens(" ".join(current_chunk))

    # Add final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)

        chunks.append(
            {
                "id": f"chunk_{chunk_index + 1:03d}",
                "index": chunk_index,
                "text": chunk_text,
                "token_count": count_tokens(chunk_text),
                "start_pos": chunk_start_offset,
                "end_pos": chunk_start_offset + len(chunk_text),
            }
        )

    return chunks


def _split_into_word_groups(text: str, target_tokens: int = 200) -> List[str]:
    """Split unpunctuated text into word groups of approximately target_tokens.

    Used for auto-generated transcripts that lack punctuation.
    Creates logical break points for chunking.

    Args:
        text: Text to split (assumes no sentence punctuation)
        target_tokens: Target tokens per group (default: 200 for finer control)

    Returns:
        List[str]: List of word groups
    """
    words = text.split()

    if not words:
        return []

    # Estimate words per group (roughly 0.75 words per token for English)
    words_per_group = max(10, int(target_tokens * 0.75))

    groups = []
    current_group = []

    for word in words:
        current_group.append(word)

        if len(current_group) >= words_per_group:
            groups.append(" ".join(current_group))
            current_group = []

    # Add remaining words
    if current_group:
        groups.append(" ".join(current_group))

    return groups


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences.

    Uses simple heuristic: split on period + space, question mark, exclamation.
    Not perfect but works well for YouTube transcripts.

    Args:
        text: Text to split

    Returns:
        List[str]: List of sentences
    """
    import re

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text)

    # Filter out empty strings
    return [s.strip() for s in sentences if s.strip()]


def _get_overlap_sentences(sentences: List[str], overlap_tokens: int) -> List[str]:
    """Get last N sentences that fit within overlap token limit.

    Walks backwards through sentences until reaching overlap limit.

    Args:
        sentences: List of sentences
        overlap_tokens: Maximum tokens for overlap

    Returns:
        List[str]: Last sentences that fit in overlap
    """
    if not sentences or overlap_tokens == 0:
        return []

    overlap = []
    token_count = 0

    # Walk backwards
    for sentence in reversed(sentences):
        sentence_tokens = count_tokens(sentence)

        if token_count + sentence_tokens > overlap_tokens:
            break

        overlap.insert(0, sentence)
        token_count += sentence_tokens

    return overlap


def estimate_timestamp_range(
    chunk_start_pos: int,
    chunk_end_pos: int,
    total_text_length: int,
    total_duration_seconds: int,
) -> Tuple[str, str]:
    """Estimate timestamp range for a chunk based on character positions.

    Uses linear interpolation to estimate timestamps from character positions.
    Assumes even distribution of content over time (reasonable for transcripts).

    Args:
        chunk_start_pos: Starting character position in full text
        chunk_end_pos: Ending character position in full text
        total_text_length: Total characters in full text
        total_duration_seconds: Total duration of video in seconds

    Returns:
        Tuple[str, str]: (start_time, end_time) as HH:MM:SS strings

    Examples:
        >>> estimate_timestamp_range(0, 5000, 10000, 600)
        ('00:00:00', '00:05:00')  # First half of 10-minute video
    """
    # Calculate proportional timestamps
    start_seconds = int((chunk_start_pos / total_text_length) * total_duration_seconds)
    end_seconds = int((chunk_end_pos / total_text_length) * total_duration_seconds)

    # Format as HH:MM:SS
    start_time = _seconds_to_timestamp(start_seconds)
    end_time = _seconds_to_timestamp(end_seconds)

    return (start_time, end_time)


def _seconds_to_timestamp(seconds: int) -> str:
    """Convert seconds to HH:MM:SS format.

    Args:
        seconds: Total seconds

    Returns:
        str: Formatted timestamp

    Examples:
        >>> _seconds_to_timestamp(90)
        '00:01:30'
        >>> _seconds_to_timestamp(3661)
        '01:01:01'
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
