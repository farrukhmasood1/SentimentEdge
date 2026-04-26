# SentimentEdge

Five-agent sequential pipeline for analyzing r/wallstreetbets sentiment using the Claude API.

**Pipeline:** Collector → Filter → Sentiment → Aggregator → Output

**Course:** 94815 Agentic Technologies | CMU Heinz College
**Track:** Track A
**Team:** Farrukh Masood, Pablo, Moid, Afaq

---

## Phase 2 Feedback — What Was Addressed in Phase 3

Phase 2 score: **93 / 100**. Three items were flagged for Phase 3:

**1. Human governance checkpoint for rumour alerts** ✅
> *"Decide what the trigger is... who owns the queue... Without this, the residual risk in the rumour-misuse row remains unmitigated."*

Built into the Aggregator. Posts with `rumour_confidence >= 0.8` **and** `rumour_type = acquisition_rumour` are written only to `rumour_pending_review.csv` and never auto-published. Config keys: `RUMOUR_HUMAN_REVIEW_MIN_CONF` and `RUMOUR_HUMAN_REVIEW_TYPES` in `config.py`. In the main run (7 rumours flagged), none matched `acquisition_rumour` at ≥ 0.8 confidence, so `rumours_pending_review = 0` — the mechanism is live but did not trigger on this dataset. Screenshots: `docs/screenshots/06_rumour_review_queue.png`.

**2. Sarcasm ground-truth benchmark** ✅ (run, with honest failure)
> *"Phase 3 is where empirical benchmark results go... Without the numbers, the benchmark exists on paper only."*

Benchmark executed on 100-post sample (annotators: Moid and Afaq). Results in `eval/sarcasm_metrics.json`:
- Krippendorff's alpha: **-0.002** (minimum threshold was 0.67 — **FAIL**, documented as F-06 in failure log)
- Pairwise agreement: 87% (inflated by class imbalance — alpha corrects for chance)
- Model precision: **0.568** | recall: **0.677** | F1: **0.618** (on 73 non-uncertain posts)
- Root cause: annotators diverged on ironic financial-loss posts; guideline revision identified but re-annotation not completed within Phase 3 scope.

**3. 4-week dataset expansion** ✅
> *"A multi-week run is the shortest path to a prototype that actually exercises every branch."*

Main run (`outputs/main_run/run_20260425_174443/`) covers March–April 2026:
- **6,919** raw posts | **945,096** comments | **1,458** filtered | **500** analyzed | **68** tickers | **7** rumours flagged
- Monthly timeline, trend alerts, and ticker comparison views all active on real data.

---

## Setup

**1. Install dependencies**
```
pip install -r requirements.txt
```

**2. Set your Anthropic API key**
```
export ANTHROPIC_API_KEY=your_key_here
```

**3. Place data files in `data/raw/`**
```
data/raw/
  r_wallstreetbets_posts.jsonl
  r_wallstreetbets_comments.jsonl
```
Data files are excluded from version control (comments file is 401MB). Source: r/wallstreetbets PushShift archive.

---

## Running the Pipeline

### Full run (all five agents, uses API)
```
python main.py
```

Each run saves to a timestamped directory:
```
outputs/main_run/run_YYYYMMDD_HHMMSS/
  trace.txt              ← full terminal output
  sentiment_results.csv  ← per-post LLM results
  ticker_summary.csv     ← aggregated ticker stats
  rumour_alerts.csv           ← released high-confidence rumour lines (if any)
  rumour_pending_review.csv  ← high-stakes rumours held for human review (if any)
  run_metadata.json          ← config snapshot + pipeline stats
```

### Replay mode (no API key required)
Replay re-renders all three reports from saved CSVs. Skips agents 1–4 entirely.

```
python main.py --replay
```

```
python main.py --replay outputs/sample_runs/run_20260412_110302
```

---

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `BATCH_SIZE` | 500 | Max posts sent to Sentiment Agent per run |
| `MIN_POST_SCORE` | 10 | Minimum upvote score to pass filter |
| `CLAUDE_MODEL` | claude-sonnet-4-20250514 | Claude model used |
| `MAX_TOKENS` | 400 | Max tokens per LLM response |
| `RUMOUR_THRESHOLD` | 0.7 | Minimum `rumour_confidence` to enter either rumour track |
| `RUMOUR_HUMAN_REVIEW_MIN_CONF` | 0.8 | With `RUMOUR_HUMAN_REVIEW_TYPES`, rows go to human review, not the released report |
| `RUMOUR_HUMAN_REVIEW_TYPES` | `acquisition_rumour` | Types treated as high-stakes (tuple in `config.py`) |

---

## Rumour governance and human review (Option A)

High-confidence model outputs are split in the **Aggregator** so that the highest-stakes pattern (configurable, default: `rumour_confidence >= 0.8` **and** `rumour_type` in `RUMOUR_HUMAN_REVIEW_TYPES`) is **not** shown in the **RUMOUR ALERTS** block. Those posts are written only to **`rumour_pending_review.csv`**.

- **Who reviews:** a **designated compliance or editorial reviewer** (named role; adjust in your Phase 3 report if your team uses a different title).  
- **SLA (team policy):** target triage within **24 hours**; adjust in the report if you choose another window.  
- **How review is evidenced (Option A):** the pipeline does **not** require merging approved rows back into `rumour_alerts.csv`. Review and approve/reject decisions are documented in the **Phase 3 final report and/or video** (e.g. narrative, screenshot of the queue, one worked example).  
- **User-facing path:** the terminal **RUMOUR ALERTS** section only lists **released** rows from `rumour_alerts.csv`. Pending rows never auto-publish from the model alone.

---

## Output Reports

The pipeline produces three reports in the terminal (also saved to `trace.txt`):

**Report 1 — Ticker Report**
Per-ticker deep dive: sentiment summary, emotion breakdown, post type breakdown, monthly timeline, top key insights, rumour alerts.

**Report 2 — Trend Alerts**
Daily sentiment shift table for qualifying tickers. Flags tickers where sentiment moved more than 15 percentage points between consecutive days.

**Report 3 — Ticker Comparison**
Side-by-side comparison across two tickers: sentiment summary, signal quality, emotion breakdown, monthly timeline, top insights.

---

## Folder Guide

```
SentimentEdge/
  main.py                        ← pipeline entry point
  config.py                      ← all tunable settings
  requirements.txt
  AI_USAGE.md                    ← AI tool disclosure

  agents/
    collector.py                 ← Agent 1: loads JSONL data
    filter_agent.py              ← Agent 2: filters and builds llm_text
    sentiment_agent.py           ← Agent 3: Claude API calls
    aggregator.py                ← Agent 4: ticker summaries + rumour routing
    output_agent.py              ← Agent 5: terminal reports

  utils/
    comment_bundler.py           ← bundles top comments per post
    logger.py                    ← timestamped run directories + TeeLogger

  data/
    raw/                         ← JSONL source files (not in git, see Setup)
    processed/                   ← intermediate files (currently empty; pipeline writes to outputs/)
    manifest.json                ← dataset description and file inventory

  docs/
    final_report.pdf             ← Phase 3 final report (TODO: add before submission)
    architecture_diagram.pdf
    SentimentEdge_Phase2_Full_Report.pdf
    screenshots/                 ← workflow screenshots

  eval/
    test_cases.md                ← 8 test cases with full evidence
    test_cases.csv               ← same cases in CSV format
    evaluation_results.csv       ← results for all 8 cases + 4 success criteria
    failure_log.md               ← 5 documented failure cases
    version_notes.md             ← v0.1 prototype → v0.2 modular
    case_outputs/                ← per-test evidence files TC-01 to TC-08

  outputs/
    main_run/                    ← primary evidence run + any new runs go here
      run_20260425_174443/       ← MAIN RUN: 4+ weeks data, 500 posts, 68 tickers
    sample_runs/
      run_20260412_110302/       ← earlier reference run (283 posts, 59 tickers)

  web/
    src/                         ← React + TypeScript frontend
    public/runs/cache.json       ← pre-cached run data for dashboard
    package.json
    vite.config.ts

  scripts/
    cache_frontend_runs.py       ← builds cache.json from run CSVs
    build_sarcasm_annotation_sheet.py

  media/
    demo_video_link.txt          ← 5-minute project video link

  phase_submissions/
    phase1/
    phase2/                      ← Phase 2 report PDF
    phase3/                      ← SUBMISSION_CHECKLIST.md + final materials (add before submitting)
```

---

## Evaluation Summary

**Primary run:** `outputs/main_run/run_20260425_174443/` (4+ weeks of data)
- **6,919** raw posts loaded | **500** analyzed | **68** tickers found | **7** rumours flagged
- Dataset: r/wallstreetbets, April 2026

**Reference run:** `outputs/sample_runs/run_20260412_110302/` (single-week slice used for test case evidence)
- **1,559** raw posts loaded | **283** analyzed | **59** tickers found | **3** rumours flagged

| Category | Cases | Result |
|---|---|---|
| Functional test cases (TC-01 to TC-08) | 8 | 8 PASS |
| Success criteria (SC-01 to SC-04) | 4 | 4 FAIL (documented) |

Full results in `eval/evaluation_results.csv`. Evidence files in `eval/case_outputs/`.

Reproduce all reports without an API key (reference run):
```
python main.py --replay outputs/sample_runs/run_20260412_110302
```

Replay the main run:
```
python main.py --replay outputs/main_run/run_20260425_174443
```

---

## Known Limitations

- **Filter retention 18.2%** — 64% of r/wallstreetbets posts have deleted bodies. Filter Rule 1 (body OR comments) mitigates this but cannot fully recover deleted content.
- **Avg confidence 0.67** — April 2026 market downturn drove a 49.5% sarcasm rate across the dataset. Heavy irony depresses confidence scores by design.
- **Ticker coverage** — 283 posts across 59 tickers yields avg 4.8 posts per ticker. A larger or multi-week dataset would produce statistically stronger per-ticker signals.
- **Web dashboard is read-only** — the React frontend displays cached run data from `web/public/runs/cache.json`. It does not run the pipeline live; a new run requires the Python pipeline and then re-caching.
- **Data files not in repo** — both JSONL files must be placed in `data/raw/` manually before running the full pipeline.
