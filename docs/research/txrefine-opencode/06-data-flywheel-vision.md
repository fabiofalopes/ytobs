# 06 — The Data Flywheel: YouTube → Curated Training Data → Better Models

**Question answered**: Can ytobs/txrefine become the seed of a self-improving data flywheel for underrepresented languages (Pt-PT as the prototype)?

**Status**: 🟡 Concept validated by research. Not yet implemented.

---

## A. The Flywheel (Named)

txrefine isn't just a cleanup step. It's the **quality gate** in a data flywheel — the mechanism that decides which transcripts are clean enough to enter the training pool. Here's the full loop:

```
    ┌─────────────────────────────────────────────────────────┐
    │                                                         ▼
  1. COLLECT            2. REFINE           3. CURATE         4. TRAIN
  ytobs pulls          txrefine cleans      Human+AI grades   Whisper fine-tune
  YouTube per          the raw auto-        trust tier:       on A-tier Pt-PT
  language/region      transcript           A/B/C/D           podcast data
  (Pt-PT podcasts)     (the primitive)      + provenance
    │                                                         ▲
    │                                                         │
    └─────────────────────────────────────────────────────────┘
                            5. DEPLOY
                  Better STT → cleaner raw transcripts →
                  txrefine has easier job → better notes →
                  more confident curation → flywheel spins
```

**This is not a new idea — it's a proven engineering pattern.** MoulSot (Moroccan Darija ASR), massive_yt_edu_scraper (35,890h English), YCSEP (620h Singapore English), GigaSpeech 2 (30k hours Thai/Indonesian) all do exactly this. The gap: nobody has done it for **Pt-PT podcasts**.

---

## B. The Pt-PT Gap (Why This Specific Opportunity)

### The landscape, brutally honest

| Domain | Available Pt-PT Hours | Source |
|--------|----------------------|--------|
| Parliamentary (formal) | **10,000+** | FalAR (5,800h) + EuroSpeech (5,096h) |
| Read speech (clean) | ~90 | MLS + BD-PÚBLICO + Common Voice |
| Broadcast news | ~7 | Alert dataset |
| Lectures | ~3 | Lectra |
| Conversational | ~4 | Postport |
| Sociolinguistic interviews | ~10 | Fala Bracarense + PT Fundamental |
| **Podcast / informal** | **0** | **← YOUR GAP** |

Common Voice v25 (the de facto open-source ASR resource) has **72 Pt-PT speakers and ~4 validated hours**. Pt-BR outnumbers Pt-PT **25:1 in clips**. This isn't a rounding error — it's systematic.

### Why podcasts are the right gap to fill

Podcasts capture what parliamentary speech and read audiobooks cannot:
- **Casual register** — contractions, slang, incomplete sentences
- **Speaker diversity** — age, region, education, not just politicians
- **Natural prosody** — interruptions, overlaps, laughter
- **Varied audio quality** — real-world conditions, not studio
- **Code-switching** — EN/PT mixing common in tech podcasts

The CAMÕES benchmark (the Pt-PT ASR evaluation) proves the point: WhisperLv3 zero-shot gets **16.4% WER on EP formal speech** but crashes to **39.3% WER on sociolinguistic interviews** (strong accents, poor audio). Podcasts live in that hard middle ground.

### The viability math

Research consensus on minimum viable dataset size for Whisper fine-tuning:

| Hours | Result | Source |
|-------|--------|--------|
| 10h | Meaningful improvement (if language in pre-training) | OpenReview 2025 |
| 17h | 26.56% relative WER reduction (Portuguese CV) | arXiv 2025 |
| 20h | **56.94% relative WER reduction** (7 low-resource langs) | Springer 2024 |
| 80-100h | **8.82% WER** on EP test set | Springer 2025 |
| 425h | 12.5% avg WER on CAMÕES (SOTA) | INESC-ID 2025 |

**20-50h of curated Pt-PT podcast audio is achievable in weeks, not months**, and would yield significant improvements. One 2-hour podcast per week = 100h/year.

---

## C. txrefine as the Linchpin (Why the Primitive Matters)

The flywheel only works if the quality gate is reliable. Here's where txrefine sits in the curation pipeline (modeled on MoulSot, the gold-standard reference):

```
YouTube audio
    │
    ▼
VAD (Silero)              ← segment into speech clips
    │
    ▼
Quality scoring           ← SQUIM (PESQ/STOI/SI-SDR) + Audiobox Aesthetics
    │                       Hard exclusions: PESQ<1.0, STOI<0.6
    ▼
Auto-transcript           ← YouTube auto-caption OR Whisper
    │
    ▼
★ txrefine ★              ← THE PRIMITIVE: clean the transcript
    │                       (this is what makes curation trustworthy)
    │                       Without this step, you're training on noise.
    ▼
Cross-model validation    ← Second ASR pass (e.g., Cohere/Wav2Vec2)
    │                       Agreement score = confidence signal
    ▼
Trust grading             ← A/B/C/D tier assignment
    │                       (see §D below)
    ▼
Human review              ← Argilla-style rating on uncertain samples
    │                       (active learning: review only what matters)
    ▼
Training store            ← Only A-tier enters here
```

**MoulSot's selection rate: 5.3%** (1,500h raw → 80h curated). txrefine is what makes that selection defensible — without a clean reference transcript, you can't grade whether the auto-transcript is good enough to train on.

### The dual-mode problem

txrefine serves two masters with **opposite requirements**:

| Mode | Requirement | Policy |
|------|-------------|--------|
| **Inference** (user runs ytobs on a new video) | Fast, lenient, never blocks | Backend: regex-only or fast LLM. Fall back gracefully. Treat input as untrusted. |
| **Curation** (building training data) | Slow, strict, full provenance | Backend: OpenCode with structured output. Length/bigram validation. Human review gate. Full provenance tracking. |

Same `refine_transcript()` function, wrapped in two policies. The function signature from Doc 04 already supports this via the `backend` and `config` parameters — just add a `mode="inference"|"curation"` parameter.

---

## D. The Trust Grading System (Provenance + Separation)

This is the part you circled at the end of your message — *"at inference you don't want user to replicate that same supposed represented."* It's the **data contamination prevention** problem, and it has production-grade solutions.

### The cardinal rule

> **Training data and inference data must be PHYSICALLY SEPARATED.** Not "logically separated" — physically. Different stores, different code paths, different access patterns. If the same service can read both, you've created a contamination path.
> — Synthesized from TianPan.co (Apr 2026), Grammar of ML Workflows (arXiv:2603.10742)

### Trust tiers

Every curated entry gets a tier. Only A enters training:

| Tier | Criteria | Use |
|------|----------|-----|
| **A (Train)** | CC-licensed source + human-verified transcript + PESQ>2.5 + single speaker | Training pool |
| **B (Use)** | Standard license + txrefine-cleaned + cross-model agreement>0.85 | Inference only, never trains |
| **C (Discard)** | Failed quality gates OR legal risk OR contamination flag | Archived, not used |
| **D (Quarantine)** | Awaiting human review | Held until graded |

### Provenance schema (every entry carries this)

```python
@dataclass
class CuratedEntry:
    # Identity
    entry_id: str                    # content hash
    source_url: str                  # YouTube URL
    video_id: str
    channel_id: str
    channel_name: str

    # Content
    audio_path: str                  # local path (never redistributed)
    transcript_raw: str              # YouTube auto-caption
    transcript_refined: str          # post-txrefine
    transcript_human_verified: Optional[str]  # if reviewed

    # Provenance
    license: str                     # "CC-BY", "standard", "commercial"
    license_risk: str                # green/yellow/orange/red
    source_category: str             # "podcast", "lecture", "interview"

    # Quality scores
    pesq: float                      # 1.0-4.5 (signal quality)
    stoi: float                      # 0.0-1.0 (intelligibility)
    si_sdr: float                    # dB (noise level)
    cross_model_agreement: float     # 0.0-1.0 (YT vs second ASR)
    human_rating: Optional[int]      # 1-5 (if reviewed)

    # Trust
    tier: str                        # A/B/C/D
    in_training_set: bool            # CRITICAL: has this EVER been trained on?
    contamination_score: float       # MinHash Jaccard vs eval set

    # Flywheel tracking
    added_date: datetime
    last_verified_date: datetime
    model_version_that_graded: str   # which txrefine version produced the refined text
```

### Contamination gate

Before ANY entry enters the training store, run:

```python
def can_enter_training(entry: CuratedEntry, eval_registry: MinHashLSH) -> bool:
    # 1. License check
    if entry.license_risk not in ("green",):
        return False

    # 2. Quality floor
    if entry.pesq < 2.5 or entry.stoi < 0.7:
        return False

    # 3. Human verification required for A-tier
    if entry.human_rating is None or entry.human_rating < 4:
        return False

    # 4. Contamination check (MinHash LSH, Jaccard 5-gram > 0.8)
    candidates = eval_registry.query(entry.content_hash)
    if any(c.jaccard > 0.8 for c in candidates):
        return False  # too similar to eval data

    # 5. Not already trained on
    if entry.in_training_set:
        return False

    return True
```

### Physical separation

```
data/
├── training/          ← A-tier only. Model training reads from here.
│   ├── pt-pt-podcasts/
│   └── manifests/
├── inference/         ← B-tier. ytobs at inference reads from here.
│   └── (user transcripts, never mixed)
├── eval/              ← CAMÕES benchmark + holdout. APPEND-ONLY. Training NEVER reads this.
└── quarantine/        ← D-tier, awaiting review
```

---

## E. The Self-Improvement Loop (Optional, Phase 3+)

Once you have a trained model, the flywheel can spin itself (with human gates):

```
                          ┌──────────────────────┐
                          │  Deploy v1 model     │
                          │  (fine-tuned on      │
                          │   20h A-tier Pt-PT)  │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Run v1 on NEW       │
                          │  YouTube podcasts    │
                          │  (inference mode)    │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Confidence-score    │
                          │  every segment       │
                          │  (cross-model +      │
                          │   txrefine validation)│
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Active learning:    │
                          │  route LOWEST        │
                          │  confidence segments │
                          │  to human review     │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Human-corrected     │
                          │  segments → A-tier   │
                          │  → training store    │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Retrain v2 on       │
                          │  expanded A-tier     │
                          │  (with eval gate)    │
                          └──────────┬───────────┘
                                     │
                                     └── back to deploy v2
```

**Research validation**: ReHear (arXiv:2602.18721) shows audio-aware LLM correction in the loop gives meaningful gains over 3 iterations. NVIDIA Nemotron Speech uses this exact pattern clinically. TTS-in-the-loop (arXiv:2506.11130) achieves **55.88% WER improvement**.

**Critical guardrail**: Every "self-improved" label is a CANDIDATE, not ground truth. Human review gates every entry that enters A-tier. The model proposes; humans dispose.

---

## F. The Legal Posture (Manageable, Not Blocking)

YouTube ToS (§4.B.3) technically prohibits scraping. But every successful project navigates this:

| Strategy | Example | Risk |
|----------|---------|------|
| **CC-licensed videos only** | YODAS (500k+ hours) | 🟢 Low — creator pre-authorized |
| **Release transcripts, not audio** | YCSEP, Rhapsody | 🟢 Low — users download their own audio |
| **Fair use (transformative)** | KT-Speech-Crawler | 🟡 Medium — research/non-commercial |
| **EU DSM Directive Art. 3** | European research | 🟢 Low — text/data mining exception |

**Practical playbook** (from massive_yt_edu_scraper's 4.4M video audit):
- 1.2% of YouTube is CC-licensed (55K+ videos) — start here
- Tag every entry with `license_risk: green/yellow/orange/red`
- Known CC podcast sources: search `creative commons portuguese podcast` on YouTube
- Never redistribute original audio — only transcripts + metadata
- Document fair use analysis per source category

**Pt-PT specific**: Portuguese podcasts are often independently produced, CC-licensed, and the creators are approachable for explicit permission. This is easier than scraping major-label content.

---

## G. Phased Path (From Today to Full Flywheel)

| Phase | Scope | Effort | Unlocks |
|-------|-------|--------|---------|
| **0. txrefine (current)** | The refine primitive, working, backend-swappable | Already scoped (Docs 02-04) | The quality gate for everything below |
| **1. Provenance tracking** | Add `CuratedEntry` schema to ytobs cache. Every processed video gets license + quality metadata. | 1-2 days | You can answer "what do I have and can I trust it?" |
| **2. Pt-PT podcast sourcing** | A channel list (10-20 CC-licensed Pt-PT podcasts). ytobs extended to download audio (not just transcript). | 2-3 days | Raw material for the dataset |
| **3. Quality scoring** | Add SQUIM + Audiobox Aesthetics to the pipeline. Tag every segment. | 2-3 days | Trust tiers become computable |
| **4. Human review portal** | Argilla (free, HF-hosted) for reviewing uncertain segments. Active learning routing. | 3-5 days | A-tier data starts flowing |
| **5. First training run** | Fine-tune Whisper-small on 20h A-tier Pt-PT. Evaluate on CAMÕES. | 1-2 days (GPU) | Proof the flywheel produces value |
| **6. Contamination gate** | MinHash LSH eval registry. Physical store separation. | 2-3 days | Production-safe training |
| **7. Self-improvement loop** | Deploy v1 → confidence-score new content → active learn → retrain | 1-2 weeks | The wheel spins on its own |

**Phase 0 is the dependency for everything.** You cannot build a trustworthy dataset on top of an untrustworthy transcript cleaner. This is why txrefine matters disproportionately — it's not a feature, it's the foundation.

---

## H. What This Enables Beyond Pt-PT

Pt-PT is the prototype. Once the flywheel works for one language, it generalizes:

| Source type | What ytobs already handles | What the flywheel adds |
|-------------|---------------------------|----------------------|
| YouTube (any language) | ✅ Transcript + metadata | Curated training data for any underrepresented language |
| Podcasts (RSS) | 🔜 Future source module | Same pipeline, RSS instead of YouTube |
| Films/subtitles | 🔜 Future source module | Domain adaptation for cinema speech |
| Voice notes (local) | ✅ (via txrefine bash) | Personal STT adaptation |
| Meeting recordings | 🔜 Future source module | Domain-specific (Zoom/Teams) STT |

The txrefine primitive + provenance schema + trust grading = a **general-purpose "curate any speech into training data" platform**. ytobs is just the first frontend.

---

## I. Honest Assessment: What's Hard

| Challenge | Difficulty | Mitigation |
|-----------|------------|------------|
| Finding CC-licensed Pt-PT podcasts | 🟡 Medium | Manual curation of 10-20 channels; outreach to creators |
| Getting 20h of A-tier data | 🟢 Tractable | ~40 podcast episodes at 30min each, post-quality-filter |
| GPU access for fine-tuning | 🟡 Medium | Google Colab (free tier), or rent A100 by the hour |
| Contamination prevention | 🟢 Solved pattern | MinHash LSH is well-documented (TianPan, Grammar paper) |
| Human review throughput | 🟡 Medium | Active learning minimizes review volume; Argilla is free |
| Legal risk | 🟢 Manageable | CC-only strategy eliminates most risk |
| Evaluation rigor | 🟢 Solved | CAMÕES benchmark exists; submit to leaderboard |
| Model degradation over time | 🟡 Medium | Eval gate on every retrain; rollback if WER regresses |

**Nothing here is a moonshot.** Every component is proven. The novelty is (a) applying it to Pt-PT podcasts specifically, and (b) building it on top of ytobs/txrefine as the curation primitive.

---

## J. Decision Framework

| If you want... | Then... |
|----------------|--------|
| Just better ytobs notes | Stop at Phase 0 (txrefine). Don't build the flywheel. |
| A Pt-PT STT model that doesn't embarrass you | Phases 0-5. ~2 weeks of focused work. |
| A general-purpose speech curation platform | Phases 0-7. ~4-6 weeks. The flywheel spins. |
| To publish a dataset paper | Phases 0-5 + write up. Fill the documented Pt-PT podcast gap. Submit to INTERSPEECH or similar. |

**My read**: The flywheel is worth building IF you already care about Pt-PT STT quality (you do — you live in Portugal and use these tools daily). The txrefine primitive is worth building regardless — it improves ytobs today and is the prerequisite for the flywheel tomorrow. Build txrefine first; the flywheel option stays open.

---

## K. Sources (Key References)

| Topic | Source |
|-------|--------|
| MoulSot pipeline (gold standard) | [HuggingFace blog](https://huggingface.co/blog/abdeljalilELmajjodi/moulsot) |
| massive_yt_edu_scraper (35k hours) | [GitHub](https://github.com/thepowerdeez/massive_yt_edu_scraper) |
| Pt-PT dataset landscape | Common Voice v25, FalAR (arXiv:2605.27062), EuroSpeech (HF), CAMÕES (INESC-ID) |
| Whisper fine-tuning thresholds | Springer 2024 (20h→57% WER reduction), Springer 2025 (100h EP→8.82% WER) |
| Contamination prevention | TianPan.co (Apr 2026), Grammar of ML Workflows (arXiv:2603.10742) |
| Self-improving STT | ReHear (arXiv:2602.18721), TTS-in-loop (arXiv:2506.11130) |
| YouTube legal playbook | [LICENSING_ANALYSIS.md](https://github.com/thepowerfuldeez/massive_yt_edu_scraper/blob/main/LICENSING_ANALYSIS.md) |
| Active learning for ASR | Adapt4Me (arXiv:2603.20112), TeLeS (arXiv:2401.03251) |

Full raw research from the two librarian agents is not persisted — the distilled signal is here. Re-run with the same agent prompts to refresh.
