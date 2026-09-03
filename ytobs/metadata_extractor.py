"""Phase 1 metadata extraction using Fabric patterns.

This module handles global context extraction before chunking. It runs
Fabric patterns on the full transcript (or representative sample) to
extract metadata that will be injected into all chunks.

Phase 1 extracts:
- Global summary (1-2 sentences)
- Main theme/idea
- Key topics/entities
"""

from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from .config import Config, ModelConfig, resolve_model, resolve_model_config
from .rate_limiter import (
    RateLimitHandler,
    RetryConfig,
    ModelHandle,
    parse_thinking_tags,
    validate_request_size,
)


@dataclass
class GlobalMetadata:
    """Global context metadata extracted from full transcript.

    Attributes:
        summary: 1-2 sentence overview of content
        theme: Main theme or core idea
        topics: Comma-separated key topics/entities
        extraction_successful: Whether all patterns succeeded
        errors: Dict of pattern_name -> error_message for failures
    """

    summary: str
    theme: str
    topics: str
    extraction_successful: bool = True
    errors: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = {}


class MetadataExtractor:
    """Extracts global metadata using Fabric patterns."""

    # Default patterns for metadata extraction
    DEFAULT_PATTERNS = {
        "summary": "create_micro_summary",
        "theme": "extract_main_idea",
        "topics": "extract_patterns",
    }

    def __init__(
        self,
        fabric_command: str = "fabric",
        timeout: int = 60,
        patterns: Optional[Dict[str, str]] = None,
        model_config: Optional[ModelConfig] = None,
        config: Optional[Config] = None,
    ):
        """Initialize metadata extractor.

        Args:
            fabric_command: Command to run Fabric (default: "fabric")
            timeout: Timeout in seconds per pattern (default: 60)
            patterns: Custom pattern mapping (default: use DEFAULT_PATTERNS)
            model_config: ModelConfig for the primary model
            config: Config object with model registry for fallbacks
        """
        self.fabric_command = fabric_command
        self.timeout = timeout
        self.patterns = patterns or self.DEFAULT_PATTERNS.copy()
        self.config = config or Config()
        self.model_config = model_config or resolve_model_config(
            resolve_model(self.config.model, self.config), self.config
        )

        primary = ModelHandle.from_config(self.model_config, fabric_command)
        fallback_aliases = ["fast", "quality", "compound"]
        fallbacks = [
            ModelHandle.from_config(
                resolve_model_config(alias, self.config), fabric_command
            )
            for alias in fallback_aliases
            if alias != resolve_model(self.config.model, self.config)
        ]

        self.rate_limiter = RateLimitHandler(
            models=[primary] + fallbacks,
            retry_config=RetryConfig(
                max_retries=3, base_delay=2.0, max_delay=30.0, exponential_base=2.0
            ),
        )

    def extract(
        self, transcript: str, video_title: str, save_dir: Optional[Path] = None
    ) -> GlobalMetadata:
        """Extract global metadata from transcript.

        Runs configured Fabric patterns to extract:
        - summary: Brief 1-2 sentence overview
        - theme: Main theme or idea
        - topics: Key topics/entities mentioned

        For long transcripts (>10K words), uses a representative sample
        (first 2K + last 500 words) to stay within token limits.

        Args:
            transcript: Full transcript text
            video_title: Video title (used for fallback)
            save_dir: Optional directory to save intermediate outputs

        Returns:
            GlobalMetadata: Extracted metadata with fallbacks on failure
        """
        print("📊 Extracting global metadata...")

        # For very long transcripts, use representative sample for Phase 1
        # Pattern extraction doesn't need full transcript, just enough context
        words = transcript.split()
        word_count = len(words)

        if word_count > 30000:
            sample_transcript = " ".join(words[:5000] + ["..."] + words[-1000:])
            print(
                f"  ℹ️  Using sample ({word_count} words → {len(sample_transcript.split())} words)"
            )
        else:
            sample_transcript = transcript

        results = {}
        errors = {}

        # Extract summary
        print("  Running: create_micro_summary")
        summary_result = self._run_pattern(
            self.patterns["summary"],
            sample_transcript,
            save_dir / "global_summary.txt" if save_dir else None,
        )

        if summary_result["success"]:
            results["summary"] = self._parse_summary(summary_result["output"])
        else:
            errors["summary"] = summary_result["error"]
            results["summary"] = f"Video titled '{video_title}'"

        # Extract theme
        print("  Running: extract_main_idea")
        theme_result = self._run_pattern(
            self.patterns["theme"],
            sample_transcript,
            save_dir / "global_theme.txt" if save_dir else None,
        )

        if theme_result["success"]:
            results["theme"] = self._parse_theme(theme_result["output"])
        else:
            errors["theme"] = theme_result["error"]
            results["theme"] = "Content analysis"

        # Extract topics
        print("  Running: extract_patterns")
        topics_result = self._run_pattern(
            self.patterns["topics"],
            sample_transcript,
            save_dir / "global_topics.txt" if save_dir else None,
        )

        if topics_result["success"]:
            results["topics"] = self._parse_topics(topics_result["output"])
        else:
            errors["topics"] = topics_result["error"]
            results["topics"] = self._extract_topics_from_title(video_title)

        extraction_successful = len(errors) == 0

        if errors:
            print(f"  ⚠️  {len(errors)} pattern(s) failed, using fallbacks")
            # Show errors in debug mode or first error as hint
            if errors:
                first_error = list(errors.values())[0]
                if "too large" in first_error.lower():
                    print(
                        f"      Hint: Transcript may be too long for Phase 1 patterns"
                    )
                    print(
                        f"      Consider implementing transcript truncation for Phase 1"
                    )
        else:
            print("  ✅ Metadata extraction complete")

        return GlobalMetadata(
            summary=results["summary"],
            theme=results["theme"],
            topics=results["topics"],
            extraction_successful=extraction_successful,
            errors=errors,
        )

    def _run_pattern(
        self, pattern: str, input_text: str, save_path: Optional[Path] = None
    ) -> Dict:
        """Run a single Fabric pattern with rate limit handling and retry logic.

        Args:
            pattern: Pattern name (e.g., "create_micro_summary")
            input_text: Input text to process
            save_path: Optional path to save output

        Returns:
            Dict with keys:
                - success: bool
                - output: str (if success)
                - error: str (if failure)
        """
        # Validate request size against primary model context
        is_valid, error = validate_request_size(
            input_text, max_tokens=self.model_config.context_window
        )
        if not is_valid:
            return {"success": False, "error": error}

        # Use rate limit handler with automatic retry on 429 errors
        result = self.rate_limiter.run_pattern(
            pattern=pattern,
            input_text=input_text,
            timeout=self.timeout,
        )

        if result.success:
            # Parse thinking tags if present
            output = parse_thinking_tags(result.output)

            # Save if requested
            if save_path:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_text(output)

            return {"success": True, "output": output}
        else:
            # Include retry count in error message for visibility
            error_msg = result.error
            if result.retries > 0:
                error_msg = f"{error_msg} (after {result.retries} retries)"

            return {"success": False, "error": error_msg}

    def _parse_summary(self, output: str) -> str:
        """Parse summary from create_micro_summary output.

        Extracts the ONE SENTENCE SUMMARY section.
        Falls back to first non-empty line if parsing fails.

        Args:
            output: Raw pattern output

        Returns:
            str: Extracted summary (1-2 sentences)
        """
        lines = output.strip().split("\n")

        # Look for "ONE SENTENCE SUMMARY:" section
        for i, line in enumerate(lines):
            if "ONE SENTENCE SUMMARY" in line.upper():
                # Next line should be the summary
                if i + 1 < len(lines):
                    summary = lines[i + 1].strip()
                    if summary:
                        return summary

        # Fallback: first non-empty, non-header line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and ":" not in line[:30]:
                return line

        return "Content overview"

    def _parse_theme(self, output: str) -> str:
        """Parse theme from extract_main_idea output.

        Extracts the MAIN IDEA section.

        Args:
            output: Raw pattern output

        Returns:
            str: Extracted main theme/idea
        """
        lines = output.strip().split("\n")

        # Look for "MAIN IDEA:" section
        for i, line in enumerate(lines):
            if "MAIN IDEA" in line.upper():
                # Next line should be the idea
                if i + 1 < len(lines):
                    idea = lines[i + 1].strip()
                    if idea:
                        return idea

        # Fallback: first substantial line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 20:
                return line

        return "Content analysis"

    def _parse_topics(self, output: str) -> str:
        """Parse topics from extract_patterns output.

        Looks for comma-separated list of topics/entities.

        Args:
            output: Raw pattern output

        Returns:
            str: Comma-separated topics
        """
        lines = output.strip().split("\n")

        # Look for lines with comma-separated values
        for line in lines:
            line = line.strip()
            # Skip headers and very short lines
            if line.startswith("#") or len(line) < 10:
                continue
            # If line has multiple commas, likely a topic list
            if line.count(",") >= 2:
                return line

        # Fallback: collect first few substantial words
        topics = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Take first few words
                words = line.split()[:3]
                topics.extend(words)
                if len(topics) >= 5:
                    break

        return ", ".join(topics[:5]) if topics else "general topics"

    def _extract_topics_from_title(self, title: str) -> str:
        """Extract basic topics from video title.

        Fallback when topic extraction fails.

        Args:
            title: Video title

        Returns:
            str: Basic topics from title
        """
        # Remove common words and split
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        words = title.lower().split()
        topics = [w for w in words if w not in stop_words and len(w) > 3]

        return ", ".join(topics[:5]) if topics else title


def create_fallback_metadata(video_title: str, video_info: Dict) -> GlobalMetadata:
    """Create fallback metadata when extraction fails completely.

    Uses video title, description, and tags to construct basic metadata.

    Args:
        video_title: Video title
        video_info: Video metadata dict (from yt-dlp)

    Returns:
        GlobalMetadata: Basic metadata constructed from available info
    """
    # Extract topics from tags if available
    tags = video_info.get("tags", [])
    if tags:
        topics = ", ".join(tags[:5])
    else:
        # Fall back to title words
        words = [w for w in video_title.split() if len(w) > 3]
        topics = ", ".join(words[:5])

    return GlobalMetadata(
        summary=f"Video titled '{video_title}'",
        theme="Content overview and analysis",
        topics=topics,
        extraction_successful=False,
        errors={"all": "All metadata extraction patterns failed"},
    )
