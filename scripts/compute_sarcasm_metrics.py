#!/usr/bin/env python3
"""
Compute inter-annotator agreement and model vs human metrics from a filled
sarcasm annotation workbook (Excel).

Expected columns (names may vary):
  - Two columns matching /person_\\d+_label/i (e.g. person_1_label - Moid)
  - Optional: adjudicated (S / N / U) for disagreements
  - model_is_sarcastic (bool)

Metrics:
  - Krippendorff's alpha (nominal) on the two human label columns
  - Pairwise agreement rate
  - Counts: uncertain (U) per rater, disagreements, rows usable for P/R/F1
  - Precision, recall, F1 for model_is_sarcastic vs gold (S=True, N=False)
    on rows with gold in {S, N} only (U excluded)

Gold label rule:
  1) If adjudicated is a non-empty S/N/U, use it.
  2) Else if person_1 == person_2, use that label.
  3) Else unresolved (excluded from P/R/F1; counted separately).

Usage (from SentimentEdge directory):
  python scripts/compute_sarcasm_metrics.py \\
    --input eval/sarcasm_annotation_sample_human_output.xlsx \\
    --output eval/sarcasm_metrics.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import krippendorff as kd
except ImportError:
    print('Install krippendorff: pip install krippendorff', file=sys.stderr)
    raise

try:
    from sklearn.metrics import precision_recall_fscore_support
except ImportError:
    print('Install scikit-learn: pip install scikit-learn', file=sys.stderr)
    raise

LABEL_RE = re.compile(r'person_\d+_label', re.I)


def _find_person_columns(columns: list[str]) -> tuple[str, str]:
    hits = [c for c in columns if LABEL_RE.search(c)]
    if len(hits) < 2:
        raise SystemExit(
            f'Need at least two columns matching person_*_label; found: {hits}'
        )
    hits = sorted(hits)
    return hits[0], hits[1]


def _norm_label(v) -> str | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip().upper()
    if s in ('', 'NAN', 'NONE'):
        return None
    if s in ('S', 'N', 'U'):
        return s
    # allow Y/N legacy
    if s in ('Y',):
        return 'S'
    if s in ('NO',):
        return 'N'
    return s


def _norm_adjudicated(v) -> str | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip().upper()
    if s in ('', 'NAN', 'NONE'):
        return None
    if s in ('S', 'N', 'U'):
        return s
    return None


def _gold_row(p1: str | None, p2: str | None, adj: str | None) -> tuple[str | None, str]:
    if adj is not None:
        return adj, 'adjudicated'
    if p1 is None or p2 is None:
        return None, 'missing_label'
    if p1 == p2:
        return p1, 'consensus'
    return None, 'unresolved_disagreement'


def main() -> None:
    parser = argparse.ArgumentParser(description='Sarcasm annotation metrics')
    parser.add_argument('--input', type=Path, required=True, help='Filled .xlsx path')
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Optional JSON path for metrics (stdout always prints summary)',
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f'✗ File not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(args.input)
    c1, c2 = _find_person_columns(list(df.columns))

    adj_col = 'adjudicated' if 'adjudicated' in df.columns else None
    if 'model_is_sarcastic' not in df.columns:
        print('✗ Column model_is_sarcastic is required', file=sys.stderr)
        sys.exit(1)

    p1 = df[c1].map(_norm_label)
    p2 = df[c2].map(_norm_label)
    adj = df[adj_col].map(_norm_adjudicated) if adj_col else pd.Series([None] * len(df))

    gold: list[str | None] = []
    gold_src: list[str] = []
    for a, b, d in zip(p1, p2, adj):
        g, src = _gold_row(a, b, d)
        gold.append(g)
        gold_src.append(src)

    df['_gold'] = gold
    df['_gold_src'] = gold_src

    # Krippendorff nominal alpha: float matrix with S=0, N=1, U=2 (NaN = missing)
    _NOM = {'S': 0.0, 'N': 1.0, 'U': 2.0}

    def _encode_nominal(x) -> float:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        return _NOM[x]

    mat = np.array(
        [[_encode_nominal(a), _encode_nominal(b)] for a, b in zip(p1.tolist(), p2.tolist())],
        dtype=float,
    )
    alpha = kd.alpha(reliability_data=mat, level_of_measurement='nominal')

    both = p1.notna() & p2.notna()
    agree_mask = both & (p1 == p2)
    disagree_mask = both & (p1 != p2)

    n = len(df)
    n_both = int(both.sum())
    n_agree = int(agree_mask.sum())
    n_disagree = int(disagree_mask.sum())

    gold_series = pd.Series(gold)
    n_gold_s = int((gold_series == 'S').sum())
    n_gold_n = int((gold_series == 'N').sum())
    n_gold_u = int((gold_series == 'U').sum())
    n_gold_missing = int(gold_series.isna().sum())

    pr_mask = gold_series.isin(['S', 'N'])
    y_true = gold_series[pr_mask].map({'S': True, 'N': False}).astype(bool)
    y_pred = df.loc[pr_mask, 'model_is_sarcastic'].astype(bool)

    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average='binary', pos_label=True, zero_division=0
    )

    out = {
        'input_file': str(args.input),
        'person_1_column': c1,
        'person_2_column': c2,
        'n_rows': n,
        'krippendorff_alpha_nominal': float(alpha),
        'pairwise_agreement_rate': round(n_agree / n_both, 4) if n_both else None,
        'n_both_labeled': n_both,
        'n_pairwise_agree': n_agree,
        'n_pairwise_disagree': n_disagree,
        'gold_counts': {
            'S': n_gold_s,
            'N': n_gold_n,
            'U': n_gold_u,
            'missing_or_unresolved': n_gold_missing,
        },
        'gold_source_counts': df['_gold_src'].value_counts().to_dict(),
        'model_vs_gold_binary': {
            'n_used_for_pr_f1': int(pr_mask.sum()),
            'precision_sarcastic_positive': float(prec),
            'recall_sarcastic_positive': float(rec),
            'f1_sarcastic_positive': float(f1),
            'note': 'Gold S=True, N=False; rows with gold U or unresolved disagreement excluded.',
        },
    }

    print(json.dumps(out, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2)
        print(f'\nWrote {args.output}')


if __name__ == '__main__':
    main()
