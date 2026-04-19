# SentimentEdge — Failure Log

**Phase 2 | Track A**
Documents failure cases discovered during prototyping and testing.

---

## Failure Log Format

| Field | Description |
|---|---|
| failure_id | Sequential ID (F-01, F-02, ...) |
| date | Date failure was observed |
| version_tested | Pipeline version or git commit |
| what_triggered_the_problem | Input or condition that caused it |
| what_happened | Observed behaviour |
| severity | High / Medium / Low |
| fix_attempted | What was done to address it |
| current_status | Fixed / Open / Mitigated / Accepted |

---

## F-01 — Viral meme post distorts ticker confidence score

| Field | Value |
|---|---|
| **failure_id** | F-01 |
| **date** | 2026-03-15 (prototype run) |
| **version_tested** | sentimentedge_prototype.py v1 |
| **what_triggered_the_problem** | A post with score 123,150 (highest in dataset) was a viral meme with no substantive market content. Its high engagement_score placed it first in the batch sent to Claude. |
| **what_happened** | Claude correctly assigned confidence 0.30 and market_relevance 0.10. However, the post's high engagement_score gave it disproportionate weight in the ticker aggregate, dragging avg_confidence below 0.6 and triggering a low-confidence warning even for tickers with otherwise strong signal. |
| **severity** | Medium |
| **fix_attempted** | Added `market_relevance` field to aggregator output. Added `avg_relevance` column to ticker_summary so users can distinguish low-confidence posts from low-relevance posts. Weighted engagement score does not currently penalise low-relevance posts — this is a known limitation. |
| **current_status** | Mitigated — low-confidence warning is surfaced, user sees avg_relevance score |

---

## F-02 — 64% of raw posts have deleted bodies

| Field | Value |
|---|---|
| **failure_id** | F-02 |
| **date** | 2026-03-10 (prototype run) |
| **version_tested** | sentimentedge_prototype.py v1 |
| **what_triggered_the_problem** | Reddit moderators remove post bodies but not titles. 64% of r/wallstreetbets posts in the dataset had `selftext = [removed]` or `[deleted]`. Initial filter logic removed all deleted posts, resulting in < 5% of raw posts surviving. |
| **what_happened** | Filter Agent was too aggressive — useful posts with only titles were discarded. 500-post batch reduced to ~25 usable posts. Sentiment output was statistically meaningless. |
| **severity** | High |
| **fix_attempted** | Filter Rule 1 changed to: keep posts where body is present OR bundled comments exist. Title-only posts now pass if they have substantive comments. This raised retention to 19.7% in the prototype run. |
| **current_status** | Fixed |

---

## F-03 — Sarcasm rate unexpectedly high during market volatility

| Field | Value |
|---|---|
| **failure_id** | F-03 |
| **date** | 2026-03-20 (prototype run) |
| **version_tested** | sentimentedge_prototype.py v1 |
| **what_triggered_the_problem** | Prototype was run during a period of heavy market sell-off. r/wallstreetbets responds to losses with extremely heavy irony. Claude flagged 78% of posts as sarcastic in the 50-post batch (expected: 10–15%). |
| **what_happened** | The high sarcasm rate triggered the sarcasm warning on every ticker report. Several posts that were genuinely bearish (not sarcastic) were flagged as sarcastic because of the surrounding ironic context in their comments. |
| **severity** | Medium |
| **fix_attempted** | Sarcasm warning threshold kept at 10% — this is by design. The system correctly surfaces high sarcasm as a signal quality warning. Claude's sarcasm judgment was manually reviewed for 20 flagged posts; 85% were correctly identified. No threshold change made. Added note to output: "scores adjusted by Claude." |
| **current_status** | Accepted — high sarcasm rate during volatility is a real signal, not a bug |

---

## F-04 — JSON parse failure on Claude response

| Field | Value |
|---|---|
| **failure_id** | F-04 |
| **date** | 2026-03-18 (prototype run) |
| **version_tested** | sentimentedge_prototype.py v1 |
| **what_triggered_the_problem** | Occasionally Claude prefixes the JSON response with a short explanation sentence (e.g. "Here is the analysis:") before the JSON object, or wraps it in markdown code fences. |
| **what_happened** | `json.loads()` raised `JSONDecodeError`. The post was silently skipped, reducing the batch count without a clear indication of why. |
| **severity** | Low |
| **fix_attempted** | Added `.replace('```json', '').replace('```', '').strip()` before parsing. Added explicit `JSONDecodeError` catch that returns neutral defaults with confidence 0.0 rather than skipping the post. Error counter incremented and reported in summary. |
| **current_status** | Fixed |

---

## F-05 — Permalink missing from df_llm in Output Agent

| Field | Value |
|---|---|
| **failure_id** | F-05 |
| **date** | 2026-03-22 (prototype run) |
| **version_tested** | sentimentedge_prototype.py v1 |
| **what_triggered_the_problem** | The `permalink` field was not carried through from `df_filtered` to the Sentiment Agent's `results.append()` block. |
| **what_happened** | Output Agent raised `KeyError: 'permalink'` when attempting to display Reddit links in the Top Key Insights section. A workaround lookup from `df_filtered` was added as a temporary fix. |
| **severity** | Medium |
| **fix_attempted** | `permalink` added explicitly to the `results.append()` dict in `run_sentiment_agent()`. Column is now present in `df_llm` directly. Workaround removed. |
| **current_status** | Fixed in modular refactor |
