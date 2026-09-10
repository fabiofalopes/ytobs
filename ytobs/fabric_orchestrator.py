"""Two-phase Fabric orchestration for YouTube video analysis.

This module coordinates the complete Fabric analysis workflow:

Phase 1: Global metadata extraction (summary, theme, topics)
Phase 2: Process enriched packets through configured Fabric patterns

The orchestrator handles:
- Running Fabric patterns on chunks
- Combining multi-part outputs
- Progress reporting
- Error recovery
- Output organization
- Debug/streaming mode for real-time visibility
"""

import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field

from .metadata_extractor import MetadataExtractor, GlobalMetadata
from .chunker import chunk_transcript
from .packet_builder import EnrichedPacket
from .markdown_utils import format_combined_output
from .config import Config, resolve_model, resolve_model_config
from .rate_limiter import (
    RateLimitHandler,
    RetryConfig,
    ModelHandle,
    parse_thinking_tags,
    validate_request_size,
    estimate_tokens,
)


@dataclass
class PatternResult:
    """Result from processing a single pattern across all chunks.

    Attributes:
        pattern_name: Name of the Fabric pattern used
        success: Whether pattern completed successfully
        outputs: List of outputs (one per chunk)
        error: Error message if failed
        combined_output: Final combined output text
        timing: Processing time in seconds per chunk
        models_used: Deduplicated ordered list of model ids that produced
            the chunks (provenance for the note, W1)
        run_timestamp: ISO timestamp of when the pattern completed (W1)
    """

    pattern_name: str
    success: bool
    outputs: List[str]
    error: Optional[str] = None
    combined_output: str = ""
    timing: List[float] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    run_timestamp: Optional[str] = None


@dataclass
class OrchestrationResult:
    """Complete result from Fabric orchestration.

    Attributes:
        success: Whether overall orchestration succeeded
        metadata: Global metadata extracted in Phase 1
        pattern_results: Dict of pattern_name -> PatternResult
        packets: List of enriched packets created
        errors: List of error messages encountered
    """

    success: bool
    metadata: GlobalMetadata
    pattern_results: Dict[str, PatternResult]
    packets: List[EnrichedPacket]
    errors: List[str]


class FabricOrchestrator:
    """Orchestrates two-phase Fabric analysis workflow."""

    def __init__(
        self,
        fabric_command: str = "fabric",
        patterns: Optional[List[str]] = None,
        join_pattern: Optional[str] = None,
        timeout: int = 120,
        max_chunk_tokens: int = 50000,
        save_dir: Optional[Path] = None,
        debug: bool = False,
        stream: bool = False,
        model: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """Initialize Fabric orchestrator.

        Args:
            fabric_command: Command to run Fabric (default: "fabric")
            patterns: List of Fabric patterns to run (default: ["youtube_summary"])
            join_pattern: Optional pattern to combine chunk outputs (default: None)
            timeout: Timeout per pattern call in seconds (default: 120)
            max_chunk_tokens: Max tokens per chunk (default: 50000)
            save_dir: Optional directory to save intermediate files
            debug: Enable debug mode with detailed output
            stream: Enable streaming mode to see Fabric output in real-time
            model: Optional LLM model override (e.g., "minimax")
            config: Optional Config object with model registry
        """
        self.fabric_command = fabric_command
        self.patterns = patterns or ["youtube_summary"]
        self.join_pattern = join_pattern  # e.g., "join_chunks"
        self.timeout = timeout
        self.max_chunk_tokens = max_chunk_tokens
        self.save_dir = save_dir
        self.debug = debug
        self.stream = stream
        self.config = config or Config()

        # Resolve model alias to ModelConfig
        model_alias = (
            resolve_model(model, self.config)
            if model
            else resolve_model(self.config.model, self.config)
        )
        self.model_config = resolve_model_config(model_alias, self.config)

        # Initialize metadata extractor with same config
        self.metadata_extractor = MetadataExtractor(
            fabric_command=fabric_command,
            timeout=timeout,
            model_config=self.model_config,
            config=self.config,
        )

    def _log(self, msg: str, level: str = "info"):
        """Print message based on debug level."""
        if level == "debug" and not self.debug:
            return

        prefix = {"info": "", "debug": "🔍 ", "stream": "📺 ", "timing": "⏱️  "}.get(
            level, ""
        )

        print(f"{prefix}{msg}", file=sys.stderr if level == "debug" else sys.stdout)

    def orchestrate(
        self,
        transcript: str,
        video_title: str,
        video_duration_seconds: int,
        video_info: Optional[Dict] = None,
    ) -> OrchestrationResult:
        """Run complete two-phase Fabric orchestration.

        Workflow:
        1. Phase 1: Extract global metadata (summary, theme, topics)
        2. Chunk transcript and create enriched packets
        3. Phase 2: Process each packet through each pattern
        4. Combine outputs per pattern
        5. Return organized results

        Args:
            transcript: Full transcript text
            video_title: Video title
            video_duration_seconds: Video duration in seconds
            video_info: Optional video metadata dict (for fallback)

        Returns:
            OrchestrationResult: Complete orchestration results
        """
        errors = []
        start_time = time.time()

        print("\n🎬 Starting Fabric orchestration...")
        print(f"   Patterns: {', '.join(self.patterns)}")

        if self.debug:
            word_count = len(transcript.split())
            self._log(f"Transcript: {word_count} words", "debug")
            self._log(f"Video duration: {video_duration_seconds}s", "debug")
            self._log(f"Max chunk tokens: {self.max_chunk_tokens}", "debug")

        print()

        # Phase 1: Extract global metadata
        print("📊 Phase 1: Extracting global metadata")
        phase1_start = time.time()

        metadata_save_dir = self.save_dir / "metadata" if self.save_dir else None
        metadata = self.metadata_extractor.extract(
            transcript=transcript, video_title=video_title, save_dir=metadata_save_dir
        )

        phase1_time = time.time() - phase1_start

        if self.debug:
            self._log(f"Phase 1 completed in {phase1_time:.1f}s", "timing")
            self._log(f"Summary: {metadata.summary[:100]}...", "debug")
            self._log(f"Theme: {metadata.theme[:100]}...", "debug")
            self._log(f"Topics: {metadata.topics[:100]}...", "debug")

        # Note: Phase 1 fallbacks work well, so partial failures don't affect overall success
        # Only log in debug mode - fallbacks produce valid enrichment context
        if not metadata.extraction_successful and self.debug and metadata.errors:
            self._log(
                f"Phase 1 used fallbacks for: {', '.join(metadata.errors.keys())}",
                "debug",
            )

        print()

        # Chunking phase
        print("✂️  Chunking and enriching transcript")
        chunk_start = time.time()

        packets = chunk_transcript(
            transcript=transcript,
            video_title=video_title,
            video_duration_seconds=video_duration_seconds,
            metadata=metadata,
            max_chunk_tokens=self.max_chunk_tokens,
            save_dir=self.save_dir,
            video_info=video_info,  # V4.0: Pass video_info for VideoContext enrichment
            output_language=getattr(self.config, "output_language", "English"),
        )

        chunk_time = time.time() - chunk_start

        if self.debug:
            self._log(f"Chunking completed in {chunk_time:.1f}s", "timing")
            self._log(f"Created {len(packets)} packets", "debug")
            for i, p in enumerate(packets):
                self._log(
                    f"  Packet {i + 1}: {p.position}, {p.token_count} tokens, {p.timestamp_range}",
                    "debug",
                )

        print()

        # Phase 2: Process patterns
        print(
            f"🔮 Phase 2: Processing {len(self.patterns)} pattern(s) × {len(packets)} chunk(s)"
        )
        phase2_start = time.time()

        pattern_results = {}

        for pattern in self.patterns:
            print(f"\n   Pattern: {pattern}")
            result = self._process_pattern(pattern, packets)
            pattern_results[pattern] = result

            if self.debug and result.timing:
                avg_time = sum(result.timing) / len(result.timing)
                self._log(f"Pattern avg time: {avg_time:.1f}s per chunk", "timing")

            if not result.success:
                errors.append(f"Pattern '{pattern}' failed: {result.error}")

        phase2_time = time.time() - phase2_start

        print()

        # Save pattern outputs if requested
        if self.save_dir:
            self._save_pattern_outputs(pattern_results)

        total_time = time.time() - start_time
        overall_success = len(errors) == 0

        if overall_success:
            print(f"✅ Fabric orchestration complete")
        else:
            print(f"⚠️  Orchestration completed with {len(errors)} error(s)")

        if self.debug:
            self._log(f"Total time: {total_time:.1f}s", "timing")
            self._log(f"  Phase 1 (metadata): {phase1_time:.1f}s", "timing")
            self._log(f"  Chunking: {chunk_time:.1f}s", "timing")
            self._log(f"  Phase 2 (patterns): {phase2_time:.1f}s", "timing")

        return OrchestrationResult(
            success=overall_success,
            metadata=metadata,
            pattern_results=pattern_results,
            packets=packets,
            errors=errors,
        )

    def _process_pattern(
        self, pattern: str, packets: List[EnrichedPacket]
    ) -> PatternResult:
        """Process all packets through a single pattern.

        Includes inter-chunk delay to avoid rate limits.

        Args:
            pattern: Fabric pattern name
            packets: List of enriched packets

        Returns:
            PatternResult: Results from processing pattern
        """
        outputs = []
        timing = []
        models_used: List[str] = []
        total = len(packets)

        inter_chunk_delay = 0

        for i, packet in enumerate(packets, 1):
            print(f"      Chunk {i}/{total}...", end=" ", flush=True)

            if self.debug:
                est_tokens = estimate_tokens(packet.to_fabric_input())
                self._log(f"\n      Input tokens: ~{est_tokens}", "debug")

            # Get Fabric-ready input
            fabric_input = packet.to_fabric_input()

            # Run pattern (with or without streaming)
            chunk_start = time.time()

            if self.stream:
                result = self._run_fabric_pattern_streaming(
                    pattern, fabric_input, i, total
                )
            else:
                result = self._run_fabric_pattern(pattern, fabric_input)

            chunk_time = time.time() - chunk_start
            timing.append(chunk_time)

            if result["success"]:
                outputs.append(result["output"])
                # Track model provenance (W1): deduped, insertion-ordered
                model_used = result.get("model_used")
                if model_used and model_used not in models_used:
                    models_used.append(model_used)
                output_len = len(result["output"])
                if not self.stream:
                    print(f"✓ ({chunk_time:.1f}s, {output_len} chars)")

                # Add delay between chunks to avoid rate limits
                if i < total and inter_chunk_delay > 0:
                    if self.debug:
                        self._log(
                            f"Waiting {inter_chunk_delay}s before next chunk...",
                            "debug",
                        )
                    time.sleep(inter_chunk_delay)
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"✗ ({error_msg})")
                return PatternResult(
                    pattern_name=pattern,
                    success=False,
                    outputs=outputs,
                    error=f"Chunk {i} failed: {error_msg}",
                    timing=timing,
                    models_used=models_used,
                )

        # Combine outputs
        print(f"      Combining {len(outputs)} outputs...")
        combined = self._combine_outputs(pattern, outputs, packets)

        return PatternResult(
            pattern_name=pattern,
            success=True,
            outputs=outputs,
            combined_output=combined,
            timing=timing,
            models_used=models_used,
            run_timestamp=datetime.now().isoformat(timespec="seconds"),
        )

    def _run_fabric_pattern(self, pattern: str, input_text: str) -> Dict:
        """Run a single Fabric pattern with rate limit handling.

        Args:
            pattern: Pattern name
            input_text: Input text (enriched packet)

        Returns:
            Dict with keys:
                - success: bool
                - output: str (if success)
                - model_used: str (model id that produced the output, if success)
                - error: str (if failure)
        """
        # Validate request size against primary model context
        is_valid, error = validate_request_size(
            input_text, max_tokens=self.model_config.context_window
        )
        if not is_valid:
            return {"success": False, "error": error}

        primary = ModelHandle.from_config(self.model_config, self.fabric_command)
        primary_alias = resolve_model(self.config.model, self.config)
        fallbacks = [
            ModelHandle.from_config(
                resolve_model_config(alias, self.config), self.fabric_command
            )
            for alias in getattr(self.config, "fallback_models", [])
            if alias != primary_alias and alias in self.config.models
        ]

        handler = RateLimitHandler(
            models=[primary] + fallbacks,
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0,
                exponential_base=2.0,
            ),
        )

        result = handler.run_pattern(
            pattern=pattern,
            input_text=input_text,
            timeout=self.timeout,
        )

        if result.success:
            # Parse thinking tags if present
            output = parse_thinking_tags(result.output)

            # Show which model was used if debugging and not primary
            if (
                self.debug
                and result.model_used
                and result.model_used != self.model_config.model_id
            ):
                model_name = (
                    result.model_used.split("/")[-1]
                    if "/" in result.model_used
                    else result.model_used
                )
                print(f"        (used fallback model: {model_name})")

            return {
                "success": True,
                "output": output,
                "model_used": result.model_used,
            }
        else:
            # Include retry count and model info in error message for visibility
            error_msg = result.error
            if result.retries > 0:
                error_msg = f"{error_msg} (after {result.retries} retries)"
            if result.model_used:
                model_name = (
                    result.model_used.split("/")[-1]
                    if "/" in result.model_used
                    else result.model_used
                )
                error_msg = f"{error_msg} [model: {model_name}]"
            return {"success": False, "error": error_msg}

    def _run_fabric_pattern_streaming(
        self, pattern: str, input_text: str, chunk_num: int, total_chunks: int
    ) -> Dict:
        """Run Fabric pattern with streaming output visible in terminal.

        Note: Streaming mode uses direct subprocess for real-time output.
        Retry logic is handled at a higher level by calling _run_fabric_pattern
        on failure.

        Args:
            pattern: Pattern name
            input_text: Input text (enriched packet)
            chunk_num: Current chunk number
            total_chunks: Total number of chunks

        Returns:
            Dict with keys:
                - success: bool
                - output: str (if success)
                - model_used: str (best-effort: the configured model id,
                  since streaming doesn't report which model served it)
                - error: str (if failure)
        """
        # Validate request size against primary model context
        is_valid, error = validate_request_size(
            input_text, max_tokens=self.model_config.context_window
        )
        if not is_valid:
            return {"success": False, "error": error}

        cmd = [self.fabric_command, "-p", pattern, "-s"]  # -s for streaming

        # Add model if specified
        if self.model_config.model_id:
            cmd.extend(["-m", self.model_config.model_id])

        print()  # New line before streaming output
        print(f"      {'─' * 60}")
        print(f"      📺 STREAMING: {pattern} (chunk {chunk_num}/{total_chunks})")
        print(f"      {'─' * 60}")

        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            def _kill_on_timeout():
                if process and process.poll() is None:
                    process.kill()

            timer = threading.Timer(self.timeout, _kill_on_timeout)
            timer.start()

            try:
                if process.stdin:
                    process.stdin.write(input_text)
                    process.stdin.close()

                output_lines = []
                if process.stdout:
                    for line in process.stdout:
                        print(f"      │ {line}", end="")
                        output_lines.append(line)

                process.wait(timeout=self.timeout)
            finally:
                timer.cancel()

            print(f"      {'─' * 60}")

            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                # Check if it's a rate limit error
                if "429" in stderr or "rate limit" in stderr.lower():
                    print(f"      ⚠️  Rate limit hit in streaming mode")
                    # Fall back to non-streaming with retry logic
                    print(f"      🔄 Retrying with rate limit handling...")
                    return self._run_fabric_pattern(pattern, input_text)

                return {
                    "success": False,
                    "error": f"Exit code {process.returncode}: {stderr[:100]}",
                }

            output = "".join(output_lines).strip()
            print(f"      ✓ Chunk {chunk_num} complete ({len(output)} chars)")

            return {
                "success": True,
                "output": output,
                "model_used": self.model_config.model_id,
            }

        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            return {"success": False, "error": f"Timeout ({self.timeout}s)"}

        except FileNotFoundError:
            return {"success": False, "error": "fabric not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _combine_outputs(
        self, pattern: str, outputs: List[str], packets: List[EnrichedPacket]
    ) -> str:
        """Combine multiple outputs from chunked processing.

        If single chunk, format and return.
        If multiple chunks:
          1. If join_pattern is set, run it on combined outputs
          2. Otherwise, concatenate and format

        The formatting pipeline:
        1. Combine all chunk outputs
        2. Optionally run join_pattern on combined
        3. Normalize heading levels (so H1 becomes H4 in final note)
        4. Clean up duplicate headings, excessive --- rules
        5. Remove chunk markers (Part 1/10, timestamps)

        Args:
            pattern: Pattern name
            outputs: List of pattern outputs (one per chunk)
            packets: List of enriched packets (for metadata)

        Returns:
            str: Combined and formatted output text
        """
        if len(outputs) == 1:
            # Single chunk - just normalize headings
            return format_combined_output(
                outputs[0],
                base_heading_level=4,  # Start at #### within AI Analysis section
                keep_chunk_markers=False,
                clean_rules=True,
            )

        # Multi-part output: first combine raw with separators
        combined_parts = []

        for i, (output, packet) in enumerate(zip(outputs, packets), 1):
            start_time, end_time = packet.timestamp_range
            combined_parts.append(f"## Part {i}/{len(outputs)}")
            combined_parts.append(f"*Timestamp: {start_time} - {end_time}*")
            combined_parts.append("")
            combined_parts.append(output)
            combined_parts.append("")
            combined_parts.append("---")
            combined_parts.append("")

        raw_combined = "\n".join(combined_parts)

        # If join_pattern is configured, run it on combined outputs
        final_output = raw_combined
        if self.join_pattern and len(outputs) > 1:
            print(
                f"      🔗 Joining {len(outputs)} chunks with '{self.join_pattern}' pattern..."
            )

            join_result = self._run_fabric_pattern(self.join_pattern, raw_combined)

            if join_result["success"]:
                final_output = join_result["output"]
                if self.debug:
                    self._log(
                        f"Join pattern produced {len(final_output)} chars", "debug"
                    )
            else:
                # Fall back to simple concatenation if join fails
                error_msg = join_result.get("error", "Unknown error")
                print(f"      ⚠️  Join pattern failed: {error_msg}, using concatenation")

        # Apply formatting pipeline
        formatted = format_combined_output(
            final_output,
            base_heading_level=4,  # Start at #### within AI Analysis section
            keep_chunk_markers=False,  # Remove Part X/Y markers for cleaner note
            clean_rules=True,
        )

        return formatted

    def _save_pattern_outputs(self, pattern_results: Dict[str, PatternResult]):
        """Save pattern outputs to disk.

        Creates structure:
        .fabric/{video_id}/outputs/{pattern_name}/
            combined.md         # Final formatted output (goes into note)
            combined_raw.md     # Raw output with chunk markers (for debugging)
            chunk_001.md        # Individual chunk outputs
            chunk_002.md
            ...

        Args:
            pattern_results: Dict of pattern_name -> PatternResult
        """
        if not self.save_dir:
            return

        outputs_dir = self.save_dir / "outputs"

        for pattern_name, result in pattern_results.items():
            if not result.success:
                continue

            pattern_dir = outputs_dir / pattern_name
            pattern_dir.mkdir(parents=True, exist_ok=True)

            # Save combined output (formatted)
            combined_path = pattern_dir / "combined.md"
            combined_path.write_text(result.combined_output)

            # Save raw combined output (with chunk markers) if multiple chunks
            if len(result.outputs) > 1:
                raw_parts = []
                for i, output in enumerate(result.outputs, 1):
                    raw_parts.append(f"## Part {i}/{len(result.outputs)}")
                    raw_parts.append("")
                    raw_parts.append(output)
                    raw_parts.append("")
                    raw_parts.append("---")
                    raw_parts.append("")

                raw_combined_path = pattern_dir / "combined_raw.md"
                raw_combined_path.write_text("\n".join(raw_parts))

            # Save individual chunk outputs
            for i, output in enumerate(result.outputs, 1):
                chunk_path = pattern_dir / f"chunk_{i:03d}.md"
                chunk_path.write_text(output)

        print(f"   💾 Pattern outputs saved to {outputs_dir}")


def orchestrate_fabric_analysis(
    transcript: str,
    video_title: str,
    video_duration_seconds: int,
    patterns: Optional[List[str]] = None,
    join_pattern: Optional[str] = None,
    fabric_command: str = "fabric",
    max_chunk_tokens: int = 50000,
    save_dir: Optional[Path] = None,
    debug: bool = False,
    stream: bool = False,
    model: Optional[str] = None,
    video_info: Optional[Dict] = None,
    config: Optional[Config] = None,
) -> OrchestrationResult:
    """Convenience function for Fabric orchestration.

    Args:
        transcript: Full transcript text
        video_title: Video title
        video_duration_seconds: Video duration in seconds
        patterns: List of Fabric patterns to run
        join_pattern: Optional pattern to combine chunk outputs
        fabric_command: Fabric command name
        max_chunk_tokens: Max tokens per chunk
        save_dir: Optional save directory
        debug: Enable debug mode with detailed output
        stream: Enable streaming mode to see Fabric output in real-time
        model: Optional LLM model override (e.g., "minimax")
        video_info: Optional dict from extractor with YouTube metadata (V4.0)
        config: Optional Config object with model registry

    Returns:
        OrchestrationResult: Complete orchestration results
    """
    orchestrator = FabricOrchestrator(
        fabric_command=fabric_command,
        patterns=patterns,
        join_pattern=join_pattern,
        max_chunk_tokens=max_chunk_tokens,
        save_dir=save_dir,
        debug=debug,
        stream=stream,
        model=model,
        config=config,
    )

    return orchestrator.orchestrate(
        transcript=transcript,
        video_title=video_title,
        video_duration_seconds=video_duration_seconds,
        video_info=video_info,  # V4.0: Pass video_info for VideoContext enrichment
    )
