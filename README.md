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
  posts.jsonl
  comments.jsonl
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
  rumour_alerts.csv      ← flagged rumour posts (if any)
  run_metadata.json      ← config snapshot + pipeline stats
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
