# AI Usage Disclosure — SentimentEdge

**Course:** 94815 Agentic Technologies | CMU Heinz College
**Project:** SentimentEdge — Phase 3
**Team:** Farrukh Masood, Pablo, Moid, Afaq

---

## Tools Used

| Tool | Version | Purpose |
|---|---|---|
| Anthropic Claude (claude-sonnet-4-20250514) | API | Reddit post sentiment analysis, sarcasm detection, rumour identification |
| Claude Code (claude-sonnet-4-6) | CLI | Refactoring, directory restructure, eval files, documentation |

---

## Claude API — Sentiment Agent

**What it was used for:**
Each Reddit post is sent to `claude-sonnet-4-20250514` via the Anthropic Messages API.
Claude returns a 13-field JSON object covering sentiment, confidence, tickers, emotions,
sarcasm, market relevance, and rumour detection.

**Prompt used (system prompt, cached across batch):**
See [agents/sentiment_agent.py](agents/sentiment_agent.py) → `_SYSTEM_PROMPT` constant.

**Prompt caching:**
The static system prompt is marked with `cache_control: ephemeral` so it is cached
after the first call in each batch. This reduces input token costs by ~90% across
a 500-post run.

**What was changed manually after AI output:**
- JSON parse failures caught and replaced with neutral defaults (confidence 0.0)
- All 13 fields validated for presence via `.get()` with safe defaults
- Rumour alerts filtered by `rumour_confidence >= 0.7` in Aggregator
- High-stakes rumours (`acquisition_rumour`, confidence >= 0.8) routed to human review queue

**What was independently verified:**
- Sarcasm detection rate manually reviewed against source posts
- Rumour flagging manually reviewed — all flagged posts were legitimate speculation threads
- Confidence scores for viral meme posts confirmed low (0.20–0.30 on high-engagement meme posts)

---

## Claude Code — Phase 2 Refactor and Documentation

**What it was used for:**
Refactoring the single-file prototype (`sentimentedge_prototype.py`) into the modular
directory structure. Writing eval files, failure log, and version notes.

**What was changed manually after Claude Code output:**
- All agent logic verified against confirmed-working prototype behaviour
- Config values cross-checked against Phase 1 documented thresholds
- Eval test cases written based on actual failure modes observed during prototyping

**What was independently verified:**
- All filter rules confirmed against prototype run statistics
- All output formatting confirmed against prototype terminal output
- Prompt caching implementation verified against Anthropic documentation

---

## Claude Code — Phase 3 Restructure and Eval Files

**What it was used for:**
- Reorganising the directory structure to match Phase 3 submission requirements
- Creating `eval/test_cases.csv` and `eval/evaluation_results.csv`
- Updating README with folder guide, evaluation summary, and known limitations
- Fixing `_latest_run_dir()` path comparison bug in `main.py`
- Updating `AI_USAGE.md` and `eval/version_notes.md` for Phase 3

**What was changed manually after Claude Code output:**
- All CSV content verified against actual run outputs and test_cases.md
- Directory structure reviewed against rubric requirements before committing
- Bug fix verified by running `python main.py --replay` and confirming correct run selected

**What was independently verified:**
- Both CSV files parsed with Python's csv module to confirm correct column count and row count
- Replay mode tested end-to-end after each structural change

---

## Web Frontend — Phase 3 Dashboard

**What it was used for:**
Building the React + TypeScript + Vite web dashboard (`web/`) that displays
cached pipeline run data including ticker reports, trend alerts, rumour alerts,
and the human review queue.

**What was changed manually after AI-assisted development:**
- Cache format (`web/public/runs/cache.json`) designed to match existing CSV output structure
- Human review queue UI designed based on Phase 2 feedback on governance visibility
- Playwright smoke test written to verify dashboard loads and key elements render

**What was independently verified:**
- Dashboard tested in browser against actual run data from `outputs/runs/run_20260425_174443/`
- All ticker data confirmed to match `ticker_summary.csv` values

---

## Prototype Development (Phase 1 → Phase 2)

The prototype (`sentimentedge_prototype.py`) was developed independently in Google Colab
using the Anthropic Claude API. All pipeline logic, filter rules, engagement scoring,
and output formatting originated from the team's own design and iteration.

AI tools were used to assist with code refactoring and documentation structure.
All design decisions, threshold values, and evaluation criteria were made by the team
based on empirical observations from prototype runs.
