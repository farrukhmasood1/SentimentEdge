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

---

## v0.3 — Phase 3 Final (Phase 3)
**Date:** 2026-04-25
**Run evidence:** outputs/runs/run_20260425_174443/

Major additions for Phase 3 submission.

**Changes from v0.2:**
- Dataset expanded from 1 week to 1 month (6,919 posts, 945,096 comments)
- Full pipeline run: 500 posts analyzed, 68 tickers found, 7 rumours flagged, 0 errors
- Human review governance layer: high-stakes rumours (acquisition_rumour, confidence >= 0.8)
  routed to rumour_pending_review.csv instead of auto-publishing
- Two new config settings: RUMOUR_HUMAN_REVIEW_MIN_CONF and RUMOUR_HUMAN_REVIEW_TYPES
- React + TypeScript + Vite web dashboard added (web/) — displays cached run data
- Sarcasm annotation evaluation added (eval/sarcasm_annotation_sample_100.xlsx)
- Directory restructured to Phase 3 submission layout (docs/, data/raw/, media/, phase_submissions/)
- eval/test_cases.csv and eval/evaluation_results.csv added (12 cases each)
- _latest_run_dir() bug fixed — now sorts by folder name not full path
- All 8 required screenshots added to docs/screenshots/
- README updated with folder guide, evaluation summary, known limitations, team members

**Pending:**
- Final report PDF (docs/final_report.pdf)
- 5-minute demo video (media/demo_video_link.txt)
- PDF submission packet (Canvas submission)
