"""
SentimentEdge — Comment Bundler
Utility used by Filter Agent. Cleans raw comments and bundles the top N
per post into a single text field ready for LLM input.
"""

import pandas as pd
from config import TOP_N_COMMENTS


def bundle_comments(df_comments_raw, top_n=TOP_N_COMMENTS):
    """
    Cleans comments and bundles the top N per post by score.

    Steps:
      1. Keep only top-level comments (parent_id starts with 't3_')
      2. Remove deleted / removed / empty bodies
      3. Remove comments that are just image URLs (start with http/https)
      4. Remove score < 2
      5. Remove comments shorter than 10 characters (emoji-only noise)
      6. Strip 't3_' prefix from link_id to create post_id that matches posts.id
      7. Group by post_id, take top N by score
      8. Format each comment as '[Score: X] text' capped at 300 chars

    Inputs:
        df_comments_raw  — raw comments DataFrame from Collector
        top_n            — max comments to bundle per post (default from config)

    Outputs:
        df_bundled — DataFrame with columns [post_id, top_comments]
    """
    # Step 1 — top-level comments only
    df_top = df_comments_raw[
        df_comments_raw['parent_id'].astype(str).str.startswith('t3_')
    ].copy()

    # Step 2 — remove deleted/removed bodies
    junk = {'[removed]', '[deleted]', '', 'nan', 'None'}
    df_top = df_top[~df_top['body'].astype(str).isin(junk)].copy()

    # Step 3 — remove image URL-only comments
    df_top = df_top[
        ~df_top['body'].astype(str).str.strip().str.startswith('http')
    ].copy()

    # Step 4 — score filter
    df_top['score'] = pd.to_numeric(df_top['score'], errors='coerce').fillna(0)
    df_top = df_top[df_top['score'] >= 2].copy()

    # Step 5 — length filter
    df_top = df_top[df_top['body'].astype(str).str.len() >= 10].copy()

    if len(df_top) == 0:
        print('  ⚠  No usable comments after cleaning.')
        return pd.DataFrame(columns=['post_id', 'top_comments'])

    # Step 6 — create post_id column
    df_top['post_id'] = (
        df_top['link_id'].astype(str).str.replace('t3_', '', regex=False)
    )

    df_top_clean = pd.DataFrame({
        'post_id': df_top['post_id'],
        'body':    df_top['body'],
        'score':   df_top['score'],
    })

    # Steps 7–8 — bundle top N per post
    def bundle(group):
        top   = group.nlargest(top_n, 'score')
        parts = []
        for _, row in top.iterrows():
            text = str(row['body']).strip()[:300]
            parts.append(f"[Score: {int(row['score'])}] {text}")
        return '\n'.join(parts)

    df_bundled = (
        df_top_clean
        .groupby('post_id')[['score', 'body']]
        .apply(bundle, include_groups=False)
        .reset_index()
    )
    df_bundled.columns = ['post_id', 'top_comments']

    print(f'  Bundled comments for {len(df_bundled)} unique posts')
    return df_bundled
