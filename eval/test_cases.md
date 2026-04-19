# SentimentEdge — Evaluation Test Cases

**Phase 2 | Track A**
Run evidence: `outputs/runs/run_20260412_110302/`
Dataset: r/wallstreetbets | 1,559 raw posts | 283 analyzed | 59 tickers | 3 rumours flagged

---

## TC-01 — Happy Path: Full Ticker Report Renders Correctly

| Field | Value |
|---|---|
| **Case ID** | TC-01 |
| **Type** | Happy path |
| **Input** | Replay saved run. Query SPY — top ticker by post count, low_sample=False. |
| **Expected** | Full report renders across all sections: Sentiment Summary, Emotion Breakdown, Post Type Breakdown, Monthly Timeline, Top Key Insights, Rumour Alerts. No crash. No missing sections. |
| **Actual** | SPY report rendered correctly across all six sections. 35 posts, 5 post types, 11 emotion categories, monthly timeline (single month — dataset covers one week), 3 top insights with direct Reddit permalinks, 2 rumour alerts displayed with disclaimer. No crash or KeyError. |
| **Outcome** | PASS |
| **Evidence** | `eval/case_outputs/TC-01_SPY_report.txt`; `outputs/runs/run_20260412_110302/ticker_summary.csv` — SPY row: post_count=35, low_sample=False |

---

## TC-02 — Sarcasm Detection: High Sarcasm Rate Warning Triggers

| Field | Value |
|---|---|
| **Case ID** | TC-02 |
| **Type** | Sarcasm handling |
| **Input** | Inspect SPY and TSLA reports from saved run. Both tickers have sarcasm_rate > 10%. |
| **Expected** | High sarcasm rate warning displayed in report. Sarcastic posts labelled `[SARCASTIC]` in Top Key Insights. Claude assigns lower confidence to sarcastic posts than to straightforward ones. |
| **Actual** | SPY: 14/35 posts sarcastic (40%) — warning triggered: "High sarcasm rate (40%) — scores adjusted by Claude." TSLA: 4/8 posts sarcastic (50%) — warning triggered. `[SARCASTIC]` label present in insights for both tickers. Sarcastic posts show lower confidence (e.g. SPY meme post: conf=0.30 vs DD post: conf=0.70). High sarcasm rate consistent with r/wallstreetbets behaviour during the April 2026 market downturn. |
| **Outcome** | PASS |
| **Evidence** | `eval/case_outputs/TC-02_sarcasm_warnings.txt`; `outputs/runs/run_20260412_110302/ticker_summary.csv` — sarcastic_count column: SPY=14, TSLA=4 |

---

## TC-03 — Low Confidence Warning: Below-Threshold Ticker Flagged

| Field | Value |
|---|---|
| **Case ID** | TC-03 |
| **Type** | Signal quality — low confidence |
| **Input** | Inspect TSLA report from saved run. avg_confidence=0.51, below LOW_CONF_THRESHOLD=0.60. |
| **Expected** | LOW CONFIDENCE warning displayed at top of report. Report still renders fully. No crash. |
| **Actual** | TSLA report displays "⚠  LOW CONFIDENCE" at header. Report rendered fully across all sections despite the warning. avg_confidence=0.51 driven by high meme/sarcasm volume in TSLA posts (e.g. JPMorgan warning post at conf=0.85 offset by three meme posts at conf=0.40). |
| **Outcome** | PASS |
| **Evidence** | `eval/case_outputs/TC-03_TSLA_low_confidence.txt`; `outputs/runs/run_20260412_110302/ticker_summary.csv` — TSLA row: avg_confidence=0.51, low_confidence=True |

---

## TC-04 — Viral Meme Post: High Engagement, Low Signal Correctly Identified

| Field | Value |
|---|---|
| **Case ID** | TC-04 |
| **Type** | Signal quality — low relevance meme |
| **Input** | Inspect DPZ (Domino's) entry from ticker_summary. Highest engagement score in dataset at 9656.8. |
| **Expected** | Claude assigns market_relevance < 0.4 and confidence < 0.5. low_confidence flag set to True. Post should not distort overall pipeline results. |
| **Actual** | DPZ: avg_engagement=9656.8 (highest in dataset), avg_confidence=0.20, avg_relevance=0.10, low_confidence=True. Claude correctly identified this as low-signal despite high engagement. DPZ does not appear in top-3 tickers by post_count so it did not generate a full report — its inflated engagement_score only affected its own single-post aggregate. |
| **Outcome** | PASS |
| **Evidence** | `eval/case_outputs/TC-04_DPZ_low_signal.txt`; `outputs/runs/run_20260412_110302/ticker_summary.csv` — DPZ row: avg_confidence=0.20, avg_relevance=0.10, avg_engagement=9656.8, low_confidence=True |

---

## TC-05 — Rumour Detection: Posts Routed to Separate Track

| Field | Value |
|---|---|
| **Case ID** | TC-05 |
| **Type** | Rumour detection and routing |
| **Input** | Inspect rumour_alerts.csv and SPY report from saved run. |
| **Expected** | Posts with is_rumour=True and rumour_confidence >= 0.70 appear in rumour_alerts.csv. Rumour Alerts section renders in the relevant ticker report with type, summary, confidence, and source link. Disclaimer displayed. |
| **Actual** | 3 posts flagged. All three appear in rumour_alerts.csv and in the SPY Rumour Alerts section: (1) Trump-Iran ceasefire causing oil price drop — rumour_confidence=0.80, type=regulatory_decision; (2) Iran missile salvo claim — rumour_confidence=0.70, type=regulatory_decision; (3) OpenAI/Anthropic/SpaceX IPO index rule bypass — rumour_confidence=0.70, type=regulatory_decision. All three correctly separated from ticker sentiment aggregate. Disclaimer "Unverified social media speculation only" displayed per alert. |
| **Outcome** | PASS |
| **Evidence** | `eval/case_outputs/TC-05_rumour_alerts.txt`; `outputs/runs/run_20260412_110302/rumour_alerts.csv` — 3 rows; `outputs/runs/run_20260412_110302/run_metadata.json` — rumours_flagged=3 |

---

## TC-06 — Replay Mode: Output Runs Without API Calls

| Field | Value |
|---|---|
| **Case ID** | TC-06 |
| **Type** | Replay / grader path |
| **Input** | `python main.py --replay` with no argument (auto-selects most recent run). |
| **Expected** | Pipeline skips agents 1–4. Loads CSVs from most recent run directory. Runs output agent and renders all three reports. No API calls made. Completes in seconds. |
| **Actual** | `python main.py --replay` printed "Replaying most recent run: outputs/runs/run_20260412_110302" and rendered all three reports (SPY, TSLA, TACO ticker reports + trend alerts + SPY/TSLA comparison) without making any API calls. `emotions` and `tickers` columns correctly restored from string repr via `ast.literal_eval`. Total runtime under 5 seconds. |
| **Outcome** | PASS |
| **Evidence** | `main.py` replay() and _latest_run_dir() functions; manual verification — no ANTHROPIC_API_KEY required for replay |

---

## TC-07 — Ticker Not Found: Graceful No-Data Response

| Field | Value |
|---|---|
| **Case ID** | TC-07 |
| **Type** | Failure — query miss |
| **Input** | Call `query_ticker('XYZ', ...)` against saved outputs where XYZ is not in ticker_summary. |
| **Expected** | Output Agent prints "No data found for $XYZ" and lists available tickers. No crash. No KeyError. |
| **Actual** | Output Agent prints "No data found for $XYZ." followed by "Available tickers: [list of 59 tickers]". Returns immediately. No exception raised. Remaining pipeline output unaffected. |
| **Outcome** | PASS |
| **Evidence** | `agents/output_agent.py` — ticker not found guard at top of query_ticker(); `outputs/runs/run_20260412_110302/ticker_summary.csv` confirms XYZ absent |

---

## TC-08 — Filter Zero Result: Pipeline Stops Before API Calls

| Field | Value |
|---|---|
| **Case ID** | TC-08 |
| **Type** | Failure — filter gate |
| **Input** | Temporarily set MIN_POST_SCORE=100000 in config.py. Run full pipeline. No posts in the dataset have score >= 100,000. |
| **Expected** | Filter Agent returns empty DataFrame. Pipeline halts after Agent 2. run_metadata.json written with n_filtered=0. No Claude API calls made. |
| **Actual** | Pipeline halted after Filter Agent with message "✗ Pipeline stopped — no posts survived filtering." run_metadata.json recorded n_filtered=0, n_analyzed=0, errors=0. trace.txt captured Agent 1 and Agent 2 output only — no Agent 3 header present confirming no API calls were made. |
| **Outcome** | PASS |
| **Evidence** | `main.py` lines 64–72 — explicit zero-result check after run_filter(); `agents/filter_agent.py` lines 107–110 — warning + empty return |

---

## Success Criteria Results

| Criterion | Target | Result | Status |
|---|---|---|---|
| Sentiment accuracy | Avg confidence ≥ 0.75 on high-quality posts | SPY (top ticker, 35 posts): avg_confidence=0.67 | Fail |
| Sarcasm detection | Sarcasm warning triggers above 10% rate | SPY 40%, TSLA 50% — both triggered correctly | Pass |
| Rumour detection | Rumours routed to separate track with disclaimer | 3 posts flagged, all in rumour_alerts.csv with disclaimer | Pass |
| Ticker extraction | No false positives on ambiguous tokens | No AI, OPEN, FAST in ticker_summary | Pass |
| Pipeline throughput | 283 posts processed | 1,113s (~18.5 min) | Fail |
| Replay mode | Output runs without API key | Confirmed — completes in < 5 seconds | Pass |
| Filter quality | ≥ 30% retention | 283/1559 = 18.2% | Fail |
| Coverage | ≥ 10 tickers with ≥ 5 posts | 3 tickers with ≥ 5 posts (SPY, TSLA, TACO) | Fail |
| Failure handling | Zero-filter and query-miss handled gracefully | TC-07 and TC-08 both confirmed | Pass |
| Viral meme handling | High-engagement low-signal post correctly scored | DPZ: conf=0.20, relevance=0.10 | Pass |

### Notes on failing criteria

**Filter quality (18.2%):** The 64% deleted-post problem (F-02) is mitigated but not eliminated. Rule 1 already accepts posts with body OR comments, raising retention from under 5% to 18.2%. Further improvement would require lowering MIN_POST_SCORE below 10, which risks including fringe low-signal posts.

**Confidence (0.67 for SPY):** The April 2026 market downturn produced a 49.5% sarcasm rate across the dataset. Heavy irony naturally depresses confidence scores. This is a dataset characteristic documented in F-03, not a pipeline failure.

**Pipeline throughput (18.5 min):** Only 283 posts were processed (not 500 — fewer passed filtering than the batch cap). At 283 posts the rate was ~3.9s/post. The `errors: 217` in run_metadata.json is a misleading label — it reflects BATCH_SIZE(500) − n_analyzed(283) = 217, not actual API errors. The Sentiment Agent reported 0 errors.

**Coverage (3 tickers ≥ 5 posts):** Direct consequence of low filter retention. 283 posts across 59 tickers yields an average of 4.8 posts per ticker. A larger or multi-week dataset would improve this significantly.
