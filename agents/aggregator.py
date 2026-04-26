"""
SentimentEdge — Agent 4: Aggregator
Combines per-post LLM results into output tracks:
  Track 1 — ticker-level sentiment summaries (engagement-weighted)
  Track 2 — released rumour alerts (high-confidence, not requiring human hold)
  Track 2b — rumour_pending_review (high-stakes: held for human review; saved to CSV)

All outputs are saved to the timestamped run directory so every run is
preserved and auditable.

Inputs:  df_llm (from Sentiment Agent), run_dir
Outputs: ticker_summary, rumour_released, rumour_pending_review, df_llm (with month column added)
"""

import os
import pandas as pd
from config import (
    RUMOUR_THRESHOLD,
    RUMOUR_HUMAN_REVIEW_MIN_CONF,
    RUMOUR_HUMAN_REVIEW_TYPES,
    LOW_CONF_THRESHOLD,
    LOW_SAMPLE_THRESHOLD,
)


def run_aggregator(df_llm, run_dir):
    """
    Groups per-post sentiment data into ticker summaries and split rumour tracks.
    Saves sentiment/ticker CSVs; saves rumour_alerts (released) and
    rumour_pending_review (held) when non-empty.

    Inputs:
        df_llm   — analyzed posts DataFrame from Sentiment Agent
        run_dir  — timestamped run folder path (from logger.create_run_dir)

    Outputs:
        ticker_summary — DataFrame indexed by primary_ticker
        rumour_released — high-confidence rumours shown in RUMOUR ALERTS
        rumour_pending_review — held rows (excluded from RUMOUR ALERTS)
        df_llm — input DataFrame with 'month' column added
    """
    print('\n' + '=' * 55)
    print('AGENT 4 — AGGREGATOR')
    print('=' * 55)

    if len(df_llm) == 0:
        print('  ⚠  df_llm is empty — returning empty outputs.')
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), df_llm

    print(f'Input: {len(df_llm)} analyzed posts')

    # ── Track 1: ticker sentiment summaries ───────────────────────────────────
    df_known = df_llm[df_llm['primary_ticker'] != 'UNKNOWN'].copy()

    ticker_summary = df_known.groupby('primary_ticker').agg(
        post_count      =('sentiment', 'count'),
        bullish_pct     =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
        bearish_pct     =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
        neutral_pct     =('sentiment', lambda x: round((x == 'neutral').sum() / len(x) * 100, 1)),
        avg_confidence  =('confidence', 'mean'),
        avg_relevance   =('market_relevance', 'mean'),
        sarcastic_count =('is_sarcastic', 'sum'),
        avg_engagement  =('engagement_score', 'mean'),
    ).round(2).sort_values('post_count', ascending=False)

    ticker_summary['low_confidence'] = ticker_summary['avg_confidence'] < LOW_CONF_THRESHOLD
    ticker_summary['low_sample']     = ticker_summary['post_count']     < LOW_SAMPLE_THRESHOLD

    # ── Track 2: high-confidence rumours → released vs human-review queue ────
    high_conf = df_llm[
        (df_llm['is_rumour'] == True) &
        (df_llm['rumour_confidence'] >= RUMOUR_THRESHOLD)
    ].copy()

    if len(high_conf) == 0:
        rumour_released = pd.DataFrame()
        rumour_pending_review = pd.DataFrame()
    else:
        pending_mask = (
            (high_conf['rumour_confidence'] >= RUMOUR_HUMAN_REVIEW_MIN_CONF) &
            (high_conf['rumour_type'].isin(RUMOUR_HUMAN_REVIEW_TYPES))
        )
        rumour_pending_review = high_conf[pending_mask].copy()
        rumour_released = high_conf[~pending_mask].copy()

    # ── Monthly trend (added to df_llm for Output Agent) ─────────────────────
    df_llm = df_llm.copy()
    df_llm['month'] = pd.to_datetime(df_llm['date']).dt.to_period('M')

    monthly = df_llm.groupby('month').agg(
        post_count  =('sentiment', 'count'),
        bullish_pct =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
        bearish_pct =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
    ).sort_index()

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f'\n  Ticker summary ({len(ticker_summary)} tickers):')
    print(ticker_summary.head(10).to_string())

    n_total = len(high_conf)
    n_held = len(rumour_pending_review)
    n_released = len(rumour_released)
    print(f'\n  High-confidence rumours (>= {RUMOUR_THRESHOLD}): {n_total} total')
    if n_total == 0:
        print('  (No high-confidence rumours — this is normal)')
    else:
        print(f'    Released to reports:           {n_released}')
        print(f'    Pending human review (held):  {n_held}  → rumour_pending_review.csv')

    print(f'\n  Monthly trend:')
    for month, row in monthly.iterrows():
        mood = '🟢' if row['bullish_pct'] > row['bearish_pct'] else '🔴'
        print(f'    {mood} {month} | 🟢 {row["bullish_pct"]}% | '
              f'🔴 {row["bearish_pct"]}% | posts: {int(row["post_count"])}')

    # ── Save outputs to run directory ─────────────────────────────────────────
    _save(df_llm,         run_dir, 'sentiment_results.csv')
    _save(ticker_summary, run_dir, 'ticker_summary.csv')
    if n_released > 0:
        _save(rumour_released, run_dir, 'rumour_alerts.csv')
    if n_held > 0:
        _save(rumour_pending_review, run_dir, 'rumour_pending_review.csv')

    print(f'\n✓ Aggregator complete')
    print(f'   Tickers found:   {len(ticker_summary)}')
    print(f'   Rumours (total high-conf): {n_total}')

    return ticker_summary, rumour_released, rumour_pending_review, df_llm


# ── Private helper ────────────────────────────────────────────────────────────

def _save(df, run_dir, filename):
    path = os.path.join(run_dir, filename)
    df.to_csv(path)
    print(f'  Saved → {path}')
