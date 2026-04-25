# SentimentEdge — Screenshot Index

| # | File | What It Shows | Why It Matters | Report Section |
|---|---|---|---|---|
| 1 | 01_pipeline_run.png | Full pipeline run in terminal — all 5 agents printing in sequence | Proves end-to-end execution and shows agent coordination | Architecture & Implementation |
| 2 | 02_spy_ticker_report.png | SPY ticker report — sentiment bars, emotion breakdown, post type table, monthly timeline | Main output artifact; shows Report 1 in action | Evaluation Results |
| 3 | 03_trend_alerts.png | Trend Alerts report — daily sentiment shift table for qualifying tickers | Shows Report 2 and the shift detection logic | Evaluation Results |
| 4 | 04_ticker_comparison.png | SPY vs TSLA side-by-side comparison report | Shows Report 3 and signal quality table | Evaluation Results |
| 5 | 05_rumour_alerts.png | Rumour Alerts section within SPY report — 3 flagged posts with type, confidence, disclaimer | Shows two-track routing and governance layer | Failure Analysis & Governance |
| 6 | 06_replay_mode.png | Terminal showing replay completing in under 5 seconds without API key | Confirms TC-06 and reproducibility for graders | Evaluation Results |
| 7 | 07_failure_case.png | TC-08 — pipeline halted after filter gate when MIN_POST_SCORE=100000 | Shows graceful failure handling | Failure Analysis |
| 8 | 08_ticker_summary_csv.png | ticker_summary.csv open — 59 tickers with all aggregated columns | Shows the evaluation data layer and saved run artifacts | Evidence Package |

## How to capture all screenshots using replay mode (no API key needed)

```
python main.py --replay outputs/sample_runs/run_20260412_110302
```

Scroll through the terminal output and screenshot each report section.
For TC-08, temporarily set MIN_POST_SCORE=100000 in config.py and run python main.py.
