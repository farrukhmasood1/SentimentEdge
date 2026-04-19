# SentimentEdge — Version Notes

---

## v0.1 — Prototype (Google Colab)
**Date:** 2026-03-10 to 2026-03-22
**File:** sentimentedge_prototype.py

Single-file prototype developed in Google Colab. All five agents implemented
as functions in one file. Confirmed working on 50-post batch from
r/wallstreetbets sample dataset.

**Confirmed working:**
- Collector: loads 2,039 posts and 303,401 comments from JSONL
- Filter: 2,039 → 401 posts (19.7% retention)
- Sentiment: 50 posts processed, 0 errors, avg confidence 0.72
- Aggregator: ticker grouping, two-track routing, CSV saves
- Output: all six report sections rendering correctly

**Known issues at this version:**
- API key hardcoded (F-00 — not in failure log, pre-existing)
- permalink missing from df_llm (F-05)
- Image URL comments passed to Claude as noise
- FutureWarning on pandas groupby.apply()

---

## v0.2 — Modular Refactor (Phase 2)
**Date:** 2026-04-11
**Structure:** Full directory layout per SENTIMENTEDGE_PROJECT.md

Refactored into clean modular structure. All known issues from v0.1 fixed.
Prompt caching added to Sentiment Agent. Run logging system added.

**Changes from v0.1:**
- Split into agents/ and utils/ directories
- API key moved to environment variable
- permalink added to df_llm results (F-05 fixed)
- Image URL filter added to comment_bundler.py (noise reduction)
- FutureWarning fixed with include_groups=False
- Prompt caching added: cache_control on system prompt across batch
- TeeLogger added: every run saves trace.txt + run_metadata.json
- Aggregator saves CSVs to timestamped run directory (not overwritten)
- Eval files added: test_cases.md, failure_log.md, version_notes.md

**Pending for Phase 3:**
- Streamlit dashboard (Output Agent currently terminal only)
- Multi-subreddit support (architecture ready, Collector needs extension)
- evaluation_results.csv (filled after running TC-01 through TC-08)
