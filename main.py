"""
SentimentEdge — Main Pipeline
Runs all five agents in sequence and logs every run to a timestamped folder.

Pipeline:
  Collector → Filter → Sentiment → Aggregator → Output

Each run produces:
  outputs/runs/run_YYYYMMDD_HHMMSS/
    trace.txt              ← full terminal output
    sentiment_results.csv  ← per-post LLM results
    ticker_summary.csv     ← aggregated ticker data
    rumour_alerts.csv      ← high-confidence rumour posts (if any)
    run_metadata.json      ← config snapshot + pipeline stats

Usage:
  Full pipeline:
    python main.py

  Replay output from a previous run (skips agents 1-4, no API calls):
    python main.py --replay outputs/runs/run_YYYYMMDD_HHMMSS

  Set your Anthropic API key before running:
    export ANTHROPIC_API_KEY=your_key_here
  Or edit API_KEY directly in config.py (not recommended for shared repos).
"""

import ast
import sys
import time
import argparse
import os
import pandas as pd
from datetime import datetime

from config import (
    POSTS_FILE, COMMENTS_FILE, API_KEY, BATCH_SIZE,
    MIN_POST_SCORE, RUMOUR_THRESHOLD, LOW_CONF_THRESHOLD,
    TOP_N_COMMENTS, SHIFT_THRESHOLD, MIN_POSTS_PER_DAY,
)
from utils.logger import create_run_dir, TeeLogger, save_metadata
from agents.collector     import run_collector
from agents.filter_agent  import run_filter
from agents.aggregator    import run_aggregator
from agents.output_agent  import query_ticker, run_trend_alerts, compare_tickers


def main():
    # ── Set up run directory and logger ───────────────────────────────────────
    run_dir = create_run_dir()
    logger  = TeeLogger(run_dir)
    sys.stdout = logger

    pipeline_start = time.time()
    print(f'SentimentEdge — Run started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Run directory: {run_dir}')
    print(f'Batch size:    {BATCH_SIZE} posts')
    print(f'Model:         claude-sonnet-4-20250514 (prompt caching enabled)')

    # ── Agent 1: Collect ──────────────────────────────────────────────────────
    df_posts_raw, df_comments_raw = run_collector(POSTS_FILE, COMMENTS_FILE)
    n_posts_raw    = len(df_posts_raw)
    n_comments_raw = len(df_comments_raw)

    # ── Agent 2: Filter ───────────────────────────────────────────────────────
    df_filtered = run_filter(df_posts_raw, df_comments_raw)
    n_filtered  = len(df_filtered)

    del df_posts_raw, df_comments_raw   # free RAM after merge

    if n_filtered == 0:
        print('\n✗ Pipeline stopped — no posts survived filtering.')
        _save_metadata_and_close(
            logger, run_dir, pipeline_start,
            n_posts_raw=n_posts_raw, n_comments_raw=n_comments_raw,
            n_filtered=0, n_analyzed=0, errors=0,
            tickers_found=0, rumours_flagged=0,
        )
        return

    # ── Agent 3: Sentiment ────────────────────────────────────────────────────
    from agents.sentiment_agent import run_sentiment_agent

    df_llm     = run_sentiment_agent(df_filtered, API_KEY, batch_size=BATCH_SIZE)
    n_analyzed = len(df_llm)
    # errors = posts sent to Claude that returned None (true API failures)
    # NOT the same as posts that didn't survive the filter
    n_sent     = min(BATCH_SIZE, n_filtered)
    errors     = n_sent - n_analyzed

    if n_analyzed == 0:
        print('\n✗ Pipeline stopped — Sentiment Agent returned no results.')
        _save_metadata_and_close(
            logger, run_dir, pipeline_start,
            n_posts_raw=n_posts_raw, n_comments_raw=n_comments_raw,
            n_filtered=n_filtered, n_analyzed=0, errors=errors,
            tickers_found=0, rumours_flagged=0,
        )
        return

    # ── Agent 4: Aggregate ────────────────────────────────────────────────────
    ticker_summary, rumour_alerts, df_llm = run_aggregator(df_llm, run_dir)

    # ── Agent 5: Output ───────────────────────────────────────────────────────
    # Show reports for the top tickers by post count
    top_tickers = (
        ticker_summary.head(3).index.tolist()
        if len(ticker_summary) >= 3
        else ticker_summary.index.tolist()
    )

    for ticker in top_tickers:
        query_ticker(ticker, ticker_summary, rumour_alerts, df_llm)

    run_trend_alerts(df_llm)

    if len(top_tickers) >= 2:
        compare_tickers(top_tickers[0], top_tickers[1], ticker_summary, df_llm)

    # ── Save metadata and close logger ────────────────────────────────────────
    _save_metadata_and_close(
        logger, run_dir, pipeline_start,
        n_posts_raw=n_posts_raw, n_comments_raw=n_comments_raw,
        n_filtered=n_filtered, n_analyzed=n_analyzed, errors=errors,
        tickers_found=len(ticker_summary),
        rumours_flagged=len(rumour_alerts),
        avg_confidence=round(float(df_llm['confidence'].mean()), 2) if n_analyzed > 0 else 0,
        sarcastic_count=int(df_llm['is_sarcastic'].sum()) if n_analyzed > 0 else 0,
    )


# ── Private helper ────────────────────────────────────────────────────────────

def _save_metadata_and_close(logger, run_dir, pipeline_start, **stats):
    elapsed = round(time.time() - pipeline_start, 1)
    metadata = {
        'run_timestamp':             datetime.now().isoformat(),
        'run_dir':                   run_dir,
        'config': {
            'batch_size':            BATCH_SIZE,
            'min_post_score':        MIN_POST_SCORE,
            'rumour_threshold':      RUMOUR_THRESHOLD,
            'low_conf_threshold':    LOW_CONF_THRESHOLD,
            'top_n_comments':        TOP_N_COMMENTS,
            'shift_threshold':       SHIFT_THRESHOLD,
            'min_posts_per_day':     MIN_POSTS_PER_DAY,
        },
        'pipeline_duration_seconds': elapsed,
        **stats,
    }
    save_metadata(metadata, run_dir)
    print(f'\nTotal pipeline time: {elapsed}s')
    print(f'All outputs saved to: {run_dir}')
    logger.close()


def _latest_run_dir():
    """Returns the most recent saved run directory, or None."""
    dirs = []
    for runs_root in (os.path.join('outputs', 'runs'), os.path.join('outputs', 'sample_runs')):
        if not os.path.exists(runs_root):
            continue
        dirs.extend(
            os.path.join(runs_root, d)
            for d in os.listdir(runs_root)
            if d.startswith('run_') and os.path.isdir(os.path.join(runs_root, d))
        )
    return max(dirs) if dirs else None  # lexicographic max == most recent timestamp


def replay(run_dir=None):
    """
    Loads saved CSVs from a previous run and re-runs the output agent.
    Skips agents 1-4 entirely — no data loading, filtering, or API calls.

    Usage:
        python main.py --replay                          # uses most recent run
        python main.py --replay outputs/runs/run_XXX    # uses specific run
    """
    if run_dir is None:
        run_dir = _latest_run_dir()
        if run_dir is None:
            print('✗ No previous runs found under outputs/runs/ or outputs/sample_runs/. Run the full pipeline first.')
            return
        print(f'SentimentEdge — Replaying most recent run: {run_dir}')
    else:
        print(f'SentimentEdge — Replaying output from: {run_dir}')

    sentiment_path = os.path.join(run_dir, 'sentiment_results.csv')
    summary_path   = os.path.join(run_dir, 'ticker_summary.csv')
    rumours_path   = os.path.join(run_dir, 'rumour_alerts.csv')

    if not os.path.exists(sentiment_path):
        print(f'✗ sentiment_results.csv not found in {run_dir}')
        return
    if not os.path.exists(summary_path):
        print(f'✗ ticker_summary.csv not found in {run_dir}')
        return

    df_llm         = pd.read_csv(sentiment_path, index_col=0)
    ticker_summary = pd.read_csv(summary_path,   index_col=0)
    rumour_alerts  = (
        pd.read_csv(rumours_path, index_col=0)
        if os.path.exists(rumours_path)
        else pd.DataFrame()
    )

    # Restore list columns that CSV serialises as strings
    for col in ('emotions', 'tickers'):
        if col in df_llm.columns:
            df_llm[col] = df_llm[col].apply(
                lambda v: ast.literal_eval(v) if isinstance(v, str) else v
            )

    # ── Agent 5: Output ───────────────────────────────────────────────────────
    top_tickers = (
        ticker_summary.head(3).index.tolist()
        if len(ticker_summary) >= 3
        else ticker_summary.index.tolist()
    )

    for ticker in top_tickers:
        query_ticker(ticker, ticker_summary, rumour_alerts, df_llm)

    run_trend_alerts(df_llm)

    if len(top_tickers) >= 2:
        compare_tickers(top_tickers[0], top_tickers[1], ticker_summary, df_llm)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SentimentEdge pipeline')
    parser.add_argument(
        '--replay',
        nargs='?',
        const='latest',
        metavar='RUN_DIR',
        help='Replay output from a previous run (skips agents 1-4). '
             'Omit RUN_DIR to use the most recent run automatically.',
    )
    args = parser.parse_args()

    if args.replay is not None:
        replay(None if args.replay == 'latest' else args.replay)
    else:
        main()
