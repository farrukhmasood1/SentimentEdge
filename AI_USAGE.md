# AI Usage Disclosure — SentimentEdge

**Course:** 94815 Agentic Technologies | CMU Heinz College
**Project:** SentimentEdge — Phase 2
**Team:** Farrukh, Pablo, Moid, Afaq

---

## Tools Used

| Tool | Version | Purpose |
|---|---|---|
| Anthropic Claude (claude-sonnet-4-20250514) | API | Reddit post sentiment analysis, sarcasm detection, rumour identification |
| Claude Code (claude-sonnet-4-6) | CLI | Refactoring prototype into modular directory structure, writing eval files |

---

## Claude API — Sentiment Agent

**What it was used for:**
Each Reddit post is sent to `claude-sonnet-4-20250514` via the Anthropic Messages API.
Claude returns a 13-field JSON object covering sentiment, confidence, tickers, emotions,
sarcasm, market relevance, and rumour detection.

**Prompt used (system prompt, cached across batch):**
See `agents/sentiment_agent.py` → `_SYSTEM_PROMPT` constant.

**Prompt caching:**
The static system prompt is marked with `cache_control: ephemeral` so it is cached
after the first call in each batch. This reduces input token costs by ~90% across
a 500-post run.

**What was changed manually after AI output:**
- JSON parse failures are caught and replaced with neutral defaults (confidence 0.0)
- All 13 fields validated for presence via `.get()` with safe defaults
- Rumour alerts additionally filtered by `rumour_confidence >= 0.7` in Aggregator

**What was independently verified:**
- Sarcasm detection rate (11.8% across prototype run) manually reviewed against source posts
- Rumour flagging manually reviewed — all flagged posts in prototype run were legitimate
  speculation threads, not jokes or hypotheticals
- Confidence scores for viral meme posts confirmed low (0.30 on 123,150-upvote meme)

---

## Claude Code — Refactor and Documentation

**What it was used for:**
Refactoring the single-file prototype (`sentimentedge_prototype.py`) into the modular
directory structure. Writing eval files, failure log, and version notes.

**What was changed manually after Claude Code output:**
- All agent logic verified against confirmed-working prototype behaviour
- Config values cross-checked against Phase 1 documented thresholds
- Eval test cases written based on actual failure modes observed during prototyping

**What was independently verified:**
- All filter rules confirmed against prototype run statistics
  (64% deleted posts, 19.7% retention rate, engagement score formula)
- All output formatting confirmed against prototype terminal output
- Prompt caching implementation verified against Anthropic documentation

---

## Prototype Development (Phase 1 → Phase 2)

The prototype (`sentimentedge_prototype.py`) was developed independently in Google Colab
using the Anthropic Claude API. All pipeline logic, filter rules, engagement scoring,
and output formatting originated from the team's own design and iteration.

AI tools were used to assist with code refactoring and documentation structure.
All design decisions, threshold values, and evaluation criteria were made by the team
based on empirical observations from prototype runs.
