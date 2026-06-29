"""High-level transcript chunking with enriched packet creation.

This module orchestrates the chunking process:
1. Analyze transcript and determine optimal chunk sizes
2. Split transcript into chunks respecting sentence boundaries
3. Create enriched packets with global metadata
4. Estimate timestamps for each chunk
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from . import token_counter
from .packet_builder import create_packet, EnrichedPacket, VideoContext
from .metadata_extractor import GlobalMetadata


class TranscriptChunker:
    """Orchestrates transcript chunking and enriched packet creation."""

    def __init__(self, max_chunk_tokens: int = 50000, overlap_tokens: int = 500):
        """Initialize chunker.

        Args:
            max_chunk_tokens: Maximum tokens per chunk (default: 8000)
            overlap_tokens: Overlap between chunks (default: 200)
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_and_enrich(
        self,
        transcript: str,
        video_title: str,
        video_duration_seconds: int,
        metadata: GlobalMetadata,
        save_dir: Optional[Path] = None,
        video_info: Optional[Dict] = None,
    ) -> List[EnrichedPacket]:
        """Chunk transcript and create enriched packets.

        Main workflow:
        1. Count tokens and determine optimal chunk size
        2. Split transcript into chunks
        3. Estimate timestamps for each chunk
        4. Create enriched packets with metadata
        5. Optionally save chunks and metadata to disk

        Args:
            transcript: Full transcript text
            video_title: Video title
            video_duration_seconds: Total video duration in seconds
            metadata: Global metadata from Phase 1
            save_dir: Optional directory to save chunks
            video_info: Optional dict from extractor with YouTube metadata (V4.0)

        Returns:
            List[EnrichedPacket]: Enriched packets ready for Fabric processing
        """
        print("✂️  Chunking transcript...")

        # Create VideoContext if video_info provided (V4.0)
        video_context = None
        if video_info:
            video_context = VideoContext.from_video_info(video_info)
            print(
                f"   📺 Video context: {video_context.channel_name} | {len(video_context.tags)} tags"
            )

        # Step 1: Analyze transcript
        total_tokens = token_counter.count_tokens(transcript)
        total_length = len(transcript)

        print(
            f"   Transcript: {len(transcript.split())} words, {total_tokens:,} tokens"
        )

        # Step 2: Determine if chunking is needed
        if total_tokens <= self.max_chunk_tokens:
            print("   ✅ Single chunk (no splitting needed)")
            packets = self._create_single_packet(
                transcript,
                video_title,
                video_duration_seconds,
                metadata,
                total_tokens,
                video_context=video_context,
            )
        else:
            # Calculate optimal chunk size
            optimal_size = token_counter.calculate_optimal_chunk_size(
                total_tokens, self.max_chunk_tokens
            )

            num_chunks_estimate = (total_tokens + optimal_size - 1) // optimal_size
            print(
                f"   📊 Optimal chunk size: {optimal_size:,} tokens ({num_chunks_estimate} chunks)"
            )

            # Step 3: Split into chunks
            chunks = token_counter.chunk_text_by_sentences(
                transcript, max_tokens=optimal_size, overlap_tokens=self.overlap_tokens
            )

            print(f"   ✅ Created {len(chunks)} chunks")

            # Step 4: Estimate timestamps
            for chunk in chunks:
                chunk["timestamp_range"] = token_counter.estimate_timestamp_range(
                    chunk["start_pos"],
                    chunk["end_pos"],
                    total_length,
                    video_duration_seconds,
                )

            # Step 5: Create enriched packets
            packets = self._create_packets_from_chunks(
                chunks, video_title, metadata, video_context=video_context
            )

        # Step 6: Save if requested
        if save_dir:
            self._save_chunks(packets, save_dir)

        return packets

    def _create_single_packet(
        self,
        transcript: str,
        video_title: str,
        video_duration_seconds: int,
        metadata: GlobalMetadata,
        token_count: int,
        video_context: Optional[VideoContext] = None,
    ) -> List[EnrichedPacket]:
        """Create a single enriched packet (no chunking needed).

        Args:
            transcript: Full transcript
            video_title: Video title
            video_duration_seconds: Video duration
            metadata: Global metadata
            token_count: Pre-calculated token count
            video_context: Optional VideoContext with YouTube metadata (V4.0)

        Returns:
            List with single EnrichedPacket
        """

        packet = create_packet(
            video_title=video_title,
            video_summary=metadata.summary,
            key_topics=metadata.topics,
            chunk_id="chunk_001",
            chunk_index=0,
            total_chunks=1,
            timestamp_range=(
                "00:00:00",
                token_counter._seconds_to_timestamp(video_duration_seconds),
            ),
            transcript_segment=transcript,
            token_count=token_count,
            video_context=video_context,
        )

        return [packet]

    def _create_packets_from_chunks(
        self,
        chunks: List[Dict],
        video_title: str,
        metadata: GlobalMetadata,
        video_context: Optional[VideoContext] = None,
    ) -> List[EnrichedPacket]:
        """Create enriched packets from chunks.

        Args:
            chunks: List of chunk dicts from token_counter
            video_title: Video title
            metadata: Global metadata
            video_context: Optional VideoContext with YouTube metadata (V4.0)

        Returns:
            List[EnrichedPacket]: Enriched packets
        """
        packets = []
        total_chunks = len(chunks)

        for chunk in chunks:
            packet = create_packet(
                video_title=video_title,
                video_summary=metadata.summary,
                key_topics=metadata.topics,
                chunk_id=chunk["id"],
                chunk_index=chunk["index"],
                total_chunks=total_chunks,
                timestamp_range=chunk["timestamp_range"],
                transcript_segment=chunk["text"],
                token_count=chunk["token_count"],
                video_context=video_context,
            )
            packets.append(packet)

        return packets

    def _save_chunks(self, packets: List[EnrichedPacket], save_dir: Path):
        """Save enriched packets to disk.

        Args:
            packets: List of enriched packets
            save_dir: Directory to save to (will create packets/ subdir)
        """
        packets_dir = save_dir / "packets"
        packets_dir.mkdir(parents=True, exist_ok=True)

        # Save each packet as markdown
        for packet in packets:
            packet_path = packets_dir / f"{packet.chunk_id}.md"
            fabric_input = packet.to_fabric_input()
            packet_path.write_text(fabric_input)

        # Save metadata summary
        metadata_json = {
            "video_title": packets[0].video_title,
            "total_chunks": len(packets),
            "chunks": [
                {
                    "id": p.chunk_id,
                    "index": p.chunk_index,
                    "position": p.position,
                    "token_count": p.token_count,
                    "timestamp_range": list(p.timestamp_range),
                }
                for p in packets
            ],
        }

        metadata_path = packets_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata_json, indent=2))

        print(f"   💾 Saved {len(packets)} packets to {packets_dir}")


def chunk_transcript(
    transcript: str,
    video_title: str,
    video_duration_seconds: int,
    metadata: GlobalMetadata,
    max_chunk_tokens: int = 50000,
    overlap_tokens: int = 500,
    save_dir: Optional[Path] = None,
    video_info: Optional[Dict] = None,
) -> List[EnrichedPacket]:
    """Convenience function for transcript chunking.

    Args:
        transcript: Full transcript text
        video_title: Video title
        video_duration_seconds: Video duration in seconds
        metadata: Global metadata from Phase 1
        max_chunk_tokens: Max tokens per chunk (default: 8000)
        overlap_tokens: Overlap between chunks (default: 200)
        save_dir: Optional save directory
        video_info: Optional dict from extractor with YouTube metadata (V4.0)

    Returns:
        List[EnrichedPacket]: Enriched packets ready for processing
    """
    chunker = TranscriptChunker(
        max_chunk_tokens=max_chunk_tokens, overlap_tokens=overlap_tokens
    )

    return chunker.chunk_and_enrich(
        transcript=transcript,
        video_title=video_title,
        video_duration_seconds=video_duration_seconds,
        metadata=metadata,
        save_dir=save_dir,
        video_info=video_info,
    )
