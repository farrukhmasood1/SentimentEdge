"""
SentimentEdge — Agent 3: Sentiment Agent
Core LLM reasoning layer. Sends each post to Claude and extracts 13
structured fields: sentiment, confidence, tickers, emotions, sarcasm,
market relevance, key insight, and rumour detection signals.

Prompt caching is enabled on the static system prompt so all 500 calls
in a batch share a single cached prefix — reducing input token costs by
~90% after the first call.

Inputs:  df_filtered (from Filter Agent), api_key, batch_size
Outputs: df_llm — original post fields + 13 LLM fields (22 columns total)
"""

import time
import json
import pandas as pd
import anthropic

from config import (
    CLAUDE_MODEL, MAX_TOKENS, RATE_LIMIT_SLEEP, BATCH_SIZE,
    RUMOUR_THRESHOLD
)

# ── Static system prompt (cached across all calls in a batch) ─────────────────
_SYSTEM_PROMPT = """You are a financial sentiment analyst specialising in Reddit finance communities.
Analyse the Reddit post provided by the user and return ONLY a valid JSON object — no markdown, no explanation, no extra text.

Guidelines:
- Detect sarcasm carefully. r/wallstreetbets uses heavy irony and meme language.
- Prefer $TICKER format for ticker extraction. Require financial context for ambiguous short words (e.g. AI, OPEN, FAST).
- For rumours: only flag if there are specific claims about a named corporate event, not general speculation or jokes.
- Set confidence low (< 0.5) for meme posts, deleted bodies, or posts with no clear market content.

Return this exact JSON structure with no other text:
{
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0.0 to 1.0,
    "tickers": ["list of stock tickers mentioned"],
    "primary_ticker": "most important ticker or UNKNOWN",
    "emotions": ["list from: greed, fear, hope, panic, euphoria, frustration, humor, sarcasm"],
    "post_type": "DD" | "YOLO" | "loss" | "gain" | "news" | "question" | "meme" | "other",
    "is_sarcastic": true | false,
    "market_relevance": 0.0 to 1.0,
    "key_insight": "one sentence summary of the post market relevance",
    "is_rumour": true | false,
    "rumour_type": "merger_speculation" | "acquisition_rumour" | "partnership_chatter" | "leadership_change" | "regulatory_decision" | "none",
    "rumour_confidence": 0.0 to 1.0,
    "rumour_summary": "one sentence description of the rumour or none"
}"""

# ── Neutral defaults returned on parse failure ────────────────────────────────
_NEUTRAL_DEFAULTS = {
    'sentiment':         'neutral',
    'confidence':        0.0,
    'tickers':           [],
    'primary_ticker':    'UNKNOWN',
    'emotions':          [],
    'post_type':         'other',
    'is_sarcastic':      False,
    'market_relevance':  0.0,
    'key_insight':       'Failed to parse',
    'is_rumour':         False,
    'rumour_type':       'none',
    'rumour_confidence': 0.0,
    'rumour_summary':    'none',
}


def analyze_post(row, client):
    """
    Sends a single post to Claude using a cached system prompt.
    Returns a 13-field dict or None on an unrecoverable API error.

    Error handling:
      - JSONDecodeError  → return neutral defaults (confidence 0.0), pipeline continues
      - Other exception  → return None, caller increments error counter
    """
    user_content = (
        f"{row['llm_text'][:800]}\n\n"
        f"Flair: {row['flair']}\n"
        f"Upvotes: {int(row['score'])}\n"
        f"Comments: {int(row['num_comments'])}"
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    'type': 'text',
                    'text': _SYSTEM_PROMPT,
                    'cache_control': {'type': 'ephemeral'},
                }
            ],
            messages=[{'role': 'user', 'content': user_content}],
        )
        raw = response.content[0].text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        return dict(_NEUTRAL_DEFAULTS)

    except Exception as e:
        print(f'  ⚠  API error on post {row.name}: {e}')
        return None


def run_sentiment_agent(df_filtered, api_key, batch_size=BATCH_SIZE):
    """
    Selects top posts by engagement score and sends each to Claude.

    Prompt caching reduces cost: the static system prompt is cached after
    the first call and reused for all subsequent calls in the batch.
    Estimated saving: ~90% on input tokens after call #1.

    Inputs:
        df_filtered — filtered posts from Filter Agent
        api_key     — Anthropic API key
        batch_size  — max posts to process (default from config)

    Outputs:
        df_llm — DataFrame with 22 columns:
          [post fields] post_id, title, permalink, score, num_comments,
                        date, flair, engagement_score, has_comments
          [LLM fields]  sentiment, confidence, tickers, primary_ticker,
                        emotions, post_type, is_sarcastic, market_relevance,
                        key_insight, is_rumour, rumour_type,
                        rumour_confidence, rumour_summary
    """
    print('\n' + '=' * 55)
    print('AGENT 3 — SENTIMENT AGENT')
    print('=' * 55)

    if len(df_filtered) == 0:
        print('  ⚠  df_filtered is empty — skipping Sentiment Agent.')
        return pd.DataFrame()

    client    = anthropic.Anthropic(api_key=api_key)
    df_subset = df_filtered.nlargest(batch_size, 'engagement_score').copy()
    df_subset = df_subset.reset_index(drop=True)

    print(f'  Posts selected:   {len(df_subset)}')
    print(f'  Engagement range: {df_subset["engagement_score"].min():.0f}'
          f' → {df_subset["engagement_score"].max():.0f}')
    print(f'  Prompt caching:   enabled (system prompt cached after call #1)')
    print(f'  Estimated cost:   ~${batch_size * 0.0015:.2f} (uncached) '
          f'→ ~${batch_size * 0.00015:.2f} (cached after first call)')
    print(f'  Estimated time:   ~{batch_size * 4 // 60} min\n')

    results = []
    errors  = 0
    start   = time.time()

    for i, row in df_subset.iterrows():
        if i > 0 and i % 10 == 0:
            elapsed  = time.time() - start
            per_post = elapsed / i
            eta      = per_post * (len(df_subset) - i)
            print(f'  Progress: {i}/{len(df_subset)} | '
                  f'Elapsed: {elapsed:.0f}s | '
                  f'ETA: {eta:.0f}s | '
                  f'Errors: {errors}')

        result = analyze_post(row, client)

        if result is not None:
            results.append({
                # Post fields
                'post_id':          row['post_id'],
                'title':            row['title'],
                'permalink':        row['permalink'],
                'score':            row['score'],
                'num_comments':     row['num_comments'],
                'date':             row['date'],
                'flair':            row['flair'],
                'engagement_score': row['engagement_score'],
                'has_comments':     row['top_comments'] != '',
                # LLM fields
                'sentiment':         result.get('sentiment',         'neutral'),
                'confidence':        result.get('confidence',        0.0),
                'tickers':           result.get('tickers',           []),
                'primary_ticker':    result.get('primary_ticker',    'UNKNOWN'),
                'emotions':          result.get('emotions',          []),
                'post_type':         result.get('post_type',         'other'),
                'is_sarcastic':      result.get('is_sarcastic',      False),
                'market_relevance':  result.get('market_relevance',  0.0),
                'key_insight':       result.get('key_insight',       ''),
                'is_rumour':         result.get('is_rumour',         False),
                'rumour_type':       result.get('rumour_type',       'none'),
                'rumour_confidence': result.get('rumour_confidence', 0.0),
                'rumour_summary':    result.get('rumour_summary',    'none'),
            })
        else:
            errors += 1

        time.sleep(RATE_LIMIT_SLEEP)

    df_llm  = pd.DataFrame(results)
    elapsed = time.time() - start

    print(f'\n✓ Sentiment Agent complete')
    print(f'   Processed: {len(df_llm)}')
    print(f'   Errors:    {errors}')
    print(f'   Time:      {elapsed:.0f}s')

    if len(df_llm) > 0:
        print(f'\n   Sentiment breakdown:')
        print(df_llm['sentiment'].value_counts().to_string())
        print(f'\n   Avg confidence:  {df_llm["confidence"].mean():.2f}')
        print(f'   Sarcastic posts: {df_llm["is_sarcastic"].sum()}')
        print(f'   Rumour posts:    {df_llm["is_rumour"].sum()}')

    return df_llm
