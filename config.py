"""
SentimentEdge — Configuration
All tunable parameters in one place. Change values here only.
"""

import os

# ── File paths ────────────────────────────────────────────────────────────────
POSTS_FILE    = 'data/r_wallstreetbets_posts.jsonl'
COMMENTS_FILE = 'data/r_wallstreetbets_comments.jsonl'

# ── Anthropic API ─────────────────────────────────────────────────────────────
API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'YOUR_ANTHROPIC_API_KEY_HERE')

# ── Pipeline settings ─────────────────────────────────────────────────────────
BATCH_SIZE     = 500   # posts sent to Sentiment Agent per run (1559 total in dataset)
TOP_N_COMMENTS = 5     # top comments bundled per post
MIN_POST_SCORE = 10    # minimum upvote score to pass Filter Agent

# ── Aggregator thresholds ─────────────────────────────────────────────────────
RUMOUR_THRESHOLD     = 0.7   # minimum rumour_confidence to surface an alert
# High-stakes rumours: held for human review (see README — governance). Not shown as released alerts.
RUMOUR_HUMAN_REVIEW_MIN_CONF = 0.8
RUMOUR_HUMAN_REVIEW_TYPES   = ('acquisition_rumour',)  # must match sentiment_agent JSON schema
LOW_CONF_THRESHOLD   = 0.6   # below this avg_confidence triggers a warning
LOW_SAMPLE_THRESHOLD = 5     # below this post_count triggers a low-sample warning

# ── Trend alert settings ──────────────────────────────────────────────────────
SHIFT_THRESHOLD   = 15   # percentage point swing to flag as significant
MIN_POSTS_PER_DAY = 3    # minimum daily posts to include ticker in trend report (TBD)

# ── Model ─────────────────────────────────────────────────────────────────────
CLAUDE_MODEL  = 'claude-sonnet-4-20250514'
MAX_TOKENS    = 400
RATE_LIMIT_SLEEP = 0.3   # seconds between Claude API calls
