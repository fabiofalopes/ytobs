# Phase 1 Implementation Plan

**Created**: 2024-12-08  
**Target**: YouTube → Obsidian Metadata Pipeline  
**Phase**: 1 - Metadata Extraction Only  
**Status**: Ready for Implementation

---

## Implementation Overview

### Objective

Build a single-purpose Python script that extracts YouTube metadata and generates Obsidian markdown notes.

### Scope

**IN SCOPE (Phase 1)**:
- ✅ YouTube URL validation
- ✅ Metadata extraction via yt-dlp
- ✅ YAML front matter generation
- ✅ Markdown file creation
- ✅ Error handling for common cases

**OUT OF SCOPE (Future Phases)**:
- ❌ Transcript extraction (Phase 2)
- ❌ Audio download (Phase 3)
- ❌ Batch processing (Phase 4)
- ❌ GUI interface (Future)

### Success Criteria

1. Script executes in < 3 seconds for single video
2. Generates valid Obsidian-compatible markdown
3. Handles edge cases (age-gated, unavailable, etc.)
4. Passes all test cases (T01-T10)
5. Clean code ready for .myscripts migration

---

## Implementation Phases

### Phase 1A: Core Script (Week 1)

**Goal**: Working prototype with core functionality

#### Tasks

| Task | Estimated Time | Priority | Status |
|------|----------------|----------|--------|
| Set up project structure | 30min | High | Pending |
| Implement URL validator | 1h | High | Pending |
| Implement yt-dlp executor | 2h | High | Pending |
| Implement JSON parser | 1h | High | Pending |
| Implement front matter generator | 2h | High | Pending |
| Implement markdown generator | 1h | High | Pending |
| Implement file system manager | 1h | High | Pending |
| Basic CLI interface | 1h | Medium | Pending |
| Manual testing | 2h | High | Pending |

**Deliverables**:
- Single Python script: `yt-obsidian.py`
- Basic configuration file
- Example outputs

---

### Phase 1B: Polish & Testing (Week 2)

**Goal**: Production-ready code with comprehensive testing

#### Tasks

| Task | Estimated Time | Priority | Status |
|------|----------------|----------|--------|
| Write unit tests | 3h | High | Pending |
| Write integration tests | 2h | Medium | Pending |
| Implement retry logic | 1h | High | Pending |
| Enhanced error messages | 1h | High | Pending |
| Configuration system | 2h | Medium | Pending |
| Documentation | 2h | High | Pending |
| Code cleanup & typing | 2h | Medium | Pending |

**Deliverables**:
- Comprehensive test suite
- Enhanced error handling
- Clean, typed Python code
- Usage documentation

---

### Phase 1C: Migration to .myscripts (Week 3)

**Goal**: Deploy to production environment

#### Tasks

| Task | Estimated Time | Priority | Status |
|------|----------------|----------|--------|
| Modularize code | 2h | High | Pending |
| Create executable wrapper | 1h | High | Pending |
| Integration testing | 2h | High | Pending |
| Migration to .myscripts | 1h | High | Pending |
| Final documentation | 2h | Medium | Pending |

**Deliverables**:
- Clean module structure
- Installed in ~/.myscripts/youtube/
- Complete usage guide

---

## Detailed Implementation Guide

### Step 1: Project Setup

```bash
# Set up environment variable (add to ~/.zshrc or ~/.bashrc)
echo 'export OBSVAULT="/path/to/your/obsidian/vault"' >> ~/.zshrc
source ~/.zshrc

# Create structure
cd ~/projetos/rascunhos/yt-dlp-tests
mkdir -p lib tests examples

# Create files
touch yt-obsidian.py
touch lib/__init__.py lib/validator.py lib/extractor.py lib/formatter.py lib/filesystem.py
touch requirements.txt
touch config.yaml
touch tests/__init__.py tests/test_validator.py tests/test_extractor.py
```

**File Structure**:
```
yt-dlp-tests/
├── yt-obsidian.py          # Main entry point
├── lib/
│   ├── __init__.py
│   ├── validator.py        # URL validation
│   ├── extractor.py        # yt-dlp execution
│   ├── formatter.py        # YAML/markdown generation
│   └── filesystem.py       # File operations
├── tests/
│   ├── __init__.py
│   ├── test_validator.py
│   ├── test_extractor.py
│   ├── test_formatter.py
│   └── test_filesystem.py
├── config.yaml             # Configuration
├── requirements.txt        # Dependencies
└── examples/               # Example outputs
```

---

### Step 2: Dependencies

**requirements.txt**:
```txt
pyyaml>=6.0
pydantic>=2.0
tenacity>=8.0
pytest>=7.0
```

**Install**:
```bash
pip install -r requirements.txt
```

**Verify yt-dlp**:
```bash
yt-dlp --version
```

---

### Step 3: Implementation Order

#### 3.1: URL Validator (lib/validator.py)

**Priority**: Start here, simplest component

```python
import re
from typing import Optional

def validate_url(url: str) -> tuple[bool, str, Optional[str]]:
    """
    Validates YouTube URL and extracts video ID.
    
    Returns:
        (is_valid, normalized_url, video_id)
    """
    # Implementation per ARCHITECTURE.md
    pass
```

**Test First**:
```python
# tests/test_validator.py
def test_validate_standard_url():
    is_valid, normalized, video_id = validate_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert is_valid
    assert video_id == "dQw4w9WgXcQ"
```

---

#### 3.2: Metadata Extractor (lib/extractor.py)

**Priority**: Core functionality

```python
import subprocess
import json
from typing import Optional

def extract_metadata(
    url: str,
    cookies_browser: Optional[str] = None
) -> dict:
    """
    Executes yt-dlp and returns parsed JSON.
    """
    # Implementation per ARCHITECTURE.md
    pass
```

**Manual Test**:
```bash
# Test yt-dlp command directly first
yt-dlp --dump-json --skip-download "https://youtu.be/dQw4w9WgXcQ"
```

---

#### 3.3: Front Matter Generator (lib/formatter.py)

**Priority**: Critical for output quality

```python
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

def generate_frontmatter(metadata: dict) -> str:
    """
    Generates YAML front matter from yt-dlp JSON.
    
    Follows OBSIDIAN_SCHEMA.md specification.
    """
    # Implementation per ARCHITECTURE.md and OBSIDIAN_SCHEMA.md
    pass

def generate_markdown(frontmatter: str, metadata: dict) -> str:
    """
    Generates complete markdown file.
    """
    # Implementation per ARCHITECTURE.md
    pass
```

---

#### 3.4: File System Manager (lib/filesystem.py)

**Priority**: Final component

```python
from pathlib import Path

def save_markdown(
    content: str,
    title: str,
    upload_date: str,
    output_dir: Path = None  # Defaults to $OBSVAULT/youtube if None
) -> Path:
    """
    Saves markdown to filesystem.
    """
    # Implementation per ARCHITECTURE.md
    pass
```

---

#### 3.5: Main Script (yt-obsidian.py)

**Priority**: After all components work

```python
#!/usr/bin/env python3
"""
YouTube to Obsidian Metadata Extractor

Usage:
    yt-obsidian <youtube_url>
    yt-obsidian --help
"""

import sys
import os
import argparse
from pathlib import Path

from lib.validator import validate_url
from lib.extractor import extract_metadata
from lib.formatter import generate_frontmatter, generate_markdown
from lib.filesystem import save_markdown

def main():
    parser = argparse.ArgumentParser(
        description="Extract YouTube metadata and create Obsidian note"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--cookies", 
        choices=["firefox", "chrome", "safari"],
        help="Browser for cookie extraction (age-gated videos)"
    )
    parser.add_argument(
        "--output", 
        type=Path,
        default=None,  # Will use $OBSVAULT/youtube if not specified
        help="Output directory (default: $OBSVAULT/youtube)"
    )
    
    args = parser.parse_args()
    
    # Validate OBSVAULT environment variable if no output specified
    if args.output is None:
        obsvault = os.getenv("OBSVAULT")
        if not obsvault:
            print("Error: OBSVAULT environment variable not set.")
            print("Set it with: export OBSVAULT=/path/to/your/obsidian/vault")
            sys.exit(1)
        args.output = Path(obsvault) / "youtube"
    
    try:
        # Validate
        is_valid, normalized, video_id = validate_url(args.url)
        if not is_valid:
            print(f"Error: Invalid YouTube URL")
            sys.exit(1)
        
        # Extract
        print(f"Extracting metadata for {video_id}...")
        metadata = extract_metadata(normalized, args.cookies)
        
        # Generate
        frontmatter = generate_frontmatter(metadata)
        markdown = generate_markdown(frontmatter, metadata)
        
        # Save
        output_path = save_markdown(
            markdown,
            metadata['title'],
            metadata['upload_date'],
            args.output
        )
        
        print(f"✓ Created: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 80%+

```python
# tests/test_validator.py
def test_validate_standard_url():
    # Test standard URL format
    pass

def test_validate_short_url():
    # Test youtu.be format
    pass

def test_invalid_url():
    # Test rejection of non-YouTube URL
    pass

# tests/test_formatter.py
def test_generate_frontmatter():
    # Test YAML generation
    pass

def test_duration_formatting():
    # Test HH:MM:SS formatting
    pass

def test_timestamp_formatting():
    # Test ISO 8601 generation
    pass
```

### Integration Tests

```python
# tests/test_integration.py
@pytest.mark.integration
def test_full_workflow():
    """Test complete extraction workflow"""
    url = "https://youtu.be/dQw4w9WgXcQ"
    
    # Extract
    metadata = extract_metadata(url)
    
    # Generate
    frontmatter = generate_frontmatter(metadata)
    markdown = generate_markdown(frontmatter, metadata)
    
    # Validate
    assert "---" in markdown
    assert metadata['title'] in markdown
    
    # Verify YAML is valid
    parts = markdown.split("---", 2)
    parsed = yaml.safe_load(parts[1])
    assert parsed['video_id'] == "dQw4w9WgXcQ"
```

### Manual Test Cases

| Test | URL | Expected |
|------|-----|----------|
| Public video | `https://youtu.be/dQw4w9WgXcQ` | Success |
| Age-restricted | (Find age-gated video) | Prompt for cookies |
| Unavailable | (Find deleted video) | Clear error |
| Long title | (Find long-title video) | Truncated filename |

---

## Error Handling Implementation

### Custom Exceptions

```python
# lib/exceptions.py
class YTObsidianError(Exception):
    """Base exception"""
    pass

class VideoUnavailableError(YTObsidianError):
    """Video is deleted/private/geo-blocked"""
    pass

class AgeRestrictedError(YTObsidianError):
    """Video requires age verification"""
    pass

class NetworkError(YTObsidianError):
    """Network connection issue"""
    pass

class RateLimitError(YTObsidianError):
    """YouTube rate limiting"""
    pass
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def extract_with_retry(url: str) -> dict:
    return extract_metadata(url)
```

---

## Configuration System

### Environment Variable Setup

**REQUIRED**: User must set `$OBSVAULT` environment variable:

```bash
# Add to ~/.zshrc or ~/.bashrc
export OBSVAULT="/path/to/your/obsidian/vault"
```

The script will use `$OBSVAULT/youtube/` as the output directory.

### config.yaml

```yaml
# NOTE: Output directory uses $OBSVAULT environment variable  
# User must set: export OBSVAULT=/path/to/obsidian/vault
output:
  directory: null  # Uses $OBSVAULT/youtube when null
  filename_format: "{date} - {title}.md"
  max_title_length: 100

ytdlp:
  cookies_browser: firefox
  proxy: null
  rate_limit: null

metadata:
  include_description: true
  include_tags: true
  include_metrics: true
  timezone: America/New_York

advanced:
  retry_attempts: 3
  verbose: false
```

### Loading

```python
# lib/config.py
import yaml
from pathlib import Path

def load_config() -> dict:
    config_path = Path.home() / ".config/yt-obsidian/config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return get_default_config()
```

---

## Migration Checklist

### Pre-Migration

- [ ] All tests passing
- [ ] Code reviewed and cleaned
- [ ] Documentation complete
- [ ] Example outputs validated in Obsidian
- [ ] Error messages user-friendly

### Migration Steps

1. **Create clean structure**:
   ```bash
   mkdir -p ~/.myscripts/youtube/{lib,examples}
   ```

2. **Copy files**:
   ```bash
   cp yt-obsidian.py ~/.myscripts/youtube/yt-obsidian
   cp -r lib ~/.myscripts/youtube/
   cp config.yaml ~/.myscripts/youtube/
   ```

3. **Make executable**:
   ```bash
   chmod +x ~/.myscripts/youtube/yt-obsidian
   ```

4. **Update PATH**:
   ```bash
   # Add to ~/.zshrc
   export PATH="$HOME/.myscripts/youtube:$PATH"
   ```

5. **Test in production**:
   ```bash
   yt-obsidian "https://youtu.be/dQw4w9WgXcQ"
   ```

### Post-Migration

- [ ] Script works from any directory
- [ ] Output directory correctly resolved
- [ ] Configuration file loaded correctly
- [ ] Git commit and push to .myscripts repo

---

## Timeline Estimate

### Phase 1A: Core Script
- Setup: 0.5h
- URL Validator: 1h
- Metadata Extractor: 2h
- Formatter: 3h
- File Manager: 1h
- Main Script: 1h
- Testing: 2h
- **Total: 10.5h** (1-2 days)

### Phase 1B: Polish
- Tests: 5h
- Error Handling: 2h
- Configuration: 2h
- Documentation: 2h
- **Total: 11h** (1-2 days)

### Phase 1C: Migration
- Refactoring: 2h
- Testing: 2h
- Migration: 1h
- Documentation: 2h
- **Total: 7h** (1 day)

### **Grand Total: ~28-30 hours** (4-5 days of focused work)

---

## Success Metrics

### Functional

- ✅ Extracts metadata in < 3 seconds
- ✅ Generates valid Obsidian markdown
- ✅ Handles 10 edge cases correctly
- ✅ 80%+ test coverage

### Quality

- ✅ Clean, typed Python code
- ✅ Comprehensive error messages
- ✅ Well-documented functions
- ✅ Follows PEP 8 style guide

### Usability

- ✅ Simple CLI interface
- ✅ Clear error messages
- ✅ Helpful usage documentation
- ✅ Works from any directory

---

## Next Steps After Phase 1

### Phase 2: Transcript Extraction
- Add `--transcript` flag
- Integrate transcript into markdown
- Format transcript for readability

### Phase 3: Audio Download
- Add `--audio` flag
- Download and convert to Opus
- Link audio file in front matter

### Phase 4: Batch Processing
- Accept multiple URLs
- Process playlist
- Process channel

---

## Resources

### Documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [OBSIDIAN_SCHEMA.md](./OBSIDIAN_SCHEMA.md) - Front matter spec
- [TECHNOLOGY_DECISION.md](./TECHNOLOGY_DECISION.md) - Tech rationale

### External
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [pytest Docs](https://docs.pytest.org/)

---

## Team Communication

### Questions During Implementation

1. **Output directory**: Uses `$OBSVAULT` environment variable
   → **User must set: export OBSVAULT=/path/to/obsidian/vault**
   → **Script uses: $OBSVAULT/youtube/ as output directory**

2. **Cookies browser**: Default to firefox or ask?
   → **Default to firefox, override with --cookies**

3. **Filename format**: `YYYY-MM-DD - Title` or other?
   → **YYYY-MM-DD - Title (100 char limit)**

4. **Include metrics**: Always include views/likes?
   → **Yes, if available (public videos)**

---

**Ready for Implementation**: All specifications complete, architecture defined, test cases outlined.

**Next**: Begin Phase 1A implementation following this plan.
