# V3.0 Development Session: Smart Cache & Incremental Updates

**Mission**: Implement intelligent caching system to eliminate duplicates and enable incremental pattern additions

**Context**: V2.1 is complete (rate limiting + multi-model fallback working). Now we need to prevent duplicate processing and enable building a scalable knowledge base.

**Location**: `~/projetos/rascunhos/yt-dlp-tests`

---

## 🎯 ONE SENTENCE GOAL

**Implement a cache system that skips re-processing existing videos, allows adding patterns to existing notes, and lays foundation for bulk video processing and knowledge base construction.**

---

## 📖 MUST READ FIRST

1. **VISION_V3_SMART_CACHE.md** (this session's output) - Complete vision, architecture, and requirements
2. **CONTEXT.md** - Project history and current state (V2.1 complete)
3. **lib/formatter.py** - Understand current markdown generation
4. **lib/filesystem.py** - Understand current file operations

---

## 🔥 THE PROBLEM (Quick Summary)

```bash
# Current behavior (BAD)
./yt "VIDEO_URL"   # Creates note
./yt "VIDEO_URL"   # Creates DUPLICATE (2).md  ❌
./yt "VIDEO_URL"   # Creates DUPLICATE (3).md  ❌

# Result: 41 files, 8 copies of same video, wasted API quota
```

**Root Cause**: No cache check before processing

---

## ✅ DESIRED BEHAVIOR

```bash
# First run
./yt "VIDEO_URL"
# ✅ Created: 2005-04-24_me_at_the_zoo.md (5 patterns, 9.8s)

# Second run (default - NEW BEHAVIOR)
./yt "VIDEO_URL"
# ⏭️  SKIPPED: Already exists (0.1s, 0 API calls)
# 💡 Use --append to add patterns or --force to re-run

# Add more patterns (incremental)
./yt --append --patterns extract_questions extract_ideas "VIDEO_URL"
# 📝 APPENDING to existing note (2 new patterns, 1 min)
# ✅ Added: extract_questions, extract_ideas

# Update metadata (video changed)
./yt --update "VIDEO_URL"
# 🔄 UPDATING metadata (5s, 0 AI calls)

# Force re-run (testing)
./yt --force "VIDEO_URL"
# 🔥 FORCE: Re-running full analysis
```

---

## 🏗️ ARCHITECTURE OVERVIEW

### New Phase 0: Cache Check (BEFORE everything else)

```python
def process_video(url: str, mode: str, flags: dict):
    # PHASE 0: Check cache (NEW!)
    video_id = extract_video_id(url)
    cache = CacheManager()
    
    if cache.exists(video_id):
        if flags.get('force'):
            cache.invalidate(video_id)
            # Continue to Phase 1
        elif flags.get('update'):
            return update_metadata_only(video_id)
        elif flags.get('append'):
            return append_patterns(video_id, flags['patterns'])
        else:
            # DEFAULT: Skip
            existing_note = cache.get_note_path(video_id)
            print(f"⏭️  SKIPPED: Already exists")
            print(f"   📄 {existing_note}")
            return existing_note
    
    # PHASE 1: Metadata extraction (existing)
    metadata = extract_metadata(url)
    
    # PHASE 2: Core analysis (existing)
    result = run_fabric_analysis(metadata, mode)
    
    # Save cache (NEW!)
    cache.save(video_id, {
        'metadata': metadata,
        'patterns_run': result.patterns,
        'chunks': result.chunks,
        'note_path': result.note_path
    })
    
    return result.note_path
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Step 1: Create CacheManager (lib/cache_manager.py)

**Priority**: HIGH  
**Time**: 2-3 hours  
**Complexity**: Medium

```python
# lib/cache_manager.py (NEW FILE)

from pathlib import Path
import json
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

@dataclass
class CacheEntry:
    """Per-video cache entry"""
    video_id: str
    video_url: str
    title: str
    upload_date: str
    duration_seconds: int
    transcript_word_count: int
    markdown_path: str
    last_updated: str
    patterns_run: List[str]
    processing_history: List[Dict]
    
class CacheManager:
    """Manages video processing cache"""
    
    def __init__(self, cache_dir: Path):
        """Initialize cache manager
        
        Args:
            cache_dir: Directory for cache files 
                       (e.g., $OBSVAULT/youtube/.cache)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._load_index()
    
    def exists(self, video_id: str) -> bool:
        """Check if video already processed"""
        return video_id in self.index['videos']
    
    def get_cache(self, video_id: str) -> Optional[CacheEntry]:
        """Load cache for video"""
        if not self.exists(video_id):
            return None
        
        cache_file = self.cache_dir / f"{video_id}.json"
        with open(cache_file) as f:
            data = json.load(f)
        return CacheEntry(**data)
    
    def save_cache(self, video_id: str, entry: CacheEntry):
        """Save cache entry"""
        cache_file = self.cache_dir / f"{video_id}.json"
        with open(cache_file, 'w') as f:
            json.dump(asdict(entry), f, indent=2)
        
        # Update index
        self.index['videos'][video_id] = {
            'title': entry.title,
            'markdown_path': entry.markdown_path,
            'last_processed': entry.last_updated,
            'patterns_count': len(entry.patterns_run)
        }
        self._save_index()
    
    def get_note_path(self, video_id: str) -> Optional[str]:
        """Get markdown note path for video"""
        cache = self.get_cache(video_id)
        return cache.markdown_path if cache else None
    
    def get_patterns_run(self, video_id: str) -> List[str]:
        """Get patterns already run on video"""
        cache = self.get_cache(video_id)
        return cache.patterns_run if cache else []
    
    def append_patterns(self, video_id: str, new_patterns: List[str]):
        """Append new patterns to cache"""
        cache = self.get_cache(video_id)
        if not cache:
            return
        
        cache.patterns_run.extend(new_patterns)
        cache.last_updated = datetime.now().isoformat()
        
        # Add to history
        cache.processing_history.append({
            'timestamp': cache.last_updated,
            'mode': 'append',
            'patterns_appended': new_patterns
        })
        
        self.save_cache(video_id, cache)
    
    def invalidate(self, video_id: str):
        """Delete cache for video"""
        cache_file = self.cache_dir / f"{video_id}.json"
        if cache_file.exists():
            cache_file.unlink()
        
        if video_id in self.index['videos']:
            del self.index['videos'][video_id]
            self._save_index()
    
    def _load_index(self):
        """Load index file"""
        if self.index_file.exists():
            with open(self.index_file) as f:
                self.index = json.load(f)
        else:
            self.index = {
                'version': '3.0',
                'last_updated': datetime.now().isoformat(),
                'videos': {}
            }
    
    def _save_index(self):
        """Save index file"""
        self.index['last_updated'] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
```

**Testing**:
```python
# Test cache manager
cache = CacheManager(Path("~/Documents/obsidian_vault/youtube/.cache"))

# Save entry
entry = CacheEntry(
    video_id="jNQXAC9IVRw",
    video_url="https://...",
    title="Me at the zoo",
    upload_date="2005-04-24",
    duration_seconds=19,
    transcript_word_count=39,
    markdown_path="2005-04-24_me_at_the_zoo.md",
    last_updated=datetime.now().isoformat(),
    patterns_run=["extract_wisdom", "youtube_summary"],
    processing_history=[...]
)
cache.save_cache("jNQXAC9IVRw", entry)

# Check exists
assert cache.exists("jNQXAC9IVRw") == True

# Get patterns
patterns = cache.get_patterns_run("jNQXAC9IVRw")
assert "extract_wisdom" in patterns
```

---

### Step 2: Integrate Cache Check into Main Flow

**Priority**: HIGH  
**Time**: 1-2 hours  
**Complexity**: Low

**File**: `yt` (main CLI script)

**Changes Needed**:

```python
# Around line 100-150 (where processing starts)

# NEW: Initialize cache manager
cache = CacheManager(Path(config['output_dir']) / '.cache')

# NEW: Check cache before processing
if cache.exists(video_id):
    if args.force:
        print(f"🔥 FORCE: Ignoring cache, re-running analysis")
        cache.invalidate(video_id)
    elif args.update:
        print(f"🔄 UPDATING metadata for {video_id}")
        return update_metadata_only(video_id, cache)
    elif args.append:
        print(f"📝 APPENDING patterns to existing note")
        return append_patterns_to_note(video_id, args.patterns, cache)
    else:
        # DEFAULT: Skip
        note_path = cache.get_note_path(video_id)
        patterns = cache.get_patterns_run(video_id)
        print(f"⏭️  SKIPPED: Note already exists for {video_id}")
        print(f"   📄 Existing: {note_path}")
        print(f"   📊 Patterns: {len(patterns)} ({', '.join(patterns[:3])}...)")
        print(f"   💡 Tip: Use --append to add patterns or --force to re-run")
        return note_path

# Continue with normal processing...
```

---

### Step 3: Add New CLI Flags

**Priority**: HIGH  
**Time**: 30 min  
**Complexity**: Low

**File**: `yt`

```python
# Add to argument parser (around line 20-50)

parser.add_argument('--append', action='store_true',
    help='Append new patterns to existing note')

parser.add_argument('--update', action='store_true',
    help='Update metadata only (fast, no AI analysis)')

parser.add_argument('--force', action='store_true',
    help='Force re-analysis (ignore cache)')

parser.add_argument('--list-processed', action='store_true',
    help='Show all processed videos')

# Mutually exclusive group
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument('--skip-existing', action='store_true', default=True,
    help='Skip if note exists (DEFAULT)')
```

---

### Step 4: Implement Incremental Writer

**Priority**: HIGH  
**Time**: 2-3 hours  
**Complexity**: Medium

**File**: `lib/incremental_writer.py` (NEW)

```python
# lib/incremental_writer.py

from pathlib import Path
from typing import Dict, List
import re

class IncrementalWriter:
    """Append sections to existing markdown notes"""
    
    def __init__(self, note_path: Path):
        self.note_path = Path(note_path)
        self.content = self._load_note()
        self.frontmatter, self.body = self._parse_note()
    
    def _load_note(self) -> str:
        """Load existing note"""
        return self.note_path.read_text()
    
    def _parse_note(self) -> tuple[str, str]:
        """Split frontmatter and body"""
        parts = self.content.split('---')
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = '---'.join(parts[2:])
            return frontmatter, body
        return "", self.content
    
    def append_section(self, heading: str, content: str):
        """Append new section to note"""
        # Add section at end of AI Analysis area
        # (before any future sections like References)
        section = f"\n\n## {heading}\n\n{content}\n"
        self.body += section
    
    def update_frontmatter(self, updates: Dict):
        """Update YAML frontmatter"""
        # Parse current frontmatter
        # Add new patterns to list
        # Update last_updated timestamp
        pass  # Implementation needed
    
    def save(self):
        """Save updated note"""
        new_content = f"---\n{self.frontmatter}\n---{self.body}"
        self.note_path.write_text(new_content)
```

**Usage**:
```python
# Append new patterns to existing note
writer = IncrementalWriter(note_path)

for pattern in new_patterns:
    result = run_fabric_pattern(pattern, chunks)
    writer.append_section(f"AI Analysis - {pattern}", result.output)

writer.update_frontmatter({'patterns': existing + new_patterns})
writer.save()
```

---

### Step 5: Implement Update & Append Functions

**Priority**: HIGH  
**Time**: 2 hours  
**Complexity**: Medium

**File**: `yt` or new `lib/update_operations.py`

```python
def update_metadata_only(video_id: str, cache: CacheManager):
    """Update metadata without re-running AI analysis
    
    Fast operation: ~5s, 0 API calls
    Updates: views, likes, comments, description
    """
    # Re-fetch video metadata
    video_info = extract_video_metadata(video_id)
    
    # Load existing note
    cache_entry = cache.get_cache(video_id)
    note_path = Path(cache_entry.markdown_path)
    
    # Update frontmatter only
    content = note_path.read_text()
    # Replace frontmatter with updated metadata
    # Keep all AI analysis sections intact
    
    print(f"✅ Updated metadata: views, likes, description")
    return note_path


def append_patterns_to_note(video_id: str, new_patterns: List[str], cache: CacheManager):
    """Append new patterns to existing note
    
    Incremental operation: Only runs new patterns
    Preserves all existing analysis
    """
    cache_entry = cache.get_cache(video_id)
    
    # Check which patterns are new
    existing_patterns = cache_entry.patterns_run
    patterns_to_run = [p for p in new_patterns if p not in existing_patterns]
    
    if not patterns_to_run:
        print(f"⏭️  All patterns already run on this video")
        return cache_entry.markdown_path
    
    print(f"📝 APPENDING {len(patterns_to_run)} new pattern(s)")
    print(f"   Existing: {len(existing_patterns)} patterns")
    print(f"   New: {', '.join(patterns_to_run)}")
    
    # Load cached chunks (so we don't re-chunk)
    chunks = cache_entry.chunks  # Stored in cache
    
    # Run only new patterns
    writer = IncrementalWriter(cache_entry.markdown_path)
    
    for pattern in patterns_to_run:
        print(f"\n   Pattern: {pattern}")
        result = run_fabric_pattern(pattern, chunks)
        writer.append_section(f"AI Analysis - {pattern}", result.output)
    
    writer.update_frontmatter({'patterns': existing_patterns + patterns_to_run})
    writer.save()
    
    # Update cache
    cache.append_patterns(video_id, patterns_to_run)
    
    print(f"✅ Appended {len(patterns_to_run)} new sections")
    return cache_entry.markdown_path
```

---

### Step 6: Save Cache After Processing

**Priority**: HIGH  
**Time**: 1 hour  
**Complexity**: Low

**File**: `yt` (at end of successful processing)

```python
# After Phase 2 completes successfully

# Save to cache (NEW!)
cache_entry = CacheEntry(
    video_id=video_id,
    video_url=url,
    title=video_info['title'],
    upload_date=video_info['upload_date'],
    duration_seconds=video_info['duration'],
    transcript_word_count=len(transcript.split()),
    markdown_path=output_path,
    last_updated=datetime.now().isoformat(),
    patterns_run=patterns,
    processing_history=[{
        'timestamp': datetime.now().isoformat(),
        'mode': mode,
        'model': model,
        'patterns_run': patterns,
        'chunks_created': len(packets),
        'success': True
    }]
)

cache.save_cache(video_id, cache_entry)
print(f"💾 Cached analysis for future runs")
```

---

## 🧪 TESTING STRATEGY

### Test 1: Basic Cache Functionality

```bash
# Clean start
rm -rf ~/Documents/obsidian_vault/youtube/.cache

# First run - should create note AND cache
./yt --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# ✅ Creates: 2005-04-24_me_at_the_zoo.md
# ✅ Creates: .cache/jNQXAC9IVRw.json

# Second run - should skip
./yt --quick "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# ⏭️  SKIPPED: Note already exists
```

### Test 2: Append Functionality

```bash
# Add more patterns to existing note
./yt --append --patterns extract_questions extract_ideas "SAME_URL"
# 📝 APPENDING 2 new patterns
# ✅ Appended 2 new sections

# Verify note has new sections
grep "extract_questions" ~/Documents/obsidian_vault/youtube/2005-04-24_me_at_the_zoo.md
```

### Test 3: Force Re-run

```bash
# Force re-analysis
./yt --force --quick "SAME_URL"
# 🔥 FORCE: Re-running full analysis
# ✅ Created new note (replaces old)
```

### Test 4: Migration (Existing Notes)

```bash
# Scan existing notes and populate cache
./yt --migrate
# 📊 Found 41 existing notes
# 💾 Created cache entries for 41 videos
# ⚠️  8 duplicates detected (can be cleaned up)
```

---

## 📊 SUCCESS CRITERIA

Before marking complete, verify:

- ✅ No duplicate notes created on re-run
- ✅ Default behavior skips existing (with helpful message)
- ✅ --append adds patterns without full re-run
- ✅ --update refreshes metadata quickly (<5s)
- ✅ --force works (re-runs everything)
- ✅ Cache survives restarts
- ✅ Cache index loads fast (<0.1s)
- ✅ Incremental append preserves existing content
- ✅ Frontmatter updated correctly

---

## 🚨 IMPORTANT NOTES

1. **Cache Location**: `$OBSVAULT/youtube/.cache/` (inside vault, not tracked by git)

2. **Cache Key**: Always use `video_id`, NOT filename (handles duplicates)

3. **Backward Compatibility**: Old behavior available with `--force`

4. **Error Handling**: If cache corrupt, log warning and re-process

5. **Migration**: Need script to scan existing notes → populate cache

6. **Testing**: Use different videos, don't pollute vault more

---

## 🎓 DEVELOPMENT WORKFLOW

```bash
# 1. Setup
cd ~/projetos/rascunhos/yt-dlp-tests
source venv/bin/activate

# 2. Create CacheManager
touch lib/cache_manager.py
# Implement class...

# 3. Test cache manager standalone
python3 -c "from lib.cache_manager import CacheManager; ..."

# 4. Integrate into main flow
vim yt
# Add cache check before processing

# 5. Test end-to-end
./yt --quick "SHORT_VIDEO_URL"  # First run
./yt --quick "SAME_URL"          # Should skip

# 6. Implement append
vim lib/incremental_writer.py
# Test append functionality

# 7. Clean up duplicates
# (Optional cleanup script)
```

---

## 💬 QUESTIONS TO RESOLVE DURING DEVELOPMENT

1. **Chunk Storage**: Store chunks in cache or re-compute for --append?
   - **Recommendation**: Store in cache (avoid re-chunking)

2. **Duplicate Handling**: What to do with existing (2).md files?
   - **Recommendation**: Migration script detects + offers to delete

3. **Cache Size**: Will cache get too large?
   - **Estimate**: 10KB per video × 1000 videos = 10MB (fine)

4. **Front Matter**: Which fields to update on --update?
   - **Recommendation**: views, likes, comments, last_updated

5. **Pattern Order**: Append at end or sort alphabetically?
   - **Recommendation**: Append at end (chronological)

---

## 📚 RELATED DOCUMENTATION

- **VISION_V3_SMART_CACHE.md** - Complete vision and future plans
- **CONTEXT.md** - Current project state (V2.1)
- **MULTI_MODEL_FALLBACK.md** - Understanding rate limiting (V2.1)
- **lib/formatter.py** - Current markdown generation
- **lib/fabric_orchestrator.py** - Pattern execution flow

---

## 🚀 READY TO START?

```bash
# Copy-paste to begin:
cd ~/projetos/rascunhos/yt-dlp-tests
source venv/bin/activate

# Read this prompt
cat DEVELOPER_PROMPT_V3.md

# Read the vision
cat VISION_V3_SMART_CACHE.md

# Start with CacheManager
touch lib/cache_manager.py
vim lib/cache_manager.py
```

**Your mission**: Implement V3.0 so we can process hundreds of videos efficiently without duplicates! 🎯
