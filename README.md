# SentimentEdge

Five-agent sequential pipeline for analyzing r/wallstreetbets sentiment using the Claude API.

**Pipeline:** Collector → Filter → Sentiment → Aggregator → Output

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
Or set `API_KEY` directly in `config.py` (not recommended for shared repos).

**3. Confirm data files are in place**
```
data/
  r_wallstreetbets_posts.jsonl
  r_wallstreetbets_comments.jsonl
```

---

## Running the Pipeline

### Full run (all five agents, uses API)
```
python main.py
```

Each run creates a timestamped output directory:
```
outputs/runs/run_YYYYMMDD_HHMMSS/
  trace.txt              ← full terminal output (all five agents)
  sentiment_results.csv  ← per-post LLM results
  ticker_summary.csv     ← aggregated ticker stats
  rumour_alerts.csv           ← released high-confidence rumour lines (if any)
  rumour_pending_review.csv  ← high-stakes rumours held for human review (if any)
  run_metadata.json          ← config snapshot + pipeline stats
```

Logs are not overwritten — each run creates a new directory.

---

## Replay Mode

Replay re-renders the three output reports from a previous run's saved CSVs. It skips agents 1–4 entirely, makes no API calls, and requires no API key.

**Replay the most recent run:**
```
python main.py --replay
```

**Replay a specific run by directory:**
```
python main.py --replay outputs/runs/run_20260412_110302
```

Replay restores all columns (including list-type fields like `emotions` and `tickers`) from the saved CSVs and runs the Output Agent exactly as it ran originally. Useful for graders, demos, or changing the output format without re-running the full pipeline.

---

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `BATCH_SIZE` | 500 | Max posts sent to Sentiment Agent per run |
| `MIN_POST_SCORE` | 10 | Minimum upvote score to pass filter |
| `MODEL` | claude-sonnet-4-20250514 | Claude model used |
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

## Output Structure

The pipeline produces three reports in the terminal (also captured in `trace.txt`):

**Report 1 — Ticker Report**
Per-ticker deep dive: sentiment summary, emotion breakdown, post type breakdown, monthly timeline, top key insights, rumour alerts.

**Report 2 — Trend Alerts**
Daily sentiment shift table for all qualifying tickers. Flags tickers where sentiment moved more than 0.3 between two consecutive days.

**Report 3 — Ticker Comparison**
Side-by-side comparison across tickers: sentiment summary, signal quality, emotion breakdown, monthly timeline, top insights.

---

## Evaluation

Test cases and evidence files are in `eval/`:
```
eval/
  test_cases.md          ← 8 test cases, all verified PASS
  case_outputs/          ← per-test evidence files (TC-01 through TC-08)
  failure_log.md
  version_notes.md
```

Run `python main.py --replay` to reproduce all three reports without API calls.
