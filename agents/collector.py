"""
SentimentEdge — Agent 1: Collector
Loads raw posts and comments from JSONL files on disk.
Platform-agnostic by design — swapping to a live Reddit API (PRAW) or
any other source only requires changing this file.

Inputs:  posts_file path, comments_file path
Outputs: df_posts_raw, df_comments_raw (raw DataFrames, no cleaning)
"""

import json
import pandas as pd


def run_collector(posts_file, comments_file):
    """
    Loads posts and comments from JSONL files.
    Returns raw DataFrames — no cleaning or filtering done here.

    Inputs:
        posts_file    — path to JSONL file of Reddit posts
        comments_file — path to JSONL file of Reddit comments

    Outputs:
        df_posts_raw    — all posts, all original columns preserved
        df_comments_raw — all comments, all original columns preserved

    Key columns in posts JSONL:
        id, title, selftext, score, upvote_ratio, num_comments,
        total_awards_received, link_flair_text, author, created_utc,
        subreddit, permalink, stickied

    Key columns in comments JSONL:
        id, body, score, link_id, parent_id, author, created_utc, subreddit
    """
    print('=' * 55)
    print('AGENT 1 — COLLECTOR')
    print('=' * 55)

    df_posts_raw    = _load_jsonl(posts_file,    label='posts')
    df_comments_raw = _load_jsonl(comments_file, label='comments')

    print(f'\n✓ Collector complete')
    print(f'   Posts loaded:    {len(df_posts_raw)}')
    print(f'   Comments loaded: {len(df_comments_raw)}')
    return df_posts_raw, df_comments_raw


# ── Private helper ────────────────────────────────────────────────────────────

def _load_jsonl(filepath, label):
    """
    Reads a JSONL file line by line.
    Skips malformed lines with a warning rather than crashing.
    Raises FileNotFoundError with a clear message if the file is missing.
    """
    if not __import__('os').path.exists(filepath):
        raise FileNotFoundError(
            f'\n  ✗ {label} file not found: {filepath}\n'
            f'  Place your JSONL files in the data/ folder and update config.py.'
        )

    print(f'Loading {label}...')
    records = []
    skipped = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
                if skipped <= 5:
                    print(f'  ⚠  Skipping malformed line {line_num} in {label} file')

    if skipped > 5:
        print(f'  ⚠  {skipped} malformed lines skipped in {label} file (showing first 5)')

    df = pd.DataFrame(records)
    print(f'  ✓ Loaded {len(df)} {label}')
    return df
