# 01 — Current State: txrefine & the ytobs Pipeline

**Question answered**: What exists TODAY, how does it work, and what's broken?

---

## A. The Existing txrefine (bash script)

**Location**: `~/.myscripts/txrefine` (205 lines, ~5.5KB)
**Architecture**: 2-stage sequential prompt pipeline over stdin → stdout

```
stdin (raw transcript)
    │
    ▼
┌─────────────────────────────────────────┐
│ STAGE 1: transcript-analyzer            │
│   fabric-ai -p transcript-analyzer      │
│   Input:  raw transcript                │
│   Output: structured QUALITY REPORT     │
│   (issues found, fixes needed,          │
│    repeated words, fillers, tech terms) │
└─────────────────────────────────────────┘
    │
    ▼  (raw transcript + analysis report combined)
┌─────────────────────────────────────────┐
│ STAGE 2: transcript-refiner             │
│   fabric-ai -p transcript-refiner       │
│   Input:  raw + analysis                │
│   Output: REFINED PLAIN TEXT            │
│   (typos fixed, formatted, NO backticks)│
└─────────────────────────────────────────┘
    │
    ▼
stdout (refined text) + clipboard copy
```

### Design Principles (worth preserving)

1. **Analyze-then-fix** — Stage 1 diagnoses without touching text; Stage 2 applies fixes. This separation is research-validated (see `03-research-findings.md`).
2. **Conservative editing** — sacred rules in the refiner pattern:
   - NEVER change meaning, add info, or remove content
   - NEVER fix grammar if that's how the speaker talks
   - NEVER make casual speech formal
   - NEVER use backticks/markdown (terminal-friendly plain text)
3. **Pipe-friendly** — status/progress → stderr, only refined text → stdout. Enables `voicenote | txrefine | obsidian-polish`.
4. **Word-list support** — Stage 2 can receive a pre-supplied terminology list.
5. **Optional model selection** — `OR_MODEL_SELECT=1` env var triggers `or-model-select` for data-driven model picking.

### The Two Fabric Patterns

Both live in `~/.myscripts/fabric-custom-patterns/` as standard Fabric patterns (`system.md` files):

| Pattern | Lines | Role |
|---------|-------|------|
| `transcript-analyzer/system.md` | 185 | Analyzer only — outputs a diagnostic report, never modifies text. Sections: Issues Found, Specific Fixes Needed (Repeated Words, Punctuation, Filler Words, Technical Terms, Formatting), Summary. |
| `transcript-refiner/system.md` | 220 | Applies fixes from the analysis report. 5 detailed examples. Strict output: refined text only, no meta-commentary. |

**Key property**: Both prompts are **pure markdown** — no YAML frontmatter, no Fabric-specific structure. They are 100% portable to any LLM system (OpenCode, raw API calls, etc.).

---

## B. The Known Bug (Why txrefine Doesn't Work Today)

**Source**: `~/.myscripts/fabric-custom-patterns/DEV-transcription-refinement-session-summary.md`

> **Status: Proof of concept — NOT WORKING RELIABLY**

### The Failure Mode

The refiner (Stage 2) **outputs example text from the prompt instead of processing the actual input**. When you pipe in a real transcript, you get back a lightly-modified version of one of the 5 examples that live in `system.md`.

### Root Causes (identified in dev notes)

1. **Prompt overload** — 5 detailed examples may be too many; the model pattern-matches to examples instead of treating input as data.
2. **No output validation** — nothing checks whether the output resembles the input (length, key terms, structure).
3. **No chunking strategy** — long transcripts blow context; behavior degrades unpredictably.
4. **Possible input corruption** — the combined raw+analysis input format may confuse the model about where data ends and instructions begin.

### What a Redesign Must Solve

| Problem | Fix (detailed in Docs 02-04) |
|---------|------------------------------|
| Example regurgitation | Fewer examples (1-2 max) + explicit "INPUT STARTS BELOW" delimiter + anti-injection guardrail |
| No validation | Length guard (reject if output < 70% of input length) + diff check |
| No chunking | Chunk long transcripts (>10K tokens) and refine per-chunk with overlap |
| Input confusion | Structured input format (clear field labels, delimiters) or OpenCode's structured I/O |

---

## C. The ytobs Pipeline (Where txrefine Plugs In)

### Current Data Flow

```
URL
 │
 ▼
extractor.py:extract_metadata()
 │  └─ yt-dlp → JSON3 subtitles → parse_json3_to_text()
 │  └─ sanitize_transcript_text()  ← ONLY cleanup today (removes [Music], collapses spaces)
 │
 ▼  transcript: str  (plain Python string, space-joined)
cli.py:817  transcript = result.get("transcript")
 │
 ├─► cli.py:855  run_pattern_optimizer()  [transcript truncated to 2000 words]
 │
 ▼
fabric_orchestrator.py:138  orchestrate(transcript, video_info)
 │
 ├─► Line 180: Phase 1 metadata extraction  [transcript sampled: first 2000 + last 500 words]
 │
 ├─► *** INSERTION POINT: LINE 205 ***   ← txrefine goes HERE
 │
 ▼
chunker.py:206  chunk_transcript(transcript)
 │  └─ token_counter.chunk_text_by_sentences() → List[Dict]
 │  └─ Each chunk → EnrichedPacket (with VideoContext preamble)
 │
 ▼
rate_limiter.py:368  subprocess.run(["fabric-ai", "-p", pattern], input=fabric_input)
 │  └─ THIS is the actual Fabric CLI call (per chunk, per pattern)
 │
 ▼
formatter.py → Obsidian markdown note
```

### Why Line 205 Is the Right Insertion Point

1. **Single chokepoint** — one `refine_transcript()` call, not per-chunk.
2. **Both phases benefit** — Phase 1 (metadata) and Phase 2 (patterns) both consume the refined text.
3. **`video_info` is already in scope** — needed to build `VideoContext` for context-aware refinement.
4. **Transcript is a flat `str`** — simplest possible data shape.
5. **All downstream consumers are transparent** — chunker, packet builder, Fabric calls all just receive better text.

### What the Call Looks Like

```python
# ytobs/fabric_orchestrator.py, around line 204-205

# === REFINE TRANSCRIPT (txrefine layer) ===
from .transcript_refiner import refine_transcript
if video_info:  # context-aware refinement
    vc = VideoContext.from_video_info(video_info)
    transcript = refine_transcript(transcript, video_context=vc)
else:
    transcript = refine_transcript(transcript)
# ==========================================
```

### All Fabric CLI Invocation Sites (for the OpenCode swap analysis)

| File:Line | Command | Purpose |
|-----------|---------|---------|
| `cli.py:231-236` | `fabric-ai --pattern pattern_optimizer` | Pattern recommendation |
| `rate_limiter.py:368-381` | `fabric-ai -p <pattern> [-m model]` | **Main workhorse** — every pattern execution |
| `fabric_orchestrator.py:461-465` | `fabric-ai -p <pattern> -s` | Streaming variant (Popen) |

A full Fabric→OpenCode swap would touch all three. A txrefine-only swap touches **none of these** — txrefine is a new, independent call.

---

## D. What's Specified But Not Built

The `PACKET_ENRICHMENT_SPEC.md` (Sprint 4) already specifies txrefine integration as "Phase B: Transcript Refinement Pipeline." Status: **spec only, zero code written**.

Specified but missing:
- `lib/transcript_refiner.py` module (the `TranscriptRefiner` class)
- `refine_transcript` Fabric pattern
- Refinement config block in `config.yaml`
- Token-budget strategy for long transcripts (>10K tokens)
- Original-vs-refined storage

This research folder picks up exactly where that spec left off — and adds the OpenCode alternative the spec didn't consider.

---

## E. The Bigger Picture: Why txrefine Is More Than a ytobs Feature

Your prompt hinted at this: txrefine isn't really about YouTube. It's a **general-purpose "clean raw human-generated text" primitive**. The same refine() function handles:

| Source | Raw Input | Same refine() Works? |
|--------|-----------|---------------------|
| YouTube auto-captions | JSON3 → text | ✅ (primary use case) |
| Voice notes (whisper/voxgen) | STT → text | ✅ (already the txrefine bash use case) |
| Podcasts | Whisper → text | ✅ |
| Meeting recordings | Teams/Zoom transcripts | ✅ |
| Films/lectures | Subtitle extraction | ✅ |
| Any URL (the future) | Whatever yt-dlp pulls | ✅ |

The refinement layer is **source-agnostic**. ytobs is just the first consumer. Building it as a clean, swappable module (with Fabric OR OpenCode backend) means every future content source gets the same quality upgrade for free.
