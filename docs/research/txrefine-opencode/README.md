# txrefine × OpenCode — Research & Experiment Hub

**Created**: 2026-06-15
**Status**: 🟡 Research complete, experiment ready to run
**Author**: Consultant synthesis session (5 parallel research agents)

---

## TL;DR — The Whole Idea in 5 Lines

1. **txrefine** = a layer that cleans raw speech-to-text transcripts (fix typos, formatting, ASR errors) **without changing meaning**.
2. It already exists as a bash script at `~/.myscripts/txrefine` using **2 sequential Fabric patterns** — but it's **known broken** (model regurgitates prompt examples instead of processing input).
3. The ytobs pipeline has a **precise insertion point** (`fabric_orchestrator.py:205`) where txrefine slots in between transcript extraction and chunking — benefiting all downstream analysis.
4. **OpenCode headless** (`opencode run` / `opencode serve`) can replace Fabric CLI for this step, adding: structured JSON output, tool use, session continuity, better controllability — at the cost of cold-boot latency.
5. The vision: a **simple, robust, swappable refinement layer** that handles YouTube today and extends to podcasts, films, voice notes, any URL-source tomorrow.

---

## Why This Matters (The Needle It Moves)

The current ytobs pipeline feeds **raw, messy YouTube auto-transcripts** directly into Fabric analysis patterns. Garbage in → diluted analysis quality. A txrefine layer:

- **Upgrades every downstream pattern** (wisdom extraction, summaries, insights) by giving them clean input — force multiplier, not just one more feature.
- **Creates a reusable primitive**: the same refine() function works for voicenotes, podcasts, meeting transcripts, films — anything that produces raw ASR text.
- **Decouples refinement from analysis**: tune the refinement prompts independently, swap Fabric↔OpenCode without touching the rest of the pipeline.
- **Enables multi-stage pipelines** (research consensus: staged beats monolithic) — analyze → fix → format, each tunable.

> The core insight from your prompt: *"this simple structure, solid foundation, simple but robust where we can make what we already had with txrefine way better."* That's exactly right. txrefine isn't a feature — it's **infrastructure**.

---

## Document Navigation

| Doc | What's Inside | Read When |
|-----|---------------|-----------|
| **[01-current-state.md](01-current-state.md)** | What exists TODAY: the txrefine bash script (annotated), the two Fabric patterns, the known bug, the ytobs pipeline trace | You want to understand the starting point |
| **[02-opencode-vs-fabric.md](02-opencode-vs-fabric.md)** | Side-by-side comparison + a concrete experiment plan with test commands, success metrics, and a decision framework | You're ready to evaluate the swap |
| **[03-research-findings.md](03-research-findings.md)** | Distilled research: 6 proven prompt patterns, 10-stage pipeline designs, the "do not paraphrase" rule, anti-injection guardrails, temperature tuning | You're designing the prompts/pipeline |
| **[04-integration-design.md](04-integration-design.md)** | The exact module signature, insertion point, config schema, and chunking strategy for wiring txrefine into ytobs | You're ready to implement |
| **[05-reorganization-proposal.md](05-reorganization-proposal.md)** | A concrete proposal for cleaning up the ytobs folder structure (archive, don't delete) | You want to tidy the project |
| **[06-data-flywheel-vision.md](06-data-flywheel-vision.md)** | The big vision: ytobs/txrefine as the seed of a self-improving data flywheel for underrepresented languages (Pt-PT as prototype). Provenance, trust grading, contamination prevention, phased path. | You're thinking about training custom models |

---

## The Decision You Need to Make

After reading these docs, the open questions are:

1. **Backend choice**: Fabric (static, predictable, fast cold-start) vs OpenCode (robust, structured output, tool use, slower cold-start) vs **hybrid** (Fabric for the one-shot patterns, OpenCode for the refinement step). Doc 02 gives you the framework to decide.

2. **Pipeline depth**: Single-pass refine (simplest) vs 2-stage (current txrefine design: analyze → fix) vs 5-stage (JonaWhisper-style: filter → disfluency → punctuate → correct → finalize). Doc 03 has the tradeoffs.

3. **Scope of this iteration**: Just wire txrefine into ytobs (Doc 04), OR also rebuild txrefine itself first (fix the known bug), OR also reorganize the project (Doc 05).

**My recommendation** (detailed in each doc): Start with a **2-stage OpenCode-backed txrefine** wired into ytobs at the identified insertion point. It fixes the broken bash version, gives you structured output validation (kills the regurgitation bug), and unlocks the multi-source future — while keeping the rest of the pipeline untouched.

---

## Source Material Location

| Artifact | Path |
|----------|------|
| Existing txrefine script | `~/.myscripts/txrefine` |
| Stage 1 pattern (analyzer) | `~/.myscripts/fabric-custom-patterns/transcript-analyzer/system.md` |
| Stage 2 pattern (refiner) | `~/.myscripts/fabric-custom-patterns/transcript-refiner/system.md` |
| Known-bug dev notes | `~/.myscripts/fabric-custom-patterns/DEV-transcription-refinement-session-summary.md` |
| ytobs pipeline spec (Phase B) | `docs/development/PACKET_ENRICHMENT_SPEC.md` (Sprint 4) |
| Raw brainstorm ideas | `~/.myscripts/fabric-custom-patterns/transcript-refiner/raw/transcription-refinement-raw-ideas.md` |

---

## How This Folder Was Produced

One orchestrator session fired **5 parallel research agents**:
- 3× explore (codebase mapping, pipeline tracing, txrefine pattern discovery)
- 2× librarian (OpenCode headless docs, transcript refinement patterns)

A follow-up session fired **2 more librarian agents**:
- Pt-PT speech dataset landscape + gaps
- STT data curation pipelines + contamination prevention

Results were synthesized into these 7 documents. Raw agent outputs are not persisted — the distilled signal is here. Re-run the research any time with the same agent prompts.
