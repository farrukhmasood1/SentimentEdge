"""
SentimentEdge — Agent 5: Output Agent
Human-facing layer. Three report functions:
  1. query_ticker()     — ticker sentiment report
  2. run_trend_alerts() — daily sentiment shifts over last 7 days
  3. compare_tickers()  — side-by-side comparison of two tickers

Inputs:  ticker_summary, rumour_alerts, df_llm, rumour_pending_review (from Aggregator)
Outputs: formatted terminal reports
"""

import json
import pandas as pd
from config import LOW_CONF_THRESHOLD, LOW_SAMPLE_THRESHOLD, SHIFT_THRESHOLD, MIN_POSTS_PER_DAY

W = 62  # report width

# Governance copy for held high-stakes rumours (document-only review; see README)
RUMOUR_REVIEWER_LABEL = "Designated compliance or editorial reviewer"
RUMOUR_REVIEW_SLA_HOURS = 24


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION 1 — query_ticker
# ══════════════════════════════════════════════════════════════════════════════

def query_ticker(ticker, ticker_summary, rumour_alerts, df_llm, rumour_pending_review=None):
    if rumour_pending_review is None:
        rumour_pending_review = pd.DataFrame()

    ticker = ticker.upper().strip()

    _header(f'TICKER REPORT — ${ticker}')

    if ticker not in ticker_summary.index:
        print(f'\n  No data found for ${ticker}.')
        print(f'  Available tickers: {list(ticker_summary.index)}')
        print('═' * W)
        return

    row = ticker_summary.loc[ticker]

    warnings = []
    if row['avg_confidence'] < LOW_CONF_THRESHOLD:
        warnings.append('LOW CONFIDENCE')
    if row['low_sample']:
        warnings.append(f'LOW SAMPLE (<{LOW_SAMPLE_THRESHOLD} posts)')
    if warnings:
        print(f'\n  ⚠  {" | ".join(warnings)}')

    # ── Sentiment Summary ────────────────────────────────────────────────────
    _section('SENTIMENT SUMMARY')
    print(f'  Posts analysed   {int(row["post_count"]):<8}  '
          f'Avg confidence   {row["avg_confidence"]:.2f}')
    print(f'  Avg relevance    {row["avg_relevance"]:<8.2f}  '
          f'Sarcastic posts  {int(row["sarcastic_count"])}')

    bull, bear, neut = row['bullish_pct'], row['bearish_pct'], row['neutral_pct']
    print()
    print(f'  🟢 Bullish  {"█" * int(bull / 5):<20} {bull}%')
    print(f'  🔴 Bearish  {"█" * int(bear / 5):<20} {bear}%')
    print(f'  🟡 Neutral  {"█" * int(neut / 5):<20} {neut}%')

    sarcasm_rate = row['sarcastic_count'] / row['post_count']
    if sarcasm_rate > 0.1:
        print(f'\n  ⚠  High sarcasm rate ({sarcasm_rate * 100:.0f}%) — scores adjusted by Claude')

    # ── Emotion Breakdown ────────────────────────────────────────────────────
    _section('EMOTION BREAKDOWN')
    ticker_posts = df_llm[df_llm['primary_ticker'] == ticker].copy()
    all_emotions = _collect_emotions(ticker_posts)
    if all_emotions:
        emotion_counts = pd.Series(all_emotions).value_counts()
        total = len(all_emotions)
        for emotion, count in emotion_counts.items():
            pct = count / total * 100
            print(f'  {emotion:<16} {"█" * int(pct / 5):<20} {count} mentions ({pct:.0f}%)')
    else:
        print('  No emotion data available')

    # ── Post Type Breakdown ──────────────────────────────────────────────────
    _section('POST TYPE BREAKDOWN')
    type_breakdown = ticker_posts.groupby('post_type').agg(
        count       =('sentiment', 'count'),
        bullish_pct =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
        bearish_pct =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
    ).sort_values('count', ascending=False)
    for ptype, trow in type_breakdown.iterrows():
        print(f'  {ptype:<14}  posts: {int(trow["count"]):>3}   '
              f'🟢 {trow["bullish_pct"]:>5}%   🔴 {trow["bearish_pct"]:>5}%')

    # ── Monthly Sentiment Timeline ───────────────────────────────────────────
    _section('MONTHLY SENTIMENT TIMELINE')
    ticker_posts = ticker_posts.copy()
    ticker_posts['month'] = pd.to_datetime(ticker_posts['date']).dt.to_period('M')
    ticker_monthly = ticker_posts.groupby('month').agg(
        post_count  =('sentiment', 'count'),
        bullish_pct =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
        bearish_pct =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
    ).sort_index()
    if len(ticker_monthly) == 0:
        print('  Not enough data for monthly breakdown')
    else:
        for month, mrow in ticker_monthly.iterrows():
            mood = '🟢' if mrow['bullish_pct'] > mrow['bearish_pct'] else '🔴'
            print(f'  {mood} {month}   🟢 {mrow["bullish_pct"]:>5}%   '
                  f'🔴 {mrow["bearish_pct"]:>5}%   posts: {int(mrow["post_count"])}')

    # ── Top Key Insights ─────────────────────────────────────────────────────
    _section('TOP KEY INSIGHTS')
    top_posts = ticker_posts.nlargest(3, 'engagement_score')
    for _, p in top_posts.iterrows():
        mood    = '🟢' if p['sentiment'] == 'bullish' else \
                  '🔴' if p['sentiment'] == 'bearish' else '🟡'
        sarcasm = '  [SARCASTIC]' if p['is_sarcastic'] else ''
        print(f'\n  {mood} {str(p["title"])[:52]}{sarcasm}')
        print(f'     {p["key_insight"]}')
        print(f'     conf: {p["confidence"]:.2f}   '
              f'type: {p["post_type"]}   score: {int(p["score"])}')
        print(f'     reddit.com{p["permalink"]}')

    # ── Rumour Alerts ────────────────────────────────────────────────────────
    ticker_rumours = (
        rumour_alerts[rumour_alerts['primary_ticker'] == ticker]
        if len(rumour_alerts) > 0 else pd.DataFrame()
    )
    if len(ticker_rumours) > 0:
        _section('⚠  RUMOUR ALERTS')
        for _, r in ticker_rumours.iterrows():
            print(f'  Type        {r["rumour_type"]}')
            print(f'  Summary     {r["rumour_summary"]}')
            print(f'  Confidence  {r["rumour_confidence"]:.2f}')
            print(f'  Source      reddit.com{r["permalink"]}')
            print(f'  ⚠  Unverified social media speculation only.')

    pending_for_ticker = (
        rumour_pending_review[rumour_pending_review['primary_ticker'] == ticker]
        if len(rumour_pending_review) > 0 else pd.DataFrame()
    )
    if len(pending_for_ticker) > 0:
        n = len(pending_for_ticker)
        _section('HELD — HIGH-STAKES RUMOUR (HUMAN REVIEW)')
        print(f'  {n} alert(s) withheld from the report above — not auto-published from the model alone.')
        print(f'  Queue file:  rumour_pending_review.csv  (this run directory)')
        print(f'  Reviewer:    {RUMOUR_REVIEWER_LABEL}')
        print(f'  Target SLA:  triage within {RUMOUR_REVIEW_SLA_HOURS}h (per team policy; evidence in Phase 3 report).')

    _footer(df_llm)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION 2 — run_trend_alerts
# ══════════════════════════════════════════════════════════════════════════════

def run_trend_alerts(df_llm, shift_threshold=SHIFT_THRESHOLD,
                     min_posts_per_day=MIN_POSTS_PER_DAY):
    _header('TREND ALERTS — LAST 7 DAYS')

    if len(df_llm) == 0:
        print('\n  ⚠  No data available.')
        print('═' * W)
        return

    df         = df_llm.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['day']  = df['date'].dt.date
    latest     = df['date'].max()
    seven_ago  = latest - pd.Timedelta(days=7)
    df_week    = df[df['date'] > seven_ago].copy()

    print(f'\n  Period: {seven_ago.strftime("%Y-%m-%d")} → {latest.strftime("%Y-%m-%d")}   '
          f'Shift threshold: {shift_threshold}%')

    if len(df_week) == 0:
        print('\n  ⚠  No posts found in last 7 days.')
        _footer(df_llm)
        return

    min_total     = min_posts_per_day * 3
    ticker_counts = (
        df_week[df_week['primary_ticker'] != 'UNKNOWN']['primary_ticker'].value_counts()
    )
    qualifying = ticker_counts[ticker_counts >= min_total].index.tolist()

    if not qualifying:
        print(f'\n  ⚠  No tickers meet the minimum threshold ({min_total} posts).')
        print(f'  Try lowering MIN_POSTS_PER_DAY in config.py or increasing BATCH_SIZE.')
        _footer(df_llm)
        return

    for ticker in qualifying:
        ticker_df = df_week[df_week['primary_ticker'] == ticker].copy()
        daily     = ticker_df.groupby('day').agg(
            post_count  =('sentiment', 'count'),
            bullish_pct =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
            bearish_pct =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
        ).sort_index()

        print(f'\n  ${ticker}')
        print(f'  {"─" * (W - 4)}')

        prev_bull, prev_bear = None, None
        for day, drow in daily.iterrows():
            mood        = '🟢' if drow['bullish_pct'] > drow['bearish_pct'] else '🔴'
            shift_label = ''
            if prev_bull is not None:
                bull_shift = drow['bullish_pct'] - prev_bull
                bear_shift = drow['bearish_pct'] - prev_bear
                if abs(bull_shift) >= shift_threshold:
                    direction   = '🟢 BULLISH SWING' if bull_shift > 0 else '🔴 BEARISH SWING'
                    shift_label = f'   ↑ {direction} {bull_shift:+.0f}%'
                elif abs(bear_shift) >= shift_threshold:
                    direction   = '🔴 BEARISH SWING' if bear_shift > 0 else '🟢 BULLISH SWING'
                    shift_label = f'   ↑ {direction} {bear_shift:+.0f}%'
            print(f'  {str(day):10}  {mood}   '
                  f'🟢 {drow["bullish_pct"]:>5}%   '
                  f'🔴 {drow["bearish_pct"]:>5}%   '
                  f'posts: {int(drow["post_count"])}'
                  f'{shift_label}')
            prev_bull = drow['bullish_pct']
            prev_bear = drow['bearish_pct']

    _footer(df_llm)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION 3 — compare_tickers
# ══════════════════════════════════════════════════════════════════════════════

def compare_tickers(ticker_a, ticker_b, ticker_summary, df_llm):
    ticker_a = ticker_a.upper().strip()
    ticker_b = ticker_b.upper().strip()

    _header(f'TICKER COMPARISON — ${ticker_a} vs ${ticker_b}')

    missing = [t for t in [ticker_a, ticker_b] if t not in ticker_summary.index]
    if missing:
        print(f'\n  ⚠  No data found for: {", ".join(["$" + t for t in missing])}')
        print(f'  Available tickers: {list(ticker_summary.index)}')
        print('═' * W)
        return

    row_a   = ticker_summary.loc[ticker_a]
    row_b   = ticker_summary.loc[ticker_b]
    posts_a = df_llm[df_llm['primary_ticker'] == ticker_a].copy()
    posts_b = df_llm[df_llm['primary_ticker'] == ticker_b].copy()

    # ── Sentiment Summary ────────────────────────────────────────────────────
    _section('SENTIMENT SUMMARY')
    for ticker, row in [(ticker_a, row_a), (ticker_b, row_b)]:
        warnings = []
        if row['avg_confidence'] < LOW_CONF_THRESHOLD:
            warnings.append('LOW CONFIDENCE')
        if row['low_sample']:
            warnings.append('LOW SAMPLE')
        warn_str = f'   ⚠  {" | ".join(warnings)}' if warnings else ''
        print(f'\n  ${ticker}  ({int(row["post_count"])} posts){warn_str}')
        bull, bear, neut = row['bullish_pct'], row['bearish_pct'], row['neutral_pct']
        print(f'  🟢 Bullish  {"█" * int(bull / 5):<20} {bull}%')
        print(f'  🔴 Bearish  {"█" * int(bear / 5):<20} {bear}%')
        print(f'  🟡 Neutral  {"█" * int(neut / 5):<20} {neut}%')

    # ── Signal Quality Table ─────────────────────────────────────────────────
    _section('SIGNAL QUALITY')
    metrics = [
        ('Avg confidence',
         f'{row_a["avg_confidence"]:.2f}',  f'{row_b["avg_confidence"]:.2f}'),
        ('Avg relevance',
         f'{row_a["avg_relevance"]:.2f}',   f'{row_b["avg_relevance"]:.2f}'),
        ('Post count',
         f'{int(row_a["post_count"])}',     f'{int(row_b["post_count"])}'),
        ('Sarcasm rate',
         f'{row_a["sarcastic_count"] / row_a["post_count"] * 100:.0f}%',
         f'{row_b["sarcastic_count"] / row_b["post_count"] * 100:.0f}%'),
        ('Avg engagement',
         f'{row_a["avg_engagement"]:.0f}',  f'{row_b["avg_engagement"]:.0f}'),
    ]
    print(f'\n  {"Metric":<22} {"$" + ticker_a:<16} {"$" + ticker_b:<16}')
    print(f'  {"─" * (W - 4)}')
    for label, val_a, val_b in metrics:
        print(f'  {label:<22} {val_a:<16} {val_b:<16}')

    # ── Emotion Breakdown ────────────────────────────────────────────────────
    _section('EMOTION BREAKDOWN')
    emotions_a       = _emotion_pcts(posts_a)
    emotions_b       = _emotion_pcts(posts_b)
    all_emotion_keys = sorted(set(list(emotions_a.index) + list(emotions_b.index)))
    if all_emotion_keys:
        print(f'\n  {"Emotion":<22} {"$" + ticker_a:<16} {"$" + ticker_b:<16}')
        print(f'  {"─" * (W - 4)}')
        for emotion in all_emotion_keys:
            print(f'  {emotion:<22} '
                  f'{f"{emotions_a.get(emotion, 0):.0f}%":<16} '
                  f'{f"{emotions_b.get(emotion, 0):.0f}%":<16}')
    else:
        print('  No emotion data available')

    # ── Monthly Sentiment Timeline ───────────────────────────────────────────
    _section('MONTHLY SENTIMENT TIMELINE')
    for ticker, posts in [(ticker_a, posts_a), (ticker_b, posts_b)]:
        print(f'\n  ${ticker}:')
        monthly = _monthly_trend(posts)
        if len(monthly) == 0:
            print('  No monthly data')
        else:
            for month, mrow in monthly.iterrows():
                mood = '🟢' if mrow['bullish_pct'] > mrow['bearish_pct'] else '🔴'
                print(f'  {mood} {month}   🟢 {mrow["bullish_pct"]:>5}%   '
                      f'🔴 {mrow["bearish_pct"]:>5}%   posts: {int(mrow["post_count"])}')

    # ── Top Key Insights ─────────────────────────────────────────────────────
    _section('TOP KEY INSIGHTS')
    for ticker, posts in [(ticker_a, posts_a), (ticker_b, posts_b)]:
        print(f'\n  ${ticker}:')
        if len(posts) == 0:
            print('  No posts available')
            continue
        top = posts.nlargest(2, 'engagement_score')
        for _, p in top.iterrows():
            mood    = '🟢' if p['sentiment'] == 'bullish' else \
                      '🔴' if p['sentiment'] == 'bearish' else '🟡'
            sarcasm = '  [SARCASTIC]' if p['is_sarcastic'] else ''
            print(f'\n  {mood} {str(p["title"])[:52]}{sarcasm}')
            print(f'     {p["key_insight"]}')
            print(f'     conf: {p["confidence"]:.2f}   '
                  f'type: {p["post_type"]}   score: {int(p["score"])}')
            print(f'     reddit.com{p["permalink"]}')

    _footer(df_llm)


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers
# ══════════════════════════════════════════════════════════════════════════════

def _header(title):
    print('\n' + '═' * W)
    print(f'  {title}')
    print('═' * W)


def _section(title):
    print(f'\n  {title}')
    print(f'  {"─" * (W - 4)}')


def _footer(df_llm):
    print(f'\n  {"─" * (W - 4)}')
    print(f'  ⚠  Not financial advice. Source: r/wallstreetbets')
    print(f'  Data up to: {pd.to_datetime(df_llm["date"]).max().strftime("%Y-%m-%d")}')
    print('═' * W)


def _collect_emotions(posts):
    all_emotions = []
    for emotions in posts['emotions']:
        if isinstance(emotions, list):
            all_emotions.extend(emotions)
        elif isinstance(emotions, str):
            try:
                all_emotions.extend(json.loads(emotions))
            except Exception:
                pass
    return all_emotions


def _emotion_pcts(posts):
    all_emotions = _collect_emotions(posts)
    if not all_emotions:
        return pd.Series(dtype=float)
    counts = pd.Series(all_emotions).value_counts()
    return (counts / counts.sum() * 100).round(1)


def _monthly_trend(posts):
    if len(posts) == 0:
        return pd.DataFrame()
    posts          = posts.copy()
    posts['month'] = pd.to_datetime(posts['date']).dt.to_period('M')
    return posts.groupby('month').agg(
        post_count  =('sentiment', 'count'),
        bullish_pct =('sentiment', lambda x: round((x == 'bullish').sum() / len(x) * 100, 1)),
        bearish_pct =('sentiment', lambda x: round((x == 'bearish').sum() / len(x) * 100, 1)),
    ).sort_index()
