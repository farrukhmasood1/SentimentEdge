"""
SentimentEdge — Run Logger
Creates a timestamped run folder under outputs/runs/ for every pipeline
execution. Tees all stdout to trace.txt while still printing to terminal.
Saves run_metadata.json at the end of each run.
"""

import os
import sys
import json
from datetime import datetime


def create_run_dir():
    """
    Creates a timestamped folder under outputs/runs/.
    Returns the absolute path to the new run directory.

    Example: outputs/runs/run_20260411_143022/
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir   = os.path.join('outputs', 'runs', f'run_{timestamp}')
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


class TeeLogger:
    """
    Redirects sys.stdout so all print() calls write to both the terminal
    and a trace.txt file inside the run directory simultaneously.

    Usage:
        run_dir = create_run_dir()
        logger  = TeeLogger(run_dir)
        sys.stdout = logger
        # ... run pipeline ...
        logger.close()   # restores sys.stdout, closes file
    """

    def __init__(self, run_dir):
        self._terminal = sys.stdout
        self.log_path  = os.path.join(run_dir, 'trace.txt')
        self._logfile  = open(self.log_path, 'w', encoding='utf-8')

    def write(self, message):
        self._terminal.write(message)
        self._logfile.write(message)

    def flush(self):
        self._terminal.flush()
        self._logfile.flush()

    def close(self):
        sys.stdout = self._terminal
        self._logfile.close()


def save_metadata(metadata: dict, run_dir: str):
    """
    Writes run_metadata.json to the run directory.

    Expected metadata keys (all optional — save whatever is available):
        run_timestamp, run_dir, config, posts_loaded, posts_after_filter,
        posts_analyzed, errors, avg_confidence, sarcastic_count,
        rumour_count, tickers_found, rumours_flagged,
        pipeline_duration_seconds
    """
    path = os.path.join(run_dir, 'run_metadata.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f'\n  run_metadata.json saved → {path}')
