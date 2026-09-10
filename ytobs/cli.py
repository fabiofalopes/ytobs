#!/usr/bin/env python3
"""
ytobs - YouTube to Obsidian

Simple command to extract YouTube videos and generate AI-enhanced Obsidian notes.

Usage:
    ytobs URL                   # Smart analysis (recommended)
    ytobs --quick URL           # Fast: 5 essential patterns
    ytobs --deep URL            # Complete: all patterns
    ytobs --preview URL         # Show recommendations only
    ytobs status VIDEO          # Show status of processed video
    ytobs vault                 # Show vault statistics
    ytobs channel URL           # Process entire channel
    ytobs retro --dry-run       # Backfill patterns on existing notes
    ytobs dedupe                # Detect duplicate notes
    ytobs --help                # Show all options

Examples:
    ytobs "https://youtube.com/watch?v=XYZ"
    ytobs --quick "https://youtube.com/watch?v=XYZ"
    ytobs --no-refine "https://youtube.com/watch?v=XYZ"
    ytobs status jNQXAC9IVRw
    ytobs vault
    ytobs channel "https://www.youtube.com/@channelname" --limit 10

Configuration:
    Edit ~/.yt-obsidian/config.yml to customize defaults
"""

import re
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import package modules
from ytobs.config import (
    Config,
    load_config,
    resolve_model,
    resolve_model_config,
    resolve_output_dir,
    get_config_path,
    get_cache_dir,
    create_default_config,
)
from ytobs.validator import validate_url
from ytobs.extractor import extract_metadata
from ytobs.fabric_orchestrator import orchestrate_fabric_analysis, FabricOrchestrator
from ytobs.cache_manager import CacheManager, CacheEntry
from ytobs.incremental_writer import append_patterns_to_note
from ytobs.status_display import display_video_status, display_status_compact
from ytobs.channel import (
    is_channel_url,
    fetch_channel_videos,
    get_channel_info,
    list_videos_table,
    export_videos_json,
    ChannelVideo,
)
from ytobs.formatter import generate_frontmatter, generate_markdown
from ytobs.frontmatter_editor import atomic_write_note
from ytobs.packet_builder import VideoContext
from ytobs.transcript_refiner import refine_transcript
from ytobs.rate_limiter import ModelHandle
from ytobs.filesystem import save_markdown


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for ytobs command."""
    parser = argparse.ArgumentParser(
        prog="ytobs",
        description="Extract YouTube videos to Obsidian notes with AI analysis",
        epilog="Config: ~/.yt-obsidian/config.yml (edit to customize defaults)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands", required=False)

    # Status command: ytobs status VIDEO_ID
    status_parser = subparsers.add_parser(
        "status", help="Show status of a processed video"
    )
    status_parser.add_argument("video", help="Video ID or URL")
    status_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show processing history",
    )

    # Vault command: ytobs vault
    vault_parser = subparsers.add_parser("vault", help="Show vault statistics")
    vault_parser.add_argument(
        "--channels",
        action="store_true",
        help="Group by channel",
    )

    # Channel command: ytobs channel URL
    channel_parser = subparsers.add_parser(
        "channel", help="Process entire YouTube channels"
    )
    channel_parser.add_argument("url", help="Channel URL")
    channel_parser.add_argument(
        "-l", "--limit", type=int, metavar="N", help="Process only N videos"
    )
    channel_parser.add_argument(
        "-s", "--skip", type=int, default=0, metavar="N", help="Skip first N videos"
    )
    channel_parser.add_argument(
        "-n", "--newest", action="store_true", help="Process newest videos first"
    )
    channel_parser.add_argument(
        "-o",
        "--oldest",
        action="store_true",
        help="Process oldest videos first (default)",
    )
    channel_parser.add_argument(
        "--list-only", action="store_true", help="List videos without processing"
    )
    channel_parser.add_argument(
        "--export", type=Path, metavar="FILE", help="Export video list to JSON file"
    )
    channel_parser.add_argument(
        "-i", "--interactive", action="store_true", help="Select videos interactively"
    )
    channel_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be processed"
    )
    channel_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Detailed output"
    )

    # Retro command: ytobs retro (Wave 3 — backfill patterns on existing notes)
    retro_parser = subparsers.add_parser(
        "retro",
        help="Backfill missing patterns on existing notes",
    )
    retro_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without writing",
    )
    retro_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=5,
        metavar="N",
        help="Max notes to process (default: 5)",
    )
    retro_parser.add_argument(
        "-p",
        "--patterns",
        nargs="+",
        default=["extract_wisdom", "summarize"],
        metavar="PATTERN",
        help="Patterns to backfill (default: extract_wisdom summarize)",
    )
    retro_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run patterns even if already present",
    )
    retro_parser.add_argument(
        "--model",
        metavar="ALIAS",
        help="Model alias override (e.g., best, fast, quality)",
    )

    # Dedupe command: ytobs dedupe (Wave 3 — duplicate note detection)
    dedupe_parser = subparsers.add_parser(
        "dedupe", help="Detect and mark duplicate notes"
    )
    dedupe_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply duplicate_of marking (default: report only)",
    )
    dedupe_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max notes to scan (default: all)",
    )

    # Patterns command: ytobs patterns (Sprint 2 — pattern discovery)
    patterns_parser = subparsers.add_parser(
        "patterns", help="Discover available fabric patterns"
    )
    patterns_parser.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "search", "describe", "suggest"],
        help="Discovery action (default: list)",
    )
    patterns_parser.add_argument(
        "query",
        nargs="?",
        default=None,
        metavar="ARG",
        help="Search query (search) / pattern name (describe) / content type (suggest)",
    )
    patterns_parser.add_argument(
        "--content-type",
        dest="content_type",
        default=None,
        metavar="TYPE",
        help="Content type for suggest (video, podcast, tutorial, talk, interview, news)",
    )

    doctor_parser = subparsers.add_parser(
        "doctor", help="Pipeline health check (start every failure session here)"
    )
    doctor_parser.add_argument(
        "--model",
        default=None,
        metavar="ALIAS",
        help="Smoke-test this model instead of the configured primary",
    )
    doctor_parser.add_argument(
        "--full",
        action="store_true",
        help="Also smoke-test fabric-provider models (slower)",
    )

    # Mode shortcuts
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--quick",
        action="store_true",
        help="Fast analysis (5 essential patterns, ~25s)",
    )
    mode_group.add_argument(
        "--deep",
        action="store_true",
        help="Complete analysis (all patterns, ~70s)",
    )
    mode_group.add_argument(
        "--preview",
        action="store_true",
        help="Show pattern recommendations without running",
    )

    # Common overrides
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help="Override model (e.g., minimax, kimi, deepseek, qwen, fast)",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        metavar="PATTERN",
        help="Specific patterns to run (expert mode)",
    )
    parser.add_argument(
        "--max-patterns",
        type=int,
        metavar="N",
        help="Maximum patterns to run (auto mode)",
    )

    # Behavior flags
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument(
        "--no-analysis",
        action="store_true",
        help="Skip AI analysis (metadata and transcript only)",
    )
    parser.add_argument("--config", metavar="PATH", help="Use custom config file")

    # Transcript refinement toggle (W3): --refine / --no-refine; default
    # None falls back to the refinement.enabled config value
    parser.add_argument(
        "--refine",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Refine transcript before analysis (default: config refinement.enabled)",
    )

    # Cache control flags (V3.0)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-analysis (ignore cache)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append new patterns to existing note",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update metadata only (fast, no AI analysis)",
    )
    parser.add_argument(
        "--list-processed",
        action="store_true",
        help="Show all processed videos and exit",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 4.1.0 (Retro, Dedupe, Refinement, Model Provenance)",
    )

    return parser


def run_pattern_optimizer(transcript: str, debug: bool = False) -> Dict[str, Any]:
    """Run pattern_optimizer Fabric pattern to get recommendations.

    Note: Uses first 2000 words of transcript to avoid context limits.
    This is sufficient for content analysis and pattern recommendation.
    """
    if debug:
        print("\n🤖 Running pattern_optimizer to analyze content...")

    # Truncate transcript for pattern analysis (2000 words ≈ 2600 tokens)
    words = transcript.split()
    if len(words) > 2000:
        sample_transcript = " ".join(words[:2000])
        if debug:
            print(
                f"   Truncated transcript: {len(words)} words → 2000 words for analysis"
            )
    else:
        sample_transcript = transcript

    config = load_config()
    model_config = resolve_model_config(resolve_model(config.model, config), config)

    handle = ModelHandle.from_config(model_config, config.fabric_command)
    result = handle.adapter.run_pattern(
        pattern="pattern_optimizer",
        input_text=sample_transcript,
        model_id=model_config.model_id,
        timeout=120,
    )
    if not result.success:
        raise RuntimeError(f"pattern_optimizer failed: {result.error}")

    try:
        recommendations = _parse_optimizer_json(result.output)
        if debug:
            print(
                f"✅ Got {len(recommendations.get('recommended_patterns', []))} pattern recommendations"
            )
        return recommendations
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Could not parse pattern_optimizer output: {e}")


def _parse_optimizer_json(raw: str) -> Dict[str, Any]:
    """Parse pattern_optimizer output, repairing common LLM JSON slips.

    Models occasionally emit a missing comma between members or a trailing
    comma. Repairs run only after a plain parse fails; a corrupted repair
    still fails validation loudly instead of returning wrong data.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    without_trailing = re.sub(r",\s*([}\]])", r"\1", text)
    repaired = re.sub(r'([}\]"\d])(\s*\n\s*)(["{[])', r"\1,\2\3", without_trailing)
    return json.loads(repaired)


def filter_patterns(
    recommendations: Dict[str, Any],
    max_patterns: int,
    min_priority: str,
    debug: bool = False,
) -> List[str]:
    """Filter patterns based on priority and max count.

    Args:
        recommendations: Pattern recommendations from pattern_optimizer
        max_patterns: Maximum number of patterns to return
        min_priority: Minimum priority level (essential, high, medium, optional)
        debug: Enable debug output

    Returns:
        List of pattern names to run
    """
    priority_order = {"essential": 0, "high": 1, "medium": 2, "optional": 3}
    min_priority_level = priority_order.get(min_priority, 2)

    # Filter by priority
    filtered = [
        p
        for p in recommendations.get("recommended_patterns", [])
        if priority_order.get(p.get("priority"), 3) <= min_priority_level
    ]

    # Sort by priority (essential first)
    filtered.sort(key=lambda p: priority_order.get(p.get("priority"), 3))

    # Limit to max_patterns
    filtered = filtered[:max_patterns]

    patterns = [p["pattern"] for p in filtered]

    if debug:
        print(
            f"📋 Selected {len(patterns)} patterns (priority: {min_priority}+, max: {max_patterns})"
        )
        for p in filtered[:5]:
            print(f"   - {p['pattern']} ({p['priority']})")
        if len(patterns) > 5:
            print(f"   ... and {len(patterns) - 5} more")

    return patterns


def show_recommendations(recommendations: Dict[str, Any], selected_patterns: List[str]):
    """Display pattern recommendations in a readable format."""
    print("\n" + "=" * 80)
    print("PATTERN RECOMMENDATIONS")
    print("=" * 80)

    analysis = recommendations.get("content_analysis", {})
    print(f"\n📋 Content Type: {analysis.get('content_type', 'Unknown')}")
    print(f"🎯 Complexity: {analysis.get('complexity', 'Unknown')}")
    print(f"💎 Value: {analysis.get('estimated_value', 'Unknown')}")

    topics = analysis.get("primary_topics", [])
    if topics:
        print(f"\n🔑 Topics: {', '.join(topics[:5])}")

    print(f"\n✅ Selected Patterns ({len(selected_patterns)}):")
    for pattern_info in recommendations.get("recommended_patterns", []):
        pattern = pattern_info.get("pattern")
        if pattern in selected_patterns:
            priority = pattern_info.get("priority", "unknown")
            emoji = {
                "essential": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "optional": "🟢",
            }.get(priority, "⚪")
            print(f"  {emoji} {pattern} ({priority})")

    print(
        f"\n⏱️  Estimated Time: {recommendations.get('estimated_total_time', 'Unknown')}"
    )
    print("=" * 80 + "\n")


def show_concise_help():
    """Show concise help when ytobs is run without arguments."""
    help_text = """ytobs - YouTube to Obsidian

USAGE
  ytobs URL                   Process video (curated mode by default)
  ytobs --quick URL           Fast mode (5 patterns, ~25s)
  ytobs --deep URL            Complete analysis (~70s)
  ytobs --preview URL         Show recommendations only
  ytobs status VIDEO          Show status of processed video
  ytobs vault                 Show vault statistics
  ytobs channel URL           Process entire channel
  ytobs retro --dry-run       Backfill patterns on existing notes
  ytobs dedupe                Detect duplicate notes

COMMON FLAGS
  --model MODEL            Override AI model
  --patterns P1 P2 ...     Run specific patterns
  --force                  Re-analyze (ignore cache)
  --append --patterns ...  Add patterns to existing note
  --refine / --no-refine   Toggle transcript refinement
  -v, --verbose            Detailed output

EXAMPLES
  ytobs "https://youtube.com/watch?v=XYZ"
  ytobs --quick "https://youtu.be/ABC"
  ytobs status jNQXAC9IVRw
  ytobs channel "https://www.youtube.com/@channelname" --limit 10
  ytobs --append --patterns extract_questions "URL"

CONFIG: ~/.yt-obsidian/config.yml
HELP:   ytobs --help (full options)
"""
    print(help_text)


def handle_status_command(args, config: Config) -> int:
    """Handle 'ytobs status VIDEO' command."""
    display_video_status(
        url_or_id=args.video, cache_dir=get_cache_dir(), verbose=args.verbose
    )
    return 0


def handle_vault_command(args, config: Config) -> int:
    """Handle 'ytobs vault' command."""
    cache = CacheManager(get_cache_dir())

    stats = cache.get_statistics()
    videos = cache.list_all()

    print(f"\n  Vault Statistics")
    print(f"  {'=' * 40}")
    print(f"  Total videos: {stats['total_videos']}")
    print(f"  Total patterns: {stats['total_patterns']}")
    print(f"  Total tokens: {stats['total_tokens_used']:,}")
    print(f"  Cache dir: {stats['cache_directory']}")

    if args.channels and videos:
        # Group by channel (if we have that info)
        # For now, just list videos
        print(f"\n  Videos:")
        for video_id, info in videos[:10]:  # Show first 10
            title = info.get("title", "Untitled")
            if len(title) > 45:
                title = title[:42] + "..."
            print(f"    - {title}")
            print(f"      {video_id} ({info.get('patterns_count', 0)} patterns)")

        if len(videos) > 10:
            print(f"\n    ... and {len(videos) - 10} more videos")

    print()
    return 0


def handle_channel_command(args, config: Config) -> int:
    """Handle 'ytobs channel URL' command."""
    channel_url = args.url

    # Get channel info
    print(f"\n📺 Fetching channel info...")
    try:
        channel_info = get_channel_info(channel_url)
        print(f"   Name: {channel_info['name']}")
        print(f"   ID: {channel_info['id']}")
    except Exception as e:
        print(f"   Warning: Could not fetch channel info: {e}")
        channel_info = {"name": "Unknown", "id": "unknown"}

    print()

    # Determine sort order (oldest first uses reverse)
    reverse = args.oldest or not args.newest

    # Fetch videos
    print("⏳ Fetching video list...")
    try:
        videos = fetch_channel_videos(
            channel_url=channel_url,
            order="date",
            limit=args.limit,
            reverse=reverse,
        )
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return 1

    if not videos:
        print("❌ No videos found")
        return 1

    # Apply skip
    if args.skip > 0:
        videos = videos[args.skip :]
        print(f"   Skipped {args.skip} videos")

    print(f"✅ Found {len(videos)} video(s)")
    print()

    # Export mode
    if args.export:
        export_videos_json(videos, args.export)
        print(f"✅ Exported {len(videos)} videos to {args.export}")
        return 0

    # List-only mode
    if args.list_only:
        print(list_videos_table(videos, show_max=100))
        return 0

    # Interactive mode
    if args.interactive:
        print("Select videos to process:")
        print("  Enter numbers/ranges (e.g., 1,3,5-10)")
        print("  'all' for all videos")
        print("  'q' to quit")
        print()

        # Show list
        for i, video in enumerate(videos[:50], 1):
            print(f"{i:3d}. {video.title}")

        if len(videos) > 50:
            print(f"\n... and {len(videos) - 50} more videos")

        print()
        try:
            selection = input("Selection: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled")
            return 0

        if selection.lower() in ("q", "quit", "exit"):
            print("Cancelled")
            return 0

        if selection.lower() == "all":
            selected = videos
        else:
            # Parse selection
            selected = []
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    start_end = part.split("-")
                    if len(start_end) == 2:
                        try:
                            start = int(start_end[0]) if start_end[0] else 1
                            end = int(start_end[1]) if start_end[1] else len(videos)
                            for i in range(start, end + 1):
                                if 1 <= i <= len(videos):
                                    selected.append(videos[i - 1])
                        except ValueError:
                            continue
                else:
                    try:
                        idx = int(part)
                        if 1 <= idx <= len(videos):
                            selected.append(videos[idx - 1])
                    except ValueError:
                        continue

            videos = selected

        if not videos:
            print("No videos selected")
            return 0

        print(f"\nProcessing {len(videos)} selected video(s)")
        print()

    # Process videos
    processed = 0
    failed = 0
    total = len(videos)

    for i, video in enumerate(videos, 1):
        progress = i * 100 // total if total > 0 else 100

        print(f"{'=' * 60}")
        print(f"[{i}/{total}] ({progress}%) {video.title}")
        print(f"   ID: {video.video_id} | Duration: {video.duration or 'N/A'}")
        print(f"   URL: {video.url}")
        print()

        if args.dry_run:
            print("   (dry run - would process this video)")
            print()
            continue

        # Process using existing video processing logic
        try:
            result = subprocess.run(
                ["ytobs", video.url],
                capture_output=False,
                timeout=300,
            )

            if result.returncode == 0:
                print("   ✅ Completed")
            else:
                print("   ❌ Failed")
                failed += 1

        except subprocess.TimeoutExpired:
            print(f"   ❌ Timed out after 300s")
            failed += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

        processed += 1
        print()

    # Summary
    print("=" * 60)
    print("📊 Summary:")
    print(f"   Total:     {total}")
    print(f"   Completed: {processed - failed}")
    print(f"   Failed:    {failed}")
    print()

    return 0 if failed == 0 else 1


def handle_retro_command(args, config: Config) -> int:
    """Handle 'ytobs retro' command (backfill patterns on existing notes).

    The implementation module lands in Wave 3; the lazy import fails
    gracefully until then so the rest of the CLI keeps working.
    """
    try:
        from ytobs.retro import run_retro
    except ImportError:
        print("retro: not implemented yet")
        return 2
    return run_retro(args, config)


def handle_dedupe_command(args, config: Config) -> int:
    """Handle 'ytobs dedupe' command (detect and mark duplicate notes).

    The implementation module lands in Wave 3; the lazy import fails
    gracefully until then so the rest of the CLI keeps working.
    """
    try:
        from ytobs.dedupe import run_dedupe
    except ImportError:
        print("dedupe: not implemented yet")
        return 2
    return run_dedupe(args, config)


def handle_patterns_command(args, config: Config) -> int:
    """Handle 'ytobs patterns' command (fabric pattern discovery)."""
    from ytobs.pattern_discovery import run_patterns

    return run_patterns(args, config)


def main() -> int:
    """Main entry point for ytobs command."""
    # Extract URL manually before argparse to avoid subparser conflicts
    # URL is the first non-flag, non-subcommand argument
    url = None
    url_idx = -1

    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg in [
            "status",
            "vault",
            "channel",
            "retro",
            "dedupe",
            "patterns",
            "doctor",
        ]:
            # This is a subcommand, don't extract URL
            break
        elif arg.startswith("-"):
            # Skip flags
            continue
        elif not url and (arg.startswith("http") or "youtu" in arg):
            # First positional argument that looks like a URL
            # (guards against --patterns VALUES being stolen as the URL)
            url = arg
            url_idx = i
            break

    # Remove URL from argv so argparse doesn't see it
    if url_idx > 0:
        sys.argv.pop(url_idx)

    parser = create_parser()
    args = parser.parse_args()

    # Restore URL to args (only for non-subcommand video URLs)
    # Subcommands like 'status', 'vault', 'channel' handle their own URL arguments
    if args.command not in (
        "status",
        "vault",
        "channel",
        "retro",
        "dedupe",
        "patterns",
        "doctor",
    ):
        args.url = url

    try:
        # Check if config needs to be created (before load_config creates it)
        config_path = get_config_path()
        config_just_created = not config_path.exists()

        # Load configuration
        config = load_config()

        # Show first-run message if config was just created
        if config_just_created:
            create_default_config()
            print(f"  Created default config at {config_path}")
            print(f"   Edit this file to customize behavior\n")

        # Handle subcommands
        if args.command == "status":
            return handle_status_command(args, config)

        if args.command == "channel":
            return handle_channel_command(args, config)

        if args.command == "vault":
            return handle_vault_command(args, config)

        if args.command == "retro":
            return handle_retro_command(args, config)

        if args.command == "dedupe":
            return handle_dedupe_command(args, config)

        if args.command == "patterns":
            return handle_patterns_command(args, config)

        if args.command == "doctor":
            from ytobs.doctor import run_doctor

            return run_doctor(config, model_override=args.model, full=args.full)

        # Determine mode based on flags
        if args.quick:
            mode = "quick"
        elif args.deep:
            mode = "deep"
        elif args.patterns:
            mode = "expert"
        elif args.preview:
            mode = "preview"
        else:
            mode = config.analysis_mode

        # Check if URL is required
        if not args.url and not args.list_processed:
            # Show concise help if no command given
            show_concise_help()
            return 0

        # Handle --list-processed flag
        if args.list_processed:
            cache = CacheManager(get_cache_dir())
            videos = cache.list_all()

            if not videos:
                print("📭 No processed videos found")
                return 0

            print(f"\n📚 Processed Videos ({len(videos)}):\n")
            for video_id, info in videos:
                print(f"  🎬 {info['title']}")
                print(f"     ID: {video_id}")
                print(f"     Note: {info['markdown_path']}")
                print(f"     Patterns: {info['patterns_count']}")
                print(f"     Last: {info['last_processed']}\n")

            stats = cache.get_statistics()
            print(f"📊 Statistics:")
            print(f"   Total videos: {stats['total_videos']}")
            print(f"   Total patterns: {stats['total_patterns']}")
            print(f"   Total tokens: {stats['total_tokens_used']:,}")
            return 0

        # Validate URL
        is_valid, normalized_url, video_id = validate_url(args.url)
        if not is_valid:
            print("❌ Invalid YouTube URL", file=sys.stderr)
            return 1

        # Resolve settings
        model = resolve_model(args.model if args.model else config.model, config)
        output_dir = resolve_output_dir(config)
        verbose = args.verbose or args.debug or config.verbose
        debug = args.debug

        if verbose:
            print(f"🎬 Video ID: {video_id}")
            print(f"📊 Mode: {mode}")
            print(f"🤖 Model: {model}")
            print(f"📁 Output: {output_dir}")

        # Surfaced once when the live config predates the curated default
        if config.analysis_mode != "curated":
            print(
                "💡 Tip: analysis_mode 'curated' (extract_wisdom + summarize only) "
                "is available — edit ~/.yt-obsidian/config.yml"
            )

        print(f"📥 Extracting video: {video_id}")

        # ============================================================
        # PHASE 0: CACHE CHECK (V3.0)
        # ============================================================
        cache = CacheManager(get_cache_dir())

        # Original note path when --force re-processes an existing video
        # (W4): captured BEFORE cache invalidation so the new note can
        # atomically overwrite the original file instead of colliding
        # into a " (2)" duplicate
        force_original_path: Optional[Path] = None

        if cache.exists(video_id):
            cache_entry = cache.get_cache(video_id)

            if args.force:
                # Force re-analysis: invalidate cache
                if verbose:
                    print(f"🔥 FORCE: Ignoring cache, re-running full analysis")
                if cache_entry is not None:
                    force_original_path = Path(cache_entry.markdown_path)
                cache.invalidate(video_id)

            elif args.update:
                # Update metadata only
                print(f"🔄 UPDATING metadata for {video_id}")
                print("   This feature will be implemented in the next iteration")
                print(f"   Existing note: {cache_entry.markdown_path}")
                return 0

            elif args.append:
                # Append new patterns
                if not args.patterns:
                    print(
                        "❌ --append requires --patterns to be specified",
                        file=sys.stderr,
                    )
                    return 1

                existing_patterns = cache_entry.patterns_run
                new_patterns = [p for p in args.patterns if p not in existing_patterns]

                if not new_patterns:
                    print(f"⏭️  All specified patterns already run on this video")
                    print(f"   Existing patterns: {', '.join(existing_patterns)}")
                    return 0

                print(
                    f"📝 APPENDING {len(new_patterns)} new pattern(s) to existing note"
                )
                print(f"   Existing: {len(existing_patterns)} patterns")
                print(f"   New: {', '.join(new_patterns)}")

                # Load transcript from cache or re-extract
                result = extract_metadata(
                    normalized_url,
                    cookies_browser=None,
                    extract_transcript=True,
                    transcript_lang="en",
                )
                transcript = result.get("transcript")

                if not transcript:
                    print(
                        "❌ Cannot append patterns without transcript", file=sys.stderr
                    )
                    return 1

                # Run new patterns only
                orchestrator = FabricOrchestrator(
                    patterns=new_patterns,
                    timeout=config.timeout_per_pattern,
                    max_chunk_tokens=config.chunk_size,
                    debug=debug,
                    stream=False,
                    model=model,
                    config=config,
                )

                print(f"🔮 Running analysis for new patterns...")
                result = orchestrator.orchestrate(
                    transcript=transcript,
                    video_title=cache_entry.title,
                    video_duration_seconds=cache_entry.duration_seconds,
                    video_info={"id": video_id},
                )

                # Build pattern outputs — only successful patterns with
                # non-empty output (W4: failed patterns must NOT be marked
                # as run or append empty sections)
                pattern_outputs = {
                    pattern_name: pattern_result.combined_output
                    for pattern_name, pattern_result in result.pattern_results.items()
                    if pattern_result.success and pattern_result.combined_output.strip()
                }
                appended_patterns = list(pattern_outputs.keys())

                if not appended_patterns:
                    print("⚠️  No new pattern produced output; note left unchanged")
                    return 0

                # Model provenance (W1) for the appended headings
                append_pattern_meta = {
                    pattern_name: {
                        "models_used": result.pattern_results[pattern_name].models_used,
                        "timestamp": result.pattern_results[pattern_name].run_timestamp,
                    }
                    for pattern_name in appended_patterns
                }
                append_pattern_runs = [
                    {
                        "pattern": pattern_name,
                        "models_used": result.pattern_results[pattern_name].models_used,
                        "timestamp": result.pattern_results[pattern_name].run_timestamp,
                        "source": "append",
                    }
                    for pattern_name in appended_patterns
                ]

                # Append to existing note
                note_path = Path(cache_entry.markdown_path)
                append_patterns_to_note(
                    note_path,
                    pattern_outputs,
                    update_frontmatter=True,
                    pattern_meta=append_pattern_meta,
                    pattern_runs=append_pattern_runs,
                )

                # Update cache
                cache.append_patterns(video_id, appended_patterns)

                print(
                    f"✅ Appended {len(appended_patterns)} new section(s) to {note_path.name}"
                )
                return 0

            else:
                # DEFAULT: Skip existing
                patterns = cache_entry.patterns_run
                print(f"⏭️  SKIPPED: Note already exists for {video_id}")
                print(f"   📄 Existing: {cache_entry.markdown_path}")
                print(
                    f"   📊 Patterns: {len(patterns)} ({', '.join(patterns[:3])}{'...' if len(patterns) > 3 else ''})"
                )
                print(
                    f"   💡 Tip: Use --append to add patterns, --update to refresh metadata, or --force to re-run"
                )
                return 0

        # Extract metadata and transcript
        result = extract_metadata(
            normalized_url,
            cookies_browser=None,
            extract_transcript=True,
            transcript_lang="en",
        )

        metadata = result["metadata"]
        transcript = result.get("transcript")
        transcript_info = result.get("transcript_info", {})

        # Report transcript status
        if transcript:
            word_count = transcript_info.get("transcript_word_count", 0)
            print(f"✅ Extracted transcript: {word_count} words")
        else:
            print("⚠️  Transcript not available")
            if not args.no_analysis:
                print("   Skipping AI analysis (no transcript)")
                args.no_analysis = True

        # Transcript refinement (txrefine, W3): clean the raw transcript
        # before analysis; the note keeps BOTH raw and refined versions.
        # Skipped entirely when disabled (--no-refine / config) or when
        # --no-analysis is set.
        refinement = None
        refine_enabled = (
            args.refine
            if args.refine is not None
            else bool(config.refinement.get("enabled", True))
        )
        if transcript and refine_enabled and not args.no_analysis:
            video_context = VideoContext.from_video_info({"id": video_id, **metadata})
            refinement = refine_transcript(
                transcript,
                video_context=video_context,
                backend=config.refinement.get("backend", "auto"),
                config=config.refinement,
            )
            fallback_note = " · fell back" if refinement.fell_back else ""
            print(
                f"🧹 Refined transcript via {refinement.backend_used}: "
                f"{refinement.original_length:,} → {refinement.refined_length:,} chars"
                f"{fallback_note} ({len(refinement.changes_made)} change(s))"
            )
            if refinement.fell_back:
                print("   ⚠️  refinement validation failed; using regex-only result")

        # Determine patterns to run
        patterns = None

        if args.no_analysis:
            # Skip analysis
            patterns = []

        elif mode == "curated":
            # Curated mode: small high-signal pattern set (new default)
            patterns = list(config.curated_patterns)
            if verbose:
                print(f"💎 Curated mode: {len(patterns)} patterns")

        elif mode == "quick":
            # Quick mode: use configured patterns
            patterns = config.quick_patterns
            if verbose:
                print(f"⚡ Quick mode: {len(patterns)} essential patterns")

        elif mode == "expert":
            # Expert mode: use specified patterns
            patterns = args.patterns
            if verbose:
                print(f"🔧 Expert mode: {len(patterns)} specified patterns")

        elif mode == "auto" or mode == "deep" or mode == "preview":
            # Use pattern_optimizer
            if not transcript:
                print("❌ Cannot run auto-analysis without transcript", file=sys.stderr)
                return 1

            recommendations = run_pattern_optimizer(transcript, debug)

            # Determine filtering
            if mode == "deep":
                min_priority = config.deep_min_priority
                max_patterns = config.deep_max_patterns
            else:  # auto or preview
                min_priority = config.auto_min_priority
                max_patterns = (
                    args.max_patterns if args.max_patterns else config.auto_max_patterns
                )

            patterns = filter_patterns(
                recommendations, max_patterns, min_priority, debug
            )

            # Show recommendations if requested or in preview mode
            if config.auto_show_recommendations or mode == "preview":
                show_recommendations(recommendations, patterns)

            if mode == "preview":
                print("🏁 Preview complete. Run without --preview to execute analysis.")
                return 0

        # Run Fabric analysis if patterns specified
        ai_analysis = None
        pattern_runs = None
        pattern_meta = None
        if patterns and len(patterns) > 0 and transcript:
            # Merge always_run_patterns (prepend, no duplicates)
            if config.always_run_patterns:
                always_patterns = [
                    p for p in config.always_run_patterns if p not in patterns
                ]
                if always_patterns:
                    patterns = always_patterns + patterns
                    if verbose:
                        print(f"📌 Always-run patterns: {', '.join(always_patterns)}")

            print(f"\n🔮 Running AI analysis with {len(patterns)} patterns...")

            # Run orchestrator on the REFINED transcript when available
            # (the note still stores the raw one)
            analysis_transcript = (
                refinement.refined_text if refinement is not None else transcript
            )

            orchestrator = FabricOrchestrator(
                patterns=patterns,
                timeout=config.timeout_per_pattern,
                max_chunk_tokens=config.chunk_size,
                debug=debug,
                stream=False,
                model=model,
                config=config,
            )

            result = orchestrator.orchestrate(
                transcript=analysis_transcript,
                video_title=metadata.get("title", "Untitled"),
                video_duration_seconds=int(metadata.get("duration", 0)),
                video_info={"id": video_id, **metadata},
            )

            # Convert OrchestrationResult to dict[pattern_name -> output_text]
            ai_analysis = {
                pattern_name: pattern_result.combined_output
                for pattern_name, pattern_result in result.pattern_results.items()
            }

            # Model provenance records (W1) — only successful, non-empty runs
            pattern_runs = [
                {
                    "pattern": pattern_name,
                    "models_used": pattern_result.models_used,
                    "timestamp": pattern_result.run_timestamp,
                    "source": "new",
                }
                for pattern_name, pattern_result in result.pattern_results.items()
                if pattern_result.success and pattern_result.combined_output.strip()
            ]
            pattern_meta = {
                run["pattern"]: {
                    "models_used": run["models_used"],
                    "timestamp": run["timestamp"],
                }
                for run in pattern_runs
            }

        # Generate and save markdown
        # Merge transcript info into metadata
        metadata.update(transcript_info)

        # Generate markdown
        frontmatter = generate_frontmatter(metadata, pattern_runs=pattern_runs)
        markdown_content = generate_markdown(
            frontmatter=frontmatter,
            metadata=metadata,
            transcript=transcript,
            ai_analysis=ai_analysis,
            pattern_meta=pattern_meta,
            refined_transcript=(
                refinement.refined_text if refinement is not None else None
            ),
            refinement_meta=refinement,
        )

        # Save to output directory
        if force_original_path is not None and force_original_path.exists():
            # --force on an existing note (W4): atomically overwrite the
            # ORIGINAL file — never resolve_collision into a " (2)" duplicate
            atomic_write_note(force_original_path, markdown_content, backup=True)
            output_path = force_original_path
        else:
            output_path = save_markdown(
                content=markdown_content,
                title=metadata.get("title", "Untitled"),
                upload_date=metadata.get("upload_date", "19700101"),
                output_dir=output_dir,
            )

        print(f"\n✅ Note saved: {output_path}")

        # ============================================================
        # SAVE TO CACHE (V3.0)
        # ============================================================
        from datetime import datetime

        # Cache only patterns that produced successful, non-empty output
        # (failed runs must stay appendable); record full provenance runs
        successful_patterns = [run["pattern"] for run in (pattern_runs or [])]

        cache_entry = CacheEntry(
            video_id=video_id,
            video_url=normalized_url,
            title=metadata.get("title", "Untitled"),
            upload_date=metadata.get("upload_date", "19700101"),
            duration_seconds=int(metadata.get("duration", 0)),
            transcript_word_count=transcript_info.get("transcript_word_count", 0),
            markdown_path=str(output_path),
            last_updated=datetime.now().isoformat(),
            patterns_run=successful_patterns,
            processing_history=[
                {
                    "timestamp": datetime.now().isoformat(),
                    "mode": mode,
                    "model": model,
                    "patterns_run": successful_patterns,
                    "pattern_runs": pattern_runs or [],
                    "success": True,
                }
            ],
            chunks=None,
            phase1_metadata=None,
            refinement_backend=(
                refinement.backend_used if refinement is not None else None
            ),
            refinement_fell_back=(
                refinement.fell_back if refinement is not None else None
            ),
            refinement_changes=(
                refinement.changes_made if refinement is not None else None
            ),
        )

        cache.save_cache(video_id, cache_entry)

        if verbose:
            print(f"💾 Cached analysis for future runs")

        if config.open_in_editor:
            import subprocess

            try:
                subprocess.run(["open", str(output_path)], timeout=10)
            except Exception:
                pass

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if hasattr(args, "debug") and args.debug:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
