"""
Build browser-readable cached run data for the SentimentEdge frontend.

Reads completed pipeline runs from outputs/runs/run_*/ and writes:
  web/public/runs/cache.json
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOTS = [ROOT / "outputs" / "runs", ROOT / "outputs" / "sample_runs"]
OUT_PATH = ROOT / "web" / "public" / "runs" / "cache.json"


def _safe_literal(value):
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    return value


def _records(df: pd.DataFrame):
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def _sentiment_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts()
    return {
        "bullish": int(counts.get("bullish", 0)),
        "bearish": int(counts.get("bearish", 0)),
        "neutral": int(counts.get("neutral", 0)),
    }


def build_run(run_dir: Path) -> dict:
    metadata = json.loads((run_dir / "run_metadata.json").read_text())

    ticker_summary = pd.read_csv(run_dir / "ticker_summary.csv", index_col=0)
    ticker_summary.index.name = "ticker"
    tickers = ticker_summary.reset_index()

    sentiment = pd.read_csv(run_dir / "sentiment_results.csv", index_col=0)
    for col in ("tickers", "emotions"):
        if col in sentiment.columns:
            sentiment[col] = sentiment[col].apply(_safe_literal)
    sentiment["date"] = pd.to_datetime(sentiment["date"], errors="coerce")

    rumours_path = run_dir / "rumour_alerts.csv"
    rumours = pd.read_csv(rumours_path, index_col=0) if rumours_path.exists() else pd.DataFrame()
    if not rumours.empty:
        rumours["date"] = pd.to_datetime(rumours["date"], errors="coerce")

    daily_rows = []
    for (ticker, day), group in (
        sentiment[sentiment["primary_ticker"] != "UNKNOWN"]
        .assign(day=sentiment["date"].dt.strftime("%Y-%m-%d"))
        .groupby(["primary_ticker", "day"])
    ):
        counts = _sentiment_counts(group["sentiment"])
        total = len(group)
        daily_rows.append(
            {
                "ticker": ticker,
                "day": day,
                "post_count": total,
                "bullish": counts["bullish"],
                "bearish": counts["bearish"],
                "neutral": counts["neutral"],
            }
        )

    emotion_rows = []
    for ticker, group in sentiment[sentiment["primary_ticker"] != "UNKNOWN"].groupby("primary_ticker"):
        emotions: list[str] = []
        for value in group.get("emotions", []):
            if isinstance(value, list):
                emotions.extend(str(item) for item in value)
        counts = pd.Series(emotions).value_counts() if emotions else pd.Series(dtype=int)
        for emotion, count in counts.head(10).items():
            emotion_rows.append({"ticker": ticker, "emotion": emotion, "count": int(count)})

    post_type_rows = []
    for ticker, group in sentiment[sentiment["primary_ticker"] != "UNKNOWN"].groupby("primary_ticker"):
        counts = group["post_type"].value_counts()
        for post_type, count in counts.head(8).items():
            post_type_rows.append({"ticker": ticker, "post_type": post_type, "count": int(count)})

    top_posts = (
        sentiment[sentiment["primary_ticker"] != "UNKNOWN"]
        .sort_values("engagement_score", ascending=False)
        .groupby("primary_ticker")
        .head(6)
    )

    return {
        "id": run_dir.name,
        "run_dir": str(run_dir.relative_to(ROOT)),
        "metadata": metadata,
        "source_files": [
            "sentiment_results.csv",
            "ticker_summary.csv",
            "rumour_alerts.csv" if rumours_path.exists() else None,
            "trace.txt",
        ],
        "tickers": _records(tickers),
        "posts": _records(top_posts),
        "rumours": _records(rumours),
        "daily": daily_rows,
        "emotions": emotion_rows,
        "post_types": post_type_rows,
    }


def main() -> None:
    runs = []
    seen = set()
    for runs_root in RUNS_ROOTS:
        for run_dir in sorted(runs_root.glob("run_*"), reverse=True):
            required = ["run_metadata.json", "ticker_summary.csv", "sentiment_results.csv"]
            if run_dir in seen:
                continue
            if run_dir.is_dir() and all((run_dir / name).exists() for name in required):
                runs.append(build_run(run_dir))
                seen.add(run_dir)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"runs": runs}, indent=2, default=str) + "\n")
    print(f"Cached {len(runs)} run(s) -> {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
