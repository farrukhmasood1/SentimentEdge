"""
SentimentEdge — Agent 4: Aggregator
Combines per-post LLM results into two output tracks:
  Track 1 — ticker-level sentiment summaries (engagement-weighted)
  Track 2 — high-confidence rumour alerts (rumour_confidence >= threshold)

All outputs are saved to the timestamped run directory so every run is
preserved and auditable.

Inputs:  df_llm (from Sentiment Agent), run_dir
Outputs: ticker_summary, rumour_alerts, df_llm (with month column added)
"""

import os
import pandas as pd
from config import RUMOUR_THRESHOLD, LOW_CONF_THRESHOLD, LOW_SAMPLE_THRESHOLD


def run_aggregator(df_llm, run_dir):
    """
    Groups per-post sentiment data into ticker summaries and rumour alerts.
    Saves three CSVs to run_dir.

    Inputs:
        df_llm   — analyzed posts DataFrame from Sentiment Agent
        run_dir  — timestamped run folder path (from logger.create_run_dir)

    Outputs:
        ticker_summary — DataFrame indexed by primary_ticker with columns:
                         post_count, bullish_pct, bearish_pct, neutral_pct,
                         avg_confidence, avg_relevance, sarcastic_count,
                         avg_engagement, low_confidence, low_sample
        rumour_alerts  — DataFrame of posts where is_rumour=True and
                         rumour_confidence >= RUMOUR_THRESHOLD
        df_llm         — input DataFrame with 'month' column added
    """
    print('\n' + '=' * 55)
    print('AGENT 4 — AGGREGATOR')
    print('=' * 55)

    if len(df_llm) == 0:
        print('  ⚠  df_llm is empty — returning empty outputs.')
        return pd.DataFrame(), pd.DataFrame(), df_llm

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

    # ── Track 2: rumour alerts ────────────────────────────────────────────────
    rumour_alerts = df_llm[
        (df_llm['is_rumour'] == True) &
        (df_llm['rumour_confidence'] >= RUMOUR_THRESHOLD)
    ].copy()

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

    print(f'\n  Rumour alerts (confidence >= {RUMOUR_THRESHOLD}): {len(rumour_alerts)}')
    if len(rumour_alerts) == 0:
        print('  (No high-confidence rumours detected — this is normal)')

    print(f'\n  Monthly trend:')
    for month, row in monthly.iterrows():
        mood = '🟢' if row['bullish_pct'] > row['bearish_pct'] else '🔴'
        print(f'    {mood} {month} | 🟢 {row["bullish_pct"]}% | '
              f'🔴 {row["bearish_pct"]}% | posts: {int(row["post_count"])}')

    # ── Save outputs to run directory ─────────────────────────────────────────
    _save(df_llm,         run_dir, 'sentiment_results.csv')
    _save(ticker_summary, run_dir, 'ticker_summary.csv')
    if len(rumour_alerts) > 0:
        _save(rumour_alerts, run_dir, 'rumour_alerts.csv')

    print(f'\n✓ Aggregator complete')
    print(f'   Tickers found:   {len(ticker_summary)}')
    print(f'   Rumours flagged: {len(rumour_alerts)}')

    return ticker_summary, rumour_alerts, df_llm


# ── Private helper ────────────────────────────────────────────────────────────

def _save(df, run_dir, filename):
    path = os.path.join(run_dir, filename)
    df.to_csv(path)
    print(f'  Saved → {path}')
