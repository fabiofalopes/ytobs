# Stability Audit Report — ytobs

**Date**: 2026-06-13
**Scope**: Full codebase audit for crash risks, missing error handling, hanging subprocess calls, and iCloud/EPERM vulnerabilities.
**Context**: Triggered by recurring `[Errno 1] Operation not permitted` crash on cache writes inside iCloud-synced vault path.

---

## Executive Summary

| Category | Critical | Moderate | Low | Resolved |
|----------|----------|----------|-----|----------|
| File I/O (EPERM/crash) | 3 | 8 | 5 | 3 (cache fix) |
| Subprocess (hang/no-timeout) | 3 | 3 | 0 | 0 |
| Dead code | 0 | 0 | 0 | 2 functions |
| **Total action items** | **6** | **11** | **5** | **3** |

The cache EPERM crash was the symptom. The audit found **19 more unguarded file-write sites** and **3 subprocess calls with no timeout** that could hang forever. Most latent paths are dormant (gated by `save_dir=None`), but `incremental_writer.py` and `cli.py:233` are live vulnerabilities on common user paths.

---

## PART 1: File I/O Vulnerabilities

### The Pattern

Every crash shares the same root cause: **bare `Path.write_text()` / `Path.read_text()` / `Path.mkdir()` without try/except**. When macOS/iCloud intermittently denies access with EPERM, these crash the entire tool instead of degrading gracefully.

The fix is already proven in `cache_manager.py` — `_atomic_write()` and `_atomic_read()` with retry + backoff + graceful failure.

### P0 — CRITICAL (live on common user paths)

| # | File | Line | Code | Why It's Critical |
|---|------|------|------|-------------------|
| 1 | `incremental_writer.py` | 32 | `self.note_path.read_text()` | Bare read of note inside vault. Called during `--append` flow. EPERM crashes tool. |
| 2 | `incremental_writer.py` | 110 | `self.note_path.write_text()` | Bare write to note inside vault. Called during `--append` flow. EPERM crashes tool. |
| 3 | `incremental_writer.py` | 24 | `self.note_path.exists()` | TOCTOU race + bare exists() can EPERM on iCloud dirs. |

**Fix**: Wrap `_load_note()` and `save()` in try/except. Return success/failure boolean from `append_patterns_to_note()`. Print user-facing warning on failure.

### P1 — HIGH (unguarded but currently dormant)

These are gated by `save_dir` which is **always `None`** in production. They become live the moment `keep_temp_files` is implemented.

| # | File | Lines | What | Gate |
|---|------|-------|------|------|
| 4 | `fabric_orchestrator.py` | 636 | `pattern_dir.mkdir()` | `if self.save_dir:` |
| 5 | `fabric_orchestrator.py` | 640 | `combined_path.write_text()` | `if self.save_dir:` |
| 6 | `fabric_orchestrator.py` | 654 | `raw_combined_path.write_text()` | `if self.save_dir:` |
| 7 | `fabric_orchestrator.py` | 659 | `chunk_path.write_text()` | `if self.save_dir:` |
| 8 | `chunker.py` | 219 | `packets_dir.mkdir()` | `if save_dir:` |
| 9 | `chunker.py` | 225 | `packet_path.write_text()` | `if save_dir:` |
| 10 | `chunker.py` | 244 | `metadata_path.write_text()` | `if save_dir:` |
| 11 | `metadata_extractor.py` | 235 | `save_path.parent.mkdir()` | `if save_path:` |
| 12 | `metadata_extractor.py` | 236 | `save_path.write_text()` | `if save_path:` |

**Fix**: If `save_dir` is ever set, it MUST resolve outside `$OBSVAULT`. Add a guard at the top of each function. Consider extracting `_atomic_write` to a shared utility.

### P2 — MODERATE (unguarded writes, user-controlled paths)

| # | File | Line | Code | Risk |
|---|------|------|------|------|
| 13 | `channel.py` | 212 | `output_path.write_text()` | User-supplied `--export FILE` path. If dir doesn't exist or read-only, crashes. |
| 14 | `config.py` | 180 | `config_dir.mkdir()` in `ensure_config_dir()` | Unguarded. If `~/.yt-obsidian` can't be created, crashes. |
| 15 | `config.py` | 318 | `cache_dir.mkdir()` (temp fallback) | Unguarded fallback in `get_cache_dir()`. |
| 16 | `cache_manager.py` | 36 | `parent.mkdir()` in `_atomic_write()` | Before the try block — partially unguarded. |
| 17 | `cache_manager.py` | 162 | `self.cache_dir.mkdir()` in constructor | Unguarded. |
| 18 | `cache_manager.py` | 252 | `self._save_index()` return ignored | `invalidate()` discards bool result. |

### P3 — LOW (intentional vault writes, already guarded)

| # | File | Line | Code | Notes |
|---|------|------|------|-------|
| 19 | `filesystem.py` | 126, 138 | `mkdir()` + `write_text()` | ✅ Already wrapped in try/except → `FileSystemError`. Intentional vault write. |
| 20 | `config.py` | 190 | `open(config_path, 'w')` | Caller `load_config()` has try/except. Safe enough. |

---

## PART 2: Subprocess & External Command Vulnerabilities

### P0 — CRITICAL (no timeout, can hang forever)

| # | File | Line | Command | Issue |
|---|------|------|---------|-------|
| 1 | `cli.py` | 233 | `subprocess.run([fabric-ai, --pattern, pattern_optimizer], ...)` | **No timeout.** If Groq API hangs, fabric-ai hangs, this hangs, tool hangs forever. Also: no try/except for `FileNotFoundError` (fabric-ai not installed). |
| 2 | `cli.py` | 542 | `subprocess.run([ytobs, video.url])` | **No timeout.** Recursive ytobs self-invocation during channel processing. If child hangs, parent hangs. |
| 3 | `fabric_orchestrator.py` | 466 | `subprocess.Popen([fabric-ai, ...])` streaming | `for line in process.stdout` is a **blocking iterator** that runs before `process.wait(timeout=...)`. If fabric-ai produces no output, the loop never reaches the wait() timeout. |

**Fix #1**: Add `timeout=120`, wrap in try/except `FileNotFoundError`, `subprocess.TimeoutExpired`.
**Fix #2**: Add `timeout=300`.
**Fix #3**: Use `select.select([process.stdout], [], [], timeout)` in a loop, or `threading.Timer` to kill process.

### P1 — MODERATE (has timeout, missing exception handling)

| # | File | Line | Command | Issue |
|---|------|------|---------|-------|
| 4 | `channel.py` | 83 | `subprocess.run([yt-dlp, --flat-playlist, ...])` | Has `timeout=60`. No try/except for `FileNotFoundError` (yt-dlp missing) or `TimeoutExpired`. |
| 5 | `channel.py` | 142 | `subprocess.run([yt-dlp, --flat-playlist, --print, ...])` | Has `timeout=30`. Same missing exception handling. |
| 6 | `cli.py` | 967 | `subprocess.run([open, output_path])` | No timeout, no error check. Low risk (macOS `open` is async). |

**Fix**: Wrap #4 and #5 in try/except `FileNotFoundError` → `CommandNotFoundError`, `TimeoutExpired` → `NetworkError`.

### P2 — GOOD (reference implementations)

| # | File | Line | Command | Status |
|---|------|------|---------|--------|
| 7 | `rate_limiter.py` | 374 | `subprocess.run([fabric-ai, ...])` | ✅ Timeout, returncode check, stderr, try/except, retry with backoff. **BEST IN CODEBASE.** |
| 8 | `transcript.py` | 113 | `requests.get(subtitle_url)` | ✅ Timeout=10, `raise_for_status()`, try/except. Minor: no retry. |

### Dead Code

| File | Lines | What | Status |
|------|-------|------|--------|
| `extractor.py` | 186-214 | `_run_yt_dlp()` + `_build_command()` | Defined but never called. `extract_metadata()` uses yt-dlp Python API instead. **Delete or wire up.** |

---

## PART 3: iCloud / Vault Path Assessment

### Cache Migration: ✅ COMPLETE
- **Before**: `$OBSVAULT/youtube/.cache/` (inside iCloud-synced `~/Documents/`)
- **After**: `~/.yt-obsidian/cache/` (outside vault, no iCloud interference)
- All `Path.home()` references resolve to `~/.yt-obsidian/` — safe.

### Active Writes Inside Vault (INTENTIONAL)
1. `filesystem.py:126,138` — Final `.md` notes at `$OBSVAULT/youtube/` ✅
2. `incremental_writer.py:110` — Appending to existing notes ✅

These are intentional — the vault is the output destination. But they still need error handling (see P0 items above).

### Ticking Bomb: `keep_temp_files` config field
- **config.py:25** — `keep_temp_files: bool = False` — parsed from YAML
- **NEVER consumed** — `cli.py` never reads this field to set `save_dir`
- If implemented naively (`save_dir = output_dir`), all P1 dormant paths become live EPERM crashes
- **Recommendation**: If implementing, `save_dir` MUST resolve outside `$OBSVAULT`

### No Hardcoded Paths
No `~/Documents/` or `/Users/` hardcoded in any `.py` file. All vault references go through `$OBSVAULT` env var. ✅

---

## PART 4: Recommended Fix Order

### Sprint 1 — Stop the Bleeding (30 min)

**Goal**: Eliminate all crash-on-EPERM and hang-forever scenarios.

| Priority | File | What to Do | Est. Time |
|----------|------|------------|-----------|
| P0 | `incremental_writer.py` | Wrap `_load_note()` and `save()` in try/except. Return bool from `append_patterns_to_note()`. | 10 min |
| P0 | `cli.py:233` | Add `timeout=120` to pattern_optimizer subprocess.run. Wrap in try/except. | 5 min |
| P0 | `cli.py:542` | Add `timeout=300` to channel ytobs subprocess.run. | 2 min |
| P0 | `fabric_orchestrator.py:466` | Add timeout to streaming stdout read loop (use `select` or threading). | 10 min |

### Sprint 2 — Harden the Perimeter (30 min)

**Goal**: Make all remaining I/O resilient.

| Priority | File | What to Do | Est. Time |
|----------|------|------------|-----------|
| P2 | `channel.py:212` | Wrap export write_text in try/except. | 5 min |
| P2 | `channel.py:83,142` | Wrap both yt-dlp subprocess calls in try/except. | 10 min |
| P2 | `config.py:180,318` | Wrap mkdir calls in try/except with fallback. | 5 min |
| P2 | `cache_manager.py:36,162` | Move mkdir inside try blocks. | 5 min |
| P2 | `cache_manager.py:252` | Check `_save_index()` return in `invalidate()`. | 2 min |

### Sprint 3 — Clean Up (15 min)

| Priority | File | What to Do | Est. Time |
|----------|------|------------|-----------|
| LOW | `extractor.py:186-214` | Delete dead code (`_run_yt_dlp`, `_build_command`). | 5 min |
| LOW | `cli.py:967` | Add timeout=10 to `open` subprocess, ignore errors. | 2 min |
| LOW | Extract `_atomic_write`/`_atomic_read` from cache_manager.py into a shared `io_utils.py` module for reuse across all files. | 10 min |

### Sprint 4 — Future-Proof (if `keep_temp_files` is implemented)

- Ensure `save_dir` resolves outside `$OBSVAULT`
- Add startup guard: warn if `save_dir` is inside vault path
- All dormant P1 sites need the same `_atomic_write` treatment

---

## Appendix: Existing Error Hierarchy

```
YTObsidianError (base)
├── VideoUnavailableError
├── AgeRestrictedError
├── NetworkError
├── RateLimitError
├── ExtractionError
├── FileSystemError
├── CommandNotFoundError
└── ValidationError
```

All exceptions are defined in `exceptions.py` but used inconsistently. `FileSystemError` is used in `filesystem.py` but not in `incremental_writer.py`, `channel.py`, or `config.py`.
