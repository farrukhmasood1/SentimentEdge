#!/usr/bin/env python3
"""
Build a stratified random sample for sarcasm human evaluation.

Reconstructs the exact user message sent to Claude (Sentiment Agent):
  llm_text[:800] + Flair / Upvotes / Comments lines
where llm_text comes from the Filter Agent (title + body cap + bundled comments).

Requires the same posts + comments JSONL files used for that sentiment run.
Run from the SentimentEdge directory.

Usage:
  python scripts/build_sarcasm_annotation_sheet.py \\
    --sentiment outputs/runs/run_20260425_174443/sentiment_results.csv \\
    --posts data/r_wallstreetbets_posts.jsonl \\
    --comments data/r_wallstreetbets_comments.jsonl

Label scheme (fill manually): S = sarcastic, N = not sarcastic, U = uncertain
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.collector import run_collector
from agents.filter_agent import run_filter
from config import COMMENTS_FILE, POSTS_FILE


def _stratified_sample(df: pd.DataFrame, n: int, col: str, seed: int) -> pd.DataFrame:
    """Prefer ~n/2 rows per class (model is_sarcastic); fill shortfall from the other class."""
    df = df.reset_index(drop=True)
    pos = df[df[col] == True]
    neg = df[df[col] == False]
    half = n // 2

    take_pos = min(len(pos), half)
    take_neg = min(len(neg), n - take_pos)

    parts = []
    if take_pos and len(pos):
        parts.append(pos.sample(n=take_pos, random_state=seed))
    if take_neg and len(neg):
        parts.append(neg.sample(n=take_neg, random_state=seed + 1))

    if not parts:
        return df.head(min(n, len(df)))

    out = pd.concat(parts, axis=0)
    if len(out) < n:
        used_idx = set(out.index)
        rest = df.loc[~df.index.isin(used_idx)]
        need = min(n - len(out), len(rest))
        if need > 0:
            out = pd.concat([out, rest.sample(n=need, random_state=seed + 2)], axis=0)

    return out.head(n).reset_index(drop=True)


def _build_model_user_content(llm_text: str, flair, score, num_comments) -> str:
    """Matches agents/sentiment_agent.py analyze_post() user_content."""
    lt = '' if llm_text is None or (isinstance(llm_text, float) and pd.isna(llm_text)) else str(llm_text)
    fl = '' if flair is None or (isinstance(flair, float) and pd.isna(flair)) else str(flair)
    sc = int(float(score)) if score is not None and not (isinstance(score, float) and pd.isna(score)) else 0
    nc = int(float(num_comments)) if num_comments is not None and not (
        isinstance(num_comments, float) and pd.isna(num_comments)
    ) else 0
    return (
        f'{lt[:800]}\n\n'
        f'Flair: {fl}\n'
        f'Upvotes: {sc}\n'
        f'Comments: {nc}'
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build sarcasm annotation Excel with exact LLM user input (filter llm_text + truncation)'
    )
    parser.add_argument('--sentiment', type=Path, required=True, help='Path to sentiment_results.csv')
    parser.add_argument(
        '--posts',
        type=Path,
        default=None,
        help=f'Posts JSONL (default: {POSTS_FILE})',
    )
    parser.add_argument(
        '--comments',
        type=Path,
        default=None,
        help=f'Comments JSONL (default: {COMMENTS_FILE})',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('eval/sarcasm_annotation_sample_100.xlsx'),
        help='Output .xlsx path (default: eval/sarcasm_annotation_sample_100.xlsx)',
    )
    parser.add_argument('--n', type=int, default=100, help='Sample size (default: 100)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    posts_path = Path(args.posts) if args.posts else Path(POSTS_FILE)
    comments_path = Path(args.comments) if args.comments else Path(COMMENTS_FILE)

    if not args.sentiment.exists():
        print(f'✗ Sentiment file not found: {args.sentiment}', file=sys.stderr)
        sys.exit(1)
    if not posts_path.exists() or not comments_path.exists():
        print(f'✗ Posts or comments file missing:\n  {posts_path}\n  {comments_path}', file=sys.stderr)
        sys.exit(1)

    print('Loading raw data and running Filter Agent (same as pipeline)…')
    df_posts_raw, df_comments_raw = run_collector(str(posts_path), str(comments_path))
    df_filtered = run_filter(df_posts_raw, df_comments_raw)

    llm_lookup = df_filtered[['post_id', 'llm_text']].copy()
    llm_lookup['post_id'] = llm_lookup['post_id'].astype(str)

    df_sent = pd.read_csv(args.sentiment, index_col=0)
    if 'post_id' not in df_sent.columns or 'is_sarcastic' not in df_sent.columns:
        print('✗ sentiment_results.csv must contain post_id and is_sarcastic', file=sys.stderr)
        sys.exit(1)

    df_sent['post_id'] = df_sent['post_id'].astype(str)
    df_sent['is_sarcastic'] = df_sent['is_sarcastic'].astype(bool)

    merged = df_sent.merge(llm_lookup, on='post_id', how='inner')
    if len(merged) < len(df_sent):
        print(f'  Note: {len(df_sent) - len(merged)} sentiment rows not found in filtered posts (skipped).')

    if len(merged) == 0:
        print('✗ No rows after joining sentiment with filtered posts. Check JSONL paths match the run.', file=sys.stderr)
        sys.exit(1)

    n_target = min(args.n, len(merged))
    if n_target < args.n:
        print(f'  Warning: only {len(merged)} rows available; writing {n_target} rows.')

    sampled = _stratified_sample(merged, n_target, 'is_sarcastic', args.seed)

    rows = []
    for case_id, (_, r) in enumerate(sampled.iterrows(), start=1):
        # flair / score / num_comments come from sentiment row (same values as filter df for that post)
        user_msg = _build_model_user_content(
            r['llm_text'], r.get('flair'), r.get('score'), r.get('num_comments')
        )
        rows.append(
            {
                'case_id': case_id,
                'post_id': str(r['post_id']),
                'permalink': str(r.get('permalink', '')),
                'title': str(r.get('title', '')),
                'model_user_content': user_msg,
                'model_is_sarcastic': bool(r['is_sarcastic']),
                'model_confidence': r.get('confidence', ''),
                'post_type': r.get('post_type', ''),
                'person_1_label': '',
                'person_2_label': '',
                'adjudicated': '',
                'notes': '',
            }
        )

    out_df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_excel(args.output, index=False, sheet_name='annotation')

    n_sar = int(out_df['model_is_sarcastic'].sum())
    print(f'Wrote {args.output} ({len(out_df)} rows).')
    print(f'  model_user_content = llm_text[:800] + Flair/Upvotes/Comments (matches Sentiment Agent).')
    print(f'  Sample: model_is_sarcastic True={n_sar}, False={len(out_df) - n_sar}')


if __name__ == '__main__':
    main()
