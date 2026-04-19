"""
SentimentEdge — Agent 2: Filter Agent
Hard gate before LLM analysis. Removes noise, merges bundled comments,
computes engagement scores, and builds the llm_text field sent to Claude.
No post reaches the Sentiment Agent unless it passes every rule here.

Inputs:  df_posts_raw, df_comments_raw, min_score
Outputs: df_filtered — clean posts ready for Sentiment Agent
"""

import pandas as pd
from utils.comment_bundler import bundle_comments
from config import MIN_POST_SCORE


def run_filter(df_posts_raw, df_comments_raw, min_score=MIN_POST_SCORE):
    """
    Cleans posts, merges bundled comments, applies filter rules,
    computes engagement scores, and builds the llm_text field.

    Filter rules applied in order:
      1. Keep posts that have body content OR bundled comments
         (handles the 64% deleted-post problem)
      2. Remove posts with score below min_score (default 10)
      3. Remove stickied mod posts (if column present)

    Engagement score formula:
      engagement_score = (score × 0.7) + (num_comments × 0.3)

    llm_text field:
      Title + Body (capped at 500 chars, skipped if deleted) + Top comments

    Inputs:
        df_posts_raw    — raw posts from Collector
        df_comments_raw — raw comments from Collector
        min_score       — minimum upvote score (default from config)

    Outputs:
        df_filtered — DataFrame with columns:
          post_id, text, title, body, score, upvote_ratio, num_comments,
          total_awards, is_deleted, flair, author, date, created_utc,
          subreddit, permalink, top_comments, engagement_score, llm_text
    """
    print('\n' + '=' * 55)
    print('AGENT 2 — FILTER AGENT')
    print('=' * 55)
    print(f'Input: {len(df_posts_raw)} posts')

    # ── Bundle comments ───────────────────────────────────────────────────────
    df_bundled = bundle_comments(df_comments_raw)

    # ── Clean posts ───────────────────────────────────────────────────────────
    _DELETED = {'[removed]', '[deleted]', 'nan', 'None', ''}

    def _combine_text(row):
        title = str(row['title']).strip()
        body  = str(row['selftext']).strip()
        return title if body in _DELETED else f'{title}. {body}'

    df_posts_raw = df_posts_raw.copy()
    df_posts_raw['text']       = df_posts_raw.apply(_combine_text, axis=1)
    df_posts_raw['is_deleted'] = df_posts_raw['selftext'].astype(str).isin(_DELETED)
    df_posts_raw['date']       = pd.to_datetime(
        df_posts_raw['created_utc'], unit='s', errors='coerce'
    )
    df_posts_raw['score']        = pd.to_numeric(df_posts_raw['score'],        errors='coerce')
    df_posts_raw['num_comments'] = pd.to_numeric(df_posts_raw['num_comments'], errors='coerce')

    df_posts_clean = pd.DataFrame({
        'post_id':      df_posts_raw['id'],
        'text':         df_posts_raw['text'],
        'title':        df_posts_raw['title'],
        'body':         df_posts_raw['selftext'],
        'score':        df_posts_raw['score'],
        'upvote_ratio': df_posts_raw['upvote_ratio'],
        'num_comments': df_posts_raw['num_comments'],
        'total_awards': df_posts_raw['total_awards_received'],
        'is_deleted':   df_posts_raw['is_deleted'],
        'flair':        df_posts_raw['link_flair_text'],
        'author':       df_posts_raw['author'],
        'date':         df_posts_raw['date'],
        'created_utc':  df_posts_raw['created_utc'],
        'subreddit':    df_posts_raw['subreddit'],
        'permalink':    df_posts_raw['permalink'],
    })

    # ── Merge with bundled comments ───────────────────────────────────────────
    df_merged = df_posts_clean.merge(df_bundled, on='post_id', how='left')
    df_merged['top_comments'] = df_merged['top_comments'].fillna('')

    # ── Filter Rule 1: body OR comments ──────────────────────────────────────
    has_body     = ~df_merged['is_deleted']
    has_comments = df_merged['top_comments'] != ''
    print(f'  Posts with body content:      {has_body.sum()}')
    print(f'  Posts with bundled comments:  {has_comments.sum()}')
    print(f'  Posts with body OR comments:  {(has_body | has_comments).sum()}')
    df_filtered  = df_merged[has_body | has_comments].copy()

    # ── Filter Rule 2: minimum score ─────────────────────────────────────────
    below_score  = (df_filtered['score'] < min_score).sum()
    print(f'  Posts removed by score (<{min_score}): {below_score}')
    df_filtered = df_filtered[df_filtered['score'] >= min_score].copy()
    print(f'  After score filter:           {len(df_filtered)}')

    # ── Filter Rule 3: stickied posts ────────────────────────────────────────
    if 'stickied' in df_posts_raw.columns:
        stickied_ids = set(df_posts_raw.loc[df_posts_raw['stickied'] == True, 'id'])
        df_filtered  = df_filtered[~df_filtered['post_id'].isin(stickied_ids)].copy()
        print(f'  After stickied-post removal:  {len(df_filtered)}')

    if len(df_filtered) == 0:
        print('  ⚠  WARNING: No posts survived filtering. '
              'Try lowering MIN_POST_SCORE in config.py.')
        return df_filtered

    # ── Engagement score ──────────────────────────────────────────────────────
    df_filtered['score']            = df_filtered['score'].fillna(0)
    df_filtered['num_comments']     = df_filtered['num_comments'].fillna(0)
    df_filtered['engagement_score'] = (
        df_filtered['score'] * 0.7 +
        df_filtered['num_comments'] * 0.3
    )

    # ── Build llm_text ────────────────────────────────────────────────────────
    def _build_llm_text(row):
        parts = [f"Title: {str(row['title']).strip()}"]
        if not row['is_deleted']:
            body = str(row['body']).strip()[:500]
            if body:
                parts.append(f'Body: {body}')
        if row['top_comments']:
            parts.append(f'Top comments:\n{row["top_comments"]}')
        return '\n'.join(parts)

    df_filtered['llm_text'] = df_filtered.apply(_build_llm_text, axis=1)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_in  = len(df_posts_raw)
    n_out = len(df_filtered)
    print(f'\n✓ Filter Agent complete')
    print(f'   Input:     {n_in}')
    print(f'   Output:    {n_out}')
    print(f'   Removed:   {n_in - n_out}')
    print(f'   Retention: {n_out / n_in * 100:.1f}%')
    print(f'   Engagement max: {df_filtered["engagement_score"].max():.0f}')
    print(f'   Engagement avg: {df_filtered["engagement_score"].mean():.0f}')

    return df_filtered
