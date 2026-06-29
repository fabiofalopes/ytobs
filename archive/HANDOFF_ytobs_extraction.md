# HANDOFF: ytobs Extraction & Packaging

**For**: Next agent session — load this file, execute checklist, ship.
**Status**: Spec complete. Awaiting execution.
**Created**: 2026-05-30
**Estimated time**: 2-3 hours

---

## What Is ytobs?

A V4.0 production CLI that extracts YouTube videos into AI-enhanced Obsidian notes with one command. Smart cache prevents duplicates. 76 videos processed. 18 Python modules (~3,000 lines).

```bash
ytobs "https://youtube.com/watch?v=VIDEO_ID"    # Smart analysis
ytobs --quick URL    # Fast (5 patterns, ~25s)
ytobs --deep URL     # Complete (all patterns, ~70s)
ytobs status VIDEO   # Show video processing status
ytobs vault          # Show vault statistics
```

**Pipeline**: URL → yt-dlp extract → Fabric pattern_optimizer → chunk transcript → AI analysis (via Groq API) → Obsidian markdown note.

---

## Current State

| Aspect | Value |
|--------|-------|
| Location | `~/projetos/hub/.myscripts/youtube-obsidian/` |
| Entry point | `yt` (1022-line Python script) |
| Shell integration | `~/.zshrc:129` — `ytobs()` function that cd's to project and runs `python3 yt` |
| Package name | None (no pyproject.toml, no pip install) |
| lib/ modules | 18 Python files |
| Dependencies | 28 pinned in requirements.txt (1 dead: pydantic) |
| Config | `~/.yt-obsidian/config.yml` (auto-created on first run) |
| Cache | `$OBSVAULT/youtube/.cache/` (76 entries) |
| Docs | CONTEXT.md (856 lines), START_HERE.md, HELP.md, README.md, SETUP.md, CONTRIBUTING.md |
| License | MIT (present) |
| Tests | None |
| Version | 4.0.0 (Status & Vault Commands) |

---

## Target State

| Aspect | Value |
|--------|-------|
| Location | `~/projetos/hub/ytobs/` |
| Entry point | `console_scripts` entry in pyproject.toml → `ytobs` CLI command |
| Shell integration | Remove shell function from ~/.zshrc. `pip install -e .` makes `ytobs` available globally. |
| Package name | `ytobs` |
| Import style | Package-relative: `from ytobs.xxx import ...` (lib/ renamed to ytobs/) |
| Dependencies | Loosened version ranges. pydantic removed. Dev deps moved to `[dev]` extras. |
| Tests | None (for now) — not in scope for extraction |

---

## Architecture (Post-Extraction)

```
hub/ytobs/
├── pyproject.toml              # NEW — package metadata + deps + entry point
├── LICENSE                     # MIT
├── README.md                   # User docs
├── CONTEXT.md                  # Full project history
├── START_HERE.md               # AI agent onboarding
├── HELP.md                     # Extended command reference
├── CONTRIBUTING.md             # Dev contribution guide
│
├── ytobs/                      # Package directory (renamed from lib/)
│   ├── __init__.py             # exports __version__ = "4.0.0"
│   ├── cli.py                  # NEW — migrate main() from yt script here
│   ├── config.py               # Config management (~/.yt-obsidian/config.yml)
│   ├── cache_manager.py        # V3.0 Smart cache
│   ├── channel.py              # YouTube channel operations
│   ├── chunker.py              # Transcript chunking
│   ├── exceptions.py           # Custom exceptions
│   ├── extractor.py            # yt-dlp metadata + transcript extraction
│   ├── fabric_orchestrator.py  # Two-phase Fabric orchestration
│   ├── filesystem.py           # Safe file I/O
│   ├── formatter.py            # YAML frontmatter + markdown
│   ├── incremental_writer.py   # Append to existing notes
│   ├── markdown_utils.py       # Heading normalization
│   ├── metadata_extractor.py   # Phase 1 global metadata
│   ├── packet_builder.py       # Enriched packet creation
│   ├── rate_limiter.py         # Groq rate limit handling
│   ├── status_display.py       # Status display
│   ├── token_counter.py        # Token estimation
│   ├── transcript.py           # Transcript parsing
│   └── validator.py            # URL validation
│
├── docs/                       # Architecture, development, design docs
├── archive/                    # Deprecated files + session history
├── reference/                  # Reference materials
├── config.yaml                 # Default project config
├── requirements.txt            # Runtime deps (loosened)
├── .gitignore                  # Already exists
└── yt                          # OLD entry script — DELETE after cli.py migration
```

---

## Critical Bugs to Fix During Extraction

### Bug 1: Absolute Import in lib/validator.py (WILL BREAK)

**File**: `lib/validator.py`, line 9
**Current**: `from lib.exceptions import ValidationError`
**Fix**: `from .exceptions import ValidationError`

**Why it breaks**: After renaming `lib/` to `ytobs/`, `from lib.exceptions` resolves to nothing. Must be `from ytobs.exceptions` or `from .exceptions`. Use relative import.

### Bug 2: Dead Dependency — pydantic

**File**: `requirements.txt`
**Issue**: `pydantic==2.12.5` is listed but **no file imports it**. The project uses `dataclasses` instead.
**Fix**: Remove `pydantic` from runtime dependencies.

### Bug 3: All lib/ imports must be package-relative

Every `from lib.xxx import ...` in `yt` (the main script) needs review when `lib/` becomes `ytobs/`. If `cli.py` is inside the `ytobs/` package, imports stay relative. If it's outside, they become `from ytobs.xxx import ...`.

---

## pyproject.toml Specification

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ytobs"
version = "4.0.0"
description = "Extract YouTube videos to Obsidian notes with AI analysis"
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.10"
authors = [
    {name = "Fábio Lopes"}
]
keywords = ["youtube", "obsidian", "ai", "transcription", "knowledge-management"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "yt-dlp>=2023.0.0",
    "pyyaml>=6.0",
    "tiktoken>=0.5.0",
    "requests>=2.28.0",
    "tenacity>=8.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "mypy>=1.19",
    "coverage>=7.13",
]

[project.scripts]
ytobs = "ytobs.cli:main"

[tool.setuptools.packages.find]
include = ["ytobs*"]
```

**Note**: `pydantic` is NOT in dependencies (dead dep). `types-PyYAML`, `types-requests`, `annotated-types`, `typing-inspection`, `librt`, `iniconfig`, `packaging`, `pathspec`, `regex`, `urllib3`, `idna`, `certifi`, `charset-normalizer` are transitive deps — they come through `yt-dlp` and `requests`. Don't list them explicitly.

---

## Execution Checklist (29 items, ordered)

### PHASE 1: Copy & Structure (5 items)

```
[ ] 1. CREATE target directory
    mkdir -p ~/projetos/hub/ytobs

[ ] 2. COPY all files from source
    cp -a ~/projetos/hub/.myscripts/youtube-obsidian/{yt,yt-obsidian.py,md-html.py,lib,config.yaml,requirements.txt,CONTEXT.md,START_HERE.md,README.md,HELP.md,HELP_SHORT.txt,HELP_SUMMARY.txt,CONTRIBUTING.md,LICENSE,.gitignore,extropics-yt.html,docs,archive,reference} ~/projetos/hub/ytobs/
    
    DO NOT copy: __pycache__, .fabric/, .opencode/, .vscode/, node_modules/, .ruff_cache/
    DO NOT copy: venv/ (doesn't exist anyway — no venv in current state)

[ ] 3. REMOVE non-essential dirs from target
    rm -rf ~/projetos/hub/ytobs/__pycache__
    rm -rf ~/projetos/hub/ytobs/.fabric 2>/dev/null || true
    rm -rf ~/projetos/hub/ytobs/.opencode 2>/dev/null || true
    rm -rf ~/projetos/hub/ytobs/.vscode 2>/dev/null || true

[ ] 4. WRITE pyproject.toml
    Write the content from § pyproject.toml Specification above to ~/projetos/hub/ytobs/pyproject.toml

[ ] 5. CREATE the ytobs/ package directory by RENAMING lib/
    mv ~/projetos/hub/ytobs/lib ~/projetos/hub/ytobs/ytobs
```

### PHASE 2: Code Fixes (5 items)

```
[ ] 6. FIX ytobs/validator.py — absolute → relative import
    Open: ~/projetos/hub/ytobs/ytobs/validator.py
    Line 9: from lib.exceptions import ValidationError
    Replace with: from .exceptions import ValidationError

[ ] 7. UPDATE ytobs/__init__.py — add version
    Open: ~/projetos/hub/ytobs/ytobs/__init__.py
    Add: __version__ = "4.0.0"

[ ] 8. UPDATE all imports in ytobs/ package files
    All existing relative imports (from .xxx import ...) are already correct.
    All existing absolute imports (from lib.xxx import ...) need review:
    
    Files to check (grep for "from lib."):
    - ytobs/validator.py (already fixing in step 6)
    
    Files that are already relative (from .) — OK, no changes needed:
    - chunker.py, extractor.py, fabric_orchestrator.py, 
      metadata_extractor.py, packet_builder.py, rate_limiter.py,
      status_display.py, token_counter.py, transcript.py
      → All use "from .xxx import" or relative imports ✅

    RUN after moving lib/:
    grep -rn "from lib\." ~/projetos/hub/ytobs/ytobs/  # should return only validator.py

[ ] 9. CREATE ytobs/cli.py — migrate main() from yt script
    Copy the create_parser() function and main() entry point from the old yt script.
    Import from the package: from ytobs.config import load_config
    Import from the package: from ytobs.validator import validate_url
    etc.
    
    The old yt script had 1022 lines. Extract just the functions:
    - create_parser()
    - run_pattern_optimizer()
    - filter_patterns()
    - main() — the full pipeline
    
    Save to: ~/projetos/hub/ytobs/ytobs/cli.py

[ ] 10. DELETE the old yt script from root
    rm ~/projetos/hub/ytobs/yt
    rm ~/projetos/hub/ytobs/yt-obsidian.py   # legacy entry point
    (md-html.py can stay if it's a utility — or move to archive/)
```

### PHASE 3: Config & Shell Integration (3 items)

```
[ ] 11. UPDATE ~/.zshrc:129 — replace ytobs() shell function
    CURRENT (line ~129):
        ytobs() { (cd /Users/fabiofalopes/projetos/hub/.myscripts/youtube-obsidian && python3 yt "$@") }
    
    REPLACE WITH (after pip install):
        # ytobs is now pip-installed — no shell function needed
        # pip install -e ~/projetos/hub/ytobs
    
    Or keep as fallback:
        ytobs() { python3 -m ytobs.cli "$@"; }

[ ] 12. REMOVE .myscripts PATH from ~/.zshrc (if ytobs was the only reason)
    Check: ~/.zshrc line 149: export PATH=/Users/fabiofalopes/projetos/hub/.myscripts/:$PATH
    If ytobs was the only dependency on this PATH entry AND other extracted projects
    are also pip-installed, remove the line entirely.
    If other scripts in .myscripts still need it, keep it.

[ ] 13. CREATE venv and install
    cd ~/projetos/hub/ytobs
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
    pip install -e ".[dev]"  # if you want dev deps
```

### PHASE 4: Documentation (5 items)

```
[ ] 14. UPDATE CONTEXT.md — location header
    Line 5: **Location**: ~/projetos/hub/.myscripts/youtube-obsidian/
    Replace with: **Location**: ~/projetos/hub/ytobs/
    
    Plus any other .myscripts or youtube-obsidian references throughout the file.
    (There are ~21 references — run: grep -n "myscripts\|youtube-obsidian" CONTEXT.md)

[ ] 15. UPDATE START_HERE.md — location header
    Line 5: **Location:** ~/projetos/hub/.myscripts/youtube-obsidian/
    Replace with: **Location:** ~/projetos/hub/ytobs/

[ ] 16. UPDATE SETUP.md — old paths
    Remove references to ~/projetos/rascunhos/yt-dlp-tests (old location).
    Replace with pip install instructions.

[ ] 17. UPDATE README.md — add pip install section
    Add to README.md:
        ## Install
        pip install -e ~/projetos/hub/ytobs

[ ] 18. SCAN all docs/ for .myscripts strings
    grep -rn "myscripts\|youtube-obsidian" ~/projetos/hub/ytobs/docs/
    Update any path references found.
```

### PHASE 5: Cleanup & Test (8 items)

```
[ ] 19. CREATE fresh requirements.txt with loosened versions
    Write to ~/projetos/hub/ytobs/requirements.txt:
        yt-dlp>=2023.0.0
        pyyaml>=6.0
        tiktoken>=0.5.0
        requests>=2.28.0
        tenacity>=8.0.0
    
    DO NOT include: pydantic, coverage, mypy, pytest, pytest-cov,
    types-PyYAML, types-requests (these are dev tools or transitive deps).

[ ] 20. VERIFY .gitignore is appropriate
    Should already cover: __pycache__/, .fabric/, .vscode/, venv/, *.pyc
    Add: dist/, build/, *.egg-info/

[ ] 21. TEST 1: ytobs --help
    ytobs --help
    Expected: full argparse help output with subcommands (status, vault, channel)

[ ] 22. TEST 2: ytobs --version
    ytobs --version
    Expected: "ytobs 4.0.0"

[ ] 23. TEST 3: ytobs --list-processed
    ytobs --list-processed
    Expected: list of 76 cached videos from $OBSVAULT/youtube/.cache/

[ ] 24. TEST 4: ytobs --preview (end-to-end)
    ytobs --preview "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    Expected: Shows pattern recommendations without making API calls.
    This tests: URL validation, yt-dlp extraction, pattern_optimizer, cache check.

[ ] 25. VERIFY config auto-creation
    Delete: rm -rf ~/.yt-obsidian/config.yml
    Run: ytobs --help
    Check: ls ~/.yt-obsidian/config.yml
    Expected: config file auto-created on first run.

[ ] 26. VERIFY OBSVAULT env var
    echo $OBSVAULT
    Should be set to ~/Documents/obsidian_vault
    If not: export OBSVAULT=~/Documents/obsidian_vault
```

### PHASE 6: Final Validation (3 items)

```
[ ] 27. CLEANUP old location
    After confirming everything works in hub/ytobs/:
    rm -rf ~/projetos/hub/.myscripts/youtube-obsidian/
    
    BUT KEEP: HANDOFF_ytobs_extraction.md as a record of what was done.
    Move it to ~/projetos/hub/ytobs/archive/ after cleanup.

[ ] 28. UPDATE MYSCRIPTS_AUDIT_AND_EXTRACTION_PLAN.md
    Mark youtube-obsidian as ✅ EXTRACTED in the audit doc.

[ ] 29. GIT INIT (optional)
    cd ~/projetos/hub/ytobs
    git init
    git add .
    git commit -m "Initial extraction from .myscripts — ytobs V4.0.0"
```

---

## File Mapping: Before → After

| Before (in .myscripts/youtube-obsidian) | After (in hub/ytobs) | Action |
|------------------------------------------|---------------------|--------|
| `lib/` (18 files) | `ytobs/` (18 files + 1 new cli.py) | **Rename** then add cli.py |
| `yt` (1022 lines, main entry) | `ytobs/cli.py` | **Migrate** code, then delete old yt |
| `yt-obsidian.py` (legacy) | `archive/deprecated/` | **Move** to archive |
| `md-html.py` | `ytobs/md_html.py` or `archive/` | Decide: utility or archive? |
| `config.yaml` | `config.yaml` | Keep at root |
| `requirements.txt` | `requirements.txt` | **Rewrite** (loosen, remove dead deps) |
| `CONTEXT.md` | `CONTEXT.md` | **Update** paths |
| `START_HERE.md` | `START_HERE.md` | **Update** paths |
| `SETUP.md` | `SETUP.md` | **Rewrite** for pip install |
| `README.md` | `README.md` | **Add** pip install section |
| `HELP.md`, `HELP_SHORT.txt`, `HELP_SUMMARY.txt` | Same | Keep as-is |
| `CONTRIBUTING.md` | Same | Keep as-is |
| `LICENSE` | Same | Keep as-is |
| `extropics-yt.html` | `archive/` | **Move** (standalone HTML, not core) |
| `docs/` (18 files) | `docs/` | **Keep**, update path refs |
| `archive/`, `reference/` | Same | Keep |
| `__pycache__/` | — | **Delete** |
| `.fabric/` | — | **Delete** |
| `.opencode/`, `.vscode/` | — | **Delete** |
| — | `pyproject.toml` | **NEW** file |
| — | `venv/` | **Create** (python3 -m venv) |

---

## Dependency Audit

### RUNTIME (keep in pyproject.toml)

| Package | Used By | Required |
|---------|---------|----------|
| `yt-dlp` | `extractor.py` | ✅ Yes |
| `PyYAML` | `config.py`, `filesystem.py` | ✅ Yes |
| `tiktoken` | `token_counter.py`, `chunker.py` | ✅ Yes |
| `requests` | `transcript.py` | ✅ Yes |
| `tenacity` | `rate_limiter.py` | ✅ Yes |

### TRANSITIVE (don't list — come through above)

`certifi`, `charset-normalizer`, `idna`, `urllib3` → come through `requests`
`regex` → comes through `tiktoken`

### DEAD (remove entirely)

| Package | Why Dead |
|---------|----------|
| `pydantic==2.12.5` | No file imports `pydantic`. Project uses `dataclasses`. |
| `pydantic_core==2.41.5` | Transitive of pydantic. |
| `annotated-types==0.7.0` | Transitive of pydantic. |
| `typing-inspection==0.4.2` | Transitive of pydantic. |

### DEV (move to [project.optional-dependencies] dev)

| Package | Used By |
|---------|---------|
| `pytest`, `pytest-cov` | Testing |
| `mypy`, `mypy_extensions` | Type checking |
| `coverage` | Test coverage |
| `types-PyYAML`, `types-requests` | Type stubs |

### UNCLEAR (review)

| Package | Usage |
|---------|-------|
| `librt==0.7.4` | Might be a macOS system lib? No Python import found. Likely spurious. |
| `iniconfig==2.3.0` | Transitive of pytest. Remove from explicit list. |
| `packaging==25.0` | Transitive of setuptools/pytest. Remove from explicit list. |
| `pathspec==0.12.1` | Might be transitive? No import found. Remove from explicit list. |
| `Pygments==2.19.2` | No import found. Remove from explicit list. |

---

## Known Non-Issues (Don't Fix)

1. **No tests directory**: Out of scope for extraction. Add tests later.
2. **yt-obsidian.py legacy script**: Move to `archive/deprecated/` — don't delete content, just archive it.
3. **md-html.py**: Standalone utility. Move to `archive/` or keep at root as a utility script.
4. **docs/ with old paths**: Update the location headers. Don't rewrite every historical session log — those are records.
5. **extropics-yt.html**: Standalone HTML file unrelated to core pipeline. Move to `archive/`.
6. **`.fabric/` directory**: Contains old AI analysis outputs. Not needed in new location.
7. **No `__version__` in `__init__.py`**: Add it. Currently empty file.

---

## Post-Extraction Verification Script

Run this after extraction to verify nothing is broken:

```bash
#!/bin/bash
# Save as ~/projetos/hub/ytobs/verify_extraction.sh
set -e

echo "=== ytobs extraction verification ==="

# 1. Package structure
echo -n "[1] Package directory exists... "
[ -d "$HOME/projetos/hub/ytobs/ytobs" ] && echo "✓" || echo "✗ FAIL"

# 2. pyproject.toml
echo -n "[2] pyproject.toml exists... "
[ -f "$HOME/projetos/hub/ytobs/pyproject.toml" ] && echo "✓" || echo "✗ FAIL"

# 3. No old yt script at root
echo -n "[3] Old yt script removed... "
[ ! -f "$HOME/projetos/hub/ytobs/yt" ] && echo "✓" || echo "✗ FAIL (still present)"

# 4. No lib/ (should be ytobs/)
echo -n "[4] lib/ renamed to ytobs/... "
[ ! -d "$HOME/projetos/hub/ytobs/lib" ] && echo "✓" || echo "✗ FAIL (still lib/)"

# 5. validator.py import fixed
echo -n "[5] validator.py uses relative import... "
grep -q "from .exceptions" "$HOME/projetos/hub/ytobs/ytobs/validator.py" && echo "✓" || echo "✗ FAIL"

# 6. No pydantic in dependencies
echo -n "[6] pydantic removed from deps... "
! grep -q "pydantic" "$HOME/projetos/hub/ytobs/pyproject.toml" && echo "✓" || echo "✗ FAIL"

# 7. Config auto-creation
echo -n "[7] Config file at ~/.yt-obsidian/config.yml... "
[ -f "$HOME/.yt-obsidian/config.yml" ] && echo "✓" || echo "✗ (will auto-create on first run)"

# 8. OBSVAULT
echo -n "[8] OBSVAULT env var... "
[ -n "$OBSVAULT" ] && echo "✓ ($OBSVAULT)" || echo "✗ NOT SET"

# 9. ytobs command works
echo -n "[9] ytobs --version... "
ytobs --version 2>/dev/null && echo "" || echo "✗ FAIL"

# 10. Cache intact
echo -n "[10] Video cache entries... "
COUNT=$(ls "$OBSVAULT/youtube/.cache/"* 2>/dev/null | wc -l)
echo "$COUNT entries"

echo "=== Verification complete ==="
```

---

## What NOT To Do

- ❌ Don't change `~/.yt-obsidian/config.yml` path — it's user config, should stay in home.
- ❌ Don't change `$OBSVAULT` env var usage — it's a system convention, not project-specific.
- ❌ Don't rewrite old session logs in CONTEXT.md or archive/ — they're historical records.
- ❌ Don't add `pydantic` to any new code — the project uses `dataclasses`.
- ❌ Don't create a setup.py — use pyproject.toml only (modern standard).
- ❌ Don't delete the source `.myscripts/youtube-obsidian/` until Phase 6 verification passes.
- ❌ Don't run `pip install` without `-e` during development — editable install is correct for local packages.

---

## Session Continuation

For the next session, the agent should load this file:

```
Load: ~/projetos/hub/ytobs/HANDOFF_ytobs_extraction.md
Start at: Phase 1, item 1
Stop at: Phase 6, item 29
```

Or if the extraction hasn't started yet (source still in .myscripts):

```
Load: ~/projetos/hub/.myscripts/youtube-obsidian/HANDOFF_ytobs_extraction.md
Start at: Phase 1, item 1
Stop at: Phase 6, item 29
```

---

## Reference

- Full audit of all .myscripts/ projects: `~/projetos/hub/.myscripts/MYSCRIPTS_AUDIT_AND_EXTRACTION_PLAN.md`
- ytobs project context: `CONTEXT.md` (856 lines of session history)
- ytobs quick start: `START_HERE.md`
- Architecture docs: `docs/architecture/`
- Development specs: `docs/development/`
