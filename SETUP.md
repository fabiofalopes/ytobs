# ytobs - Setup Guide

## What This Tool Does

Extracts YouTube videos to AI-enhanced Obsidian notes with ONE command.

```bash
ytobs "https://youtube.com/watch?v=VIDEO_ID"
```

Result: Markdown note with metadata, transcript, and AI analysis in your Obsidian vault.

---

## Quick Setup

### 1. Set Obsidian Vault Location
```bash
# Add to ~/.zshrc or ~/.bashrc
export OBSVAULT="/path/to/your/obsidian/vault"

# Reload shell
source ~/.zshrc
```

### 2. Install ytobs
```bash
pip install -e ~/projetos/hub/ytobs
```

### 3. Test It Works
```bash
ytobs --help
```

### 4. Run Your First Video
```bash
ytobs --quick "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Check `$OBSVAULT/youtube/` for the generated note.

---

## Usage Modes

### Quick Mode (~25s)
All `./yt` commands replaced with `ytobs`:
```bash
ytobs --quick "URL"
```

### Auto Mode (~50s) - Default
Smart pattern selection based on content:
```bash
ytobs "URL"
```

### Deep Mode (~70s)
Comprehensive analysis with all patterns:
```bash
ytobs --deep "URL"
```

### Preview Mode (instant)
See what patterns would run without executing:
```bash
ytobs --preview "URL"
```

---

## Configuration

First run creates `~/.yt-obsidian/config.yml`:

```yaml
mode: auto                # auto, quick, deep
model: kimi              # kimi, llama-4-scout, llama-70b
output_dir: ~/Documents/obsidian_vault/youtube
timeout_per_pattern: 60
chunk_size: 10000
open_in_editor: false
```

Edit to customize your defaults.

---

## What You Get

Every note includes:

1. **YAML Frontmatter**
   - Title, channel, duration, views, likes
   - Upload date, tags, categories
   - Video ID and direct link

2. **Video Description**
   - Full description with links
   - Channel information

3. **Transcript**
   - Complete transcript with timestamps
   - Formatted for readability

4. **AI Analysis** (varies by mode)
   - Wisdom extraction
   - Key insights and patterns
   - Summary and main ideas
   - Quotes and facts
   - Actionable recommendations

---

## Project Structure

```
ytobs/
├── ytobs/             # 🐍 Python package (ytobs.cli:main)
├── venv/              # Virtual environment
├── pyproject.toml     # Package metadata + entry point
├── config.yaml        # Default configuration
├── requirements.txt   # Dependencies
├── README.md          # Full documentation
├── CONTEXT.md         # Project state/decisions
├── docs/              # Architecture docs
└── reference/         # Reference materials
```

No hidden runtime directories in ytobs/.

---

## Troubleshooting

**"OBSVAULT not set"**
```bash
export OBSVAULT="/path/to/vault"
echo $OBSVAULT  # Verify it's set
```

**"Age-restricted video"**
Tool will show clear error. Most videos work without authentication.

**"Slow analysis"**
Use `--quick` mode or faster model:
```bash
ytobs --quick "URL"
ytobs --model llama-4-scout "URL"
```

---

## Advanced Options

```bash
# Use specific model
ytobs --model llama-4-scout "URL"

# Run specific patterns only
ytobs --patterns extract_wisdom summary "URL"

# Skip AI analysis (metadata + transcript only)
ytobs --no-analysis "URL"

# Custom output directory
ytobs --output /custom/path "URL"

# Debug mode
ytobs --debug "URL"
```

---

## Available Models

- **kimi** (default) - 10K TPM, balanced quality/speed
- **llama-4-scout** - 30K TPM, fastest
- **llama-70b** - 12K TPM, highest quality

---

## Making It Global

`ytobs` is already a global command after `pip install -e ~/projetos/hub/ytobs`:

```bash
ytobs --version
```

---

## What's in archive/

Old tools kept as backup:
- `yt-obsidian.py` - Original legacy entry point
- `md-html.py` - Standalone converter utility

---

**Need help?** Check `README.md` for full documentation.
