"""
Configuration management for yt (YouTube to Obsidian).

Handles loading, creating, and managing user configuration from ~/.yt-obsidian/config.yml
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Provider-aware model configuration."""

    provider: str = "fabric"
    model_id: str = ""
    context_window: int = 200000
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None


@dataclass
class Config:
    """User configuration for yt command."""

    # Analysis behavior
    analysis_mode: str = "auto"  # auto, quick, deep, expert
    model: str = "best"  # best (auto-pick), fast, quality, or specific model name

    # Provider-aware model registry
    models: Dict[str, ModelConfig] = field(
        default_factory=lambda: {
            "minimax": ModelConfig("fabric", "minimax-m2.7:cloud", 204800),
            "kimi": ModelConfig("fabric", "kimi-k2.6:cloud", 262144),
            "deepseek": ModelConfig("fabric", "deepseek-v4-pro:cloud", 1048576),
            "fast": ModelConfig("fabric", "minimax-m2.1:cloud", 204800),
            "qwen": ModelConfig("fabric", "qwen3.5:cloud", 262144),
        }
    )
    model_aliases: Dict[str, str] = field(
        default_factory=lambda: {
            "best": "minimax",
            "fast": "fast",
            "quality": "deepseek",
        }
    )

    # Output settings
    output_dir: Optional[str] = None  # Default: $OBSVAULT/youtube
    open_in_editor: bool = False
    keep_temp_files: bool = False
    verbose: bool = False

    # Always-run patterns (run on every video first)
    always_run_patterns: list = field(default_factory=list)

    # Auto-analyze settings (used when analysis_mode=auto)
    auto_min_priority: str = "high"  # essential, high, medium, optional
    auto_max_patterns: int = 15
    auto_show_recommendations: bool = False

    # Quick mode settings
    quick_patterns: list = field(
        default_factory=lambda: [
            "extract_wisdom",
            "youtube_summary",
            "extract_insights",
            "extract_patterns",
            "extract_main_idea",
        ]
    )

    # Deep mode settings
    deep_min_priority: str = "optional"  # Include everything
    deep_max_patterns: int = 25

    # Expert mode settings
    fabric_command: str = "fabric-ai"
    timeout_per_pattern: int = 120
    chunk_size: int = 50000


DEFAULT_CONFIG_CONTENT = """# yt - YouTube to Obsidian Configuration
# Location: ~/.yt-obsidian/config.yml
# Edit this file to customize default behavior

# ============================================================================
# ANALYSIS MODE
# ============================================================================
# Determines how videos are analyzed by default
# Options: auto, quick, deep, expert
#
# - auto:   Smart analysis using pattern_optimizer (recommended)
#           Analyzes content and selects 10-15 optimal patterns
#           Time: ~50 seconds
#
# - quick:  Fast analysis with 5 essential patterns only
#           Time: ~25 seconds
#           Patterns: wisdom, summary, insights, patterns, main idea
#
# - deep:   Complete analysis with all recommended patterns
#           Time: ~70 seconds
#
# - expert: Full manual control over all settings
#
analysis_mode: auto

# ============================================================================
# MODEL SELECTION
# ============================================================================
# Default model alias. Must resolve to an entry in model_aliases below, or be
# a specific model_id registered in models (or a raw Fabric model tag).
# Options: best, fast, quality, or any model alias defined below
#
# - best:    Auto-selects best all-around model (minimax-m2.7, 200K context)
# - fast:    Prioritizes speed (minimax-m2.1, 200K context)
# - quality: Prioritizes quality (deepseek-v4-pro, 1M context)
#
model: best

# Provider-aware model registry.
# Add, remove, or edit entries to switch providers without touching code.
# 'provider' selects the backend adapter. Only 'fabric' is implemented today.
models:
  minimax:
    provider: fabric
    model_id: minimax-m2.7:cloud
    context_window: 204800
  kimi:
    provider: fabric
    model_id: kimi-k2.6:cloud
    context_window: 262144
  deepseek:
    provider: fabric
    model_id: deepseek-v4-pro:cloud
    context_window: 1048576
  fast:
    provider: fabric
    model_id: minimax-m2.1:cloud
    context_window: 204800
  qwen:
    provider: fabric
    model_id: qwen3.5:cloud
    context_window: 262144

# Short aliases that map to entries in 'models'.
model_aliases:
  best: minimax
  fast: fast
  quality: deepseek

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
# Where to save the generated notes
# Use $OBSVAULT to reference your Obsidian vault environment variable
# Default: $OBSVAULT/youtube
output_dir: null

# Open note in editor after creation?
open_in_editor: false

# Keep temporary files in .fabric/ directory for debugging?
keep_temp_files: false

# Show detailed output during processing?
verbose: false

# ============================================================================
# ALWAYS-RUN PATTERNS
# ============================================================================
# Patterns that run on EVERY video before mode-specific patterns.
# Useful for baseline analysis you always want. Leave empty for none.
# Example: ["extract_main_idea", "youtube_summary"]
always_run_patterns: []

# ============================================================================
# AUTO MODE SETTINGS (used when analysis_mode=auto)
# ============================================================================
auto:
  # Minimum pattern priority to include
  # Options: essential, high, medium, optional
  min_priority: high
  
  # Maximum number of patterns to run
  max_patterns: 15
  
  # Show pattern recommendations before running?
  show_recommendations: false

# ============================================================================
# QUICK MODE SETTINGS
# ============================================================================
# Patterns to run in quick mode (can customize this list)
quick:
  patterns:
    - extract_wisdom
    - youtube_summary
    - extract_insights
    - extract_patterns
    - extract_main_idea

# ============================================================================
# DEEP MODE SETTINGS
# ============================================================================
deep:
  # Include all priorities (even optional patterns)
  min_priority: optional
  
  # Higher limit for comprehensive analysis
  max_patterns: 25

# ============================================================================
# EXPERT MODE SETTINGS
# ============================================================================
expert:
  # Fabric CLI command (override if using different installation)
  fabric_command: fabric-ai
  
  # Timeout per pattern execution (seconds)
  timeout_per_pattern: 120
  
  # Chunk size for large transcripts (tokens)
  chunk_size: 50000
"""


def get_config_path() -> Path:
    """Get path to user config file."""
    config_dir = Path.home() / ".yt-obsidian"
    return config_dir / "config.yml"


def ensure_config_dir() -> Path:
    """Ensure config directory exists."""
    config_dir = Path.home() / ".yt-obsidian"
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return config_dir


def create_default_config() -> Path:
    """Create default config file."""
    ensure_config_dir()
    config_path = get_config_path()

    if not config_path.exists():
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG_CONTENT)

    return config_path


def load_config() -> Config:
    """Load user configuration from file.

    Creates default config if it doesn't exist.
    Falls back to built-in defaults if file is malformed.

    Returns:
        Config object with user settings
    """
    config_path = get_config_path()

    # Create default config if doesn't exist
    if not config_path.exists():
        create_default_config()
        return Config()  # Return defaults for first run

    # Try to load existing config
    try:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)

        if not user_config:
            return Config()

        # Parse config with defaults
        config = Config()

        # Top-level settings
        config.analysis_mode = user_config.get("analysis_mode", config.analysis_mode)
        config.model = user_config.get("model", config.model)
        config.output_dir = user_config.get("output_dir", config.output_dir)
        config.open_in_editor = user_config.get("open_in_editor", config.open_in_editor)
        config.keep_temp_files = user_config.get(
            "keep_temp_files", config.keep_temp_files
        )
        config.verbose = user_config.get("verbose", config.verbose)

        # Always-run patterns
        config.always_run_patterns = user_config.get(
            "always_run_patterns", config.always_run_patterns
        )

        # Auto mode settings
        if "auto" in user_config:
            auto = user_config["auto"]
            config.auto_min_priority = auto.get(
                "min_priority", config.auto_min_priority
            )
            config.auto_max_patterns = auto.get(
                "max_patterns", config.auto_max_patterns
            )
            config.auto_show_recommendations = auto.get(
                "show_recommendations", config.auto_show_recommendations
            )

        # Quick mode settings
        if "quick" in user_config and "patterns" in user_config["quick"]:
            config.quick_patterns = user_config["quick"]["patterns"]

        # Deep mode settings
        if "deep" in user_config:
            deep = user_config["deep"]
            config.deep_min_priority = deep.get(
                "min_priority", config.deep_min_priority
            )
            config.deep_max_patterns = deep.get(
                "max_patterns", config.deep_max_patterns
            )

        # Expert mode settings
        if "expert" in user_config:
            expert = user_config["expert"]
            config.fabric_command = expert.get("fabric_command", config.fabric_command)
            config.timeout_per_pattern = expert.get(
                "timeout_per_pattern", config.timeout_per_pattern
            )
            config.chunk_size = expert.get("chunk_size", config.chunk_size)

        # Provider-aware model registry
        if "models" in user_config:
            config.models = {
                name: ModelConfig(
                    provider=model.get("provider", "fabric"),
                    model_id=model.get("model_id", ""),
                    context_window=model.get("context_window", 200000),
                    base_url=model.get("base_url"),
                    api_key_env=model.get("api_key_env"),
                )
                for name, model in user_config["models"].items()
            }

        if "model_aliases" in user_config:
            config.model_aliases = user_config["model_aliases"]

        return config

    except Exception as e:
        # If config is malformed, fall back to defaults
        print(f"⚠️  Warning: Could not load config from {config_path}: {e}")
        print(f"⚠️  Using built-in defaults")
        return Config()


def resolve_model(model_setting: str, config: Config) -> str:
    """Resolve model setting to an alias or direct model identifier."""
    return config.model_aliases.get(model_setting, model_setting)


def resolve_model_config(alias_or_id: str, config: Config) -> ModelConfig:
    """Resolve a model alias or raw identifier to a ModelConfig.

    If alias_or_id matches an entry in config.models, return that config.
    Otherwise treat it as a raw model identifier and default to the fabric
    provider with a conservative context window.
    """
    if alias_or_id in config.models:
        return config.models[alias_or_id]
    return ModelConfig(provider="fabric", model_id=alias_or_id, context_window=200000)


def get_cache_dir() -> Path:
    """Get cache directory path outside iCloud-synced locations.

    Uses ~/.yt-obsidian/cache/ to avoid macOS/iCloud permission issues
    that occur when cache is inside the Obsidian vault (Documents/).

    Returns:
        Path to cache directory (created if doesn't exist)
    """
    cache_dir = Path.home() / ".yt-obsidian" / "cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Last resort fallback: system temp directory
        import tempfile

        cache_dir = Path(tempfile.gettempdir()) / "ytobs-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def resolve_output_dir(config: Config) -> Path:
    """Resolve output directory from config.

    Args:
        config: User configuration

    Returns:
        Path to output directory

    Raises:
        ValueError: If OBSVAULT not set and no output_dir specified
    """
    if config.output_dir:
        # Expand $OBSVAULT if present
        output_dir = config.output_dir
        if "$OBSVAULT" in output_dir:
            obsvault = os.getenv("OBSVAULT")
            if not obsvault:
                raise ValueError("OBSVAULT environment variable not set")
            output_dir = output_dir.replace("$OBSVAULT", obsvault)
        return Path(output_dir)

    # Default: $OBSVAULT/youtube
    obsvault = os.getenv("OBSVAULT")
    if not obsvault:
        raise ValueError(
            "OBSVAULT environment variable not set. "
            "Set it with: export OBSVAULT=/path/to/vault"
        )

    return Path(obsvault) / "youtube"
