import Papa from "papaparse";
import type {
  DailyPoint,
  EmotionPoint,
  PostTypePoint,
  RunCache,
  RunDataset,
  RunMetadata,
  SentimentPost,
  TickerSummary,
} from "./types";

const numberFields = new Set([
  "post_count",
  "bullish_pct",
  "bearish_pct",
  "neutral_pct",
  "avg_confidence",
  "avg_relevance",
  "sarcastic_count",
  "avg_engagement",
  "score",
  "num_comments",
  "engagement_score",
  "confidence",
  "market_relevance",
  "rumour_confidence",
]);

export async function loadCachedRuns(): Promise<RunDataset[]> {
  const response = await fetch("/runs/cache.json", { cache: "no-cache" });
  if (!response.ok) {
    throw new Error("No cached runs found. Run npm run cache-runs from web/.");
  }
  const cache = (await response.json()) as RunCache;
  return cache.runs.map(normalizeRun);
}

export async function buildRunFromFiles(files: FileList): Promise<RunDataset> {
  const byName = new Map<string, File>();
  Array.from(files).forEach((file) => byName.set(file.name, file));

  const metadataFile = byName.get("run_metadata.json");
  const tickerFile = byName.get("ticker_summary.csv");
  const sentimentFile = byName.get("sentiment_results.csv");
  const rumourFile = byName.get("rumour_alerts.csv");

  if (!metadataFile || !tickerFile || !sentimentFile) {
    throw new Error(
      "Upload at least run_metadata.json, ticker_summary.csv, and sentiment_results.csv."
    );
  }

  const metadata = JSON.parse(await metadataFile.text()) as RunMetadata;
  const tickers = parseTickerCsv(await tickerFile.text());
  const sentiment = parseSentimentCsv(await sentimentFile.text());
  const rumours = rumourFile ? parseSentimentCsv(await rumourFile.text()) : [];

  const run: RunDataset = {
    id: metadata.run_dir?.split(/[\\/]/).pop() || `uploaded_run_${new Date().toISOString()}`,
    run_dir: metadata.run_dir,
    metadata,
    source_files: Array.from(byName.keys()),
    tickers,
    posts: topPostsByTicker(sentiment),
    rumours: rumours as RunDataset["rumours"],
    daily: buildDaily(sentiment),
    emotions: buildEmotions(sentiment),
    post_types: buildPostTypes(sentiment),
    uploaded: true,
  };

  return normalizeRun(run);
}

export function normalizeRun(run: RunDataset): RunDataset {
  return {
    ...run,
    tickers: run.tickers.map((ticker) => ({
      ...ticker,
      ticker: String(ticker.ticker || "UNKNOWN").toUpperCase(),
      post_count: toNumber(ticker.post_count),
      bullish_pct: toNumber(ticker.bullish_pct),
      bearish_pct: toNumber(ticker.bearish_pct),
      neutral_pct: toNumber(ticker.neutral_pct),
      avg_confidence: toNumber(ticker.avg_confidence),
      avg_relevance: optionalNumber(ticker.avg_relevance),
      sarcastic_count: optionalNumber(ticker.sarcastic_count),
      avg_engagement: optionalNumber(ticker.avg_engagement),
      low_confidence: toBool(ticker.low_confidence),
      low_sample: toBool(ticker.low_sample),
    })),
    posts: run.posts.map(normalizePost),
    rumours: run.rumours.map((post) => normalizePost(post) as RunDataset["rumours"][number]),
    daily: run.daily.map((point) => ({
      ...point,
      ticker: String(point.ticker || "UNKNOWN").toUpperCase(),
      post_count: toNumber(point.post_count),
      bullish: toNumber(point.bullish),
      bearish: toNumber(point.bearish),
      neutral: toNumber(point.neutral),
    })),
  };
}

function parseTickerCsv(text: string): TickerSummary[] {
  const rows = parseCsv(text);
  return rows.map((row) => ({
    ticker: String(row.primary_ticker || row.ticker || row[""] || row["Unnamed: 0"] || "UNKNOWN"),
    post_count: toNumber(row.post_count),
    bullish_pct: toNumber(row.bullish_pct),
    bearish_pct: toNumber(row.bearish_pct),
    neutral_pct: toNumber(row.neutral_pct),
    avg_confidence: toNumber(row.avg_confidence),
    avg_relevance: optionalNumber(row.avg_relevance),
    sarcastic_count: optionalNumber(row.sarcastic_count),
    avg_engagement: optionalNumber(row.avg_engagement),
    low_confidence: toBool(row.low_confidence),
    low_sample: toBool(row.low_sample),
  }));
}

function parseSentimentCsv(text: string): SentimentPost[] {
  return parseCsv(text).map((row) =>
    normalizePost({
      post_id: String(row.post_id || ""),
      title: String(row.title || "Untitled post"),
      permalink: String(row.permalink || ""),
      score: optionalNumber(row.score),
      num_comments: optionalNumber(row.num_comments),
      date: String(row.date || ""),
      flair: String(row.flair || ""),
      engagement_score: optionalNumber(row.engagement_score),
      sentiment: String(row.sentiment || "neutral"),
      confidence: optionalNumber(row.confidence),
      tickers: parseArrayish(row.tickers),
      primary_ticker: String(row.primary_ticker || "UNKNOWN"),
      emotions: parseArrayish(row.emotions),
      post_type: String(row.post_type || "other"),
      is_sarcastic: toBool(row.is_sarcastic),
      market_relevance: optionalNumber(row.market_relevance),
      key_insight: String(row.key_insight || ""),
      is_rumour: toBool(row.is_rumour),
      rumour_type: String(row.rumour_type || "none"),
      rumour_confidence: optionalNumber(row.rumour_confidence),
      rumour_summary: String(row.rumour_summary || "none"),
    })
  );
}

function parseCsv(text: string): Array<Record<string, unknown>> {
  const result = Papa.parse<Record<string, unknown>>(text, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
  });
  return result.data.map((row) => {
    const cleaned: Record<string, unknown> = {};
    Object.entries(row).forEach(([key, value]) => {
      const cleanKey = key.trim();
      cleaned[cleanKey] = numberFields.has(cleanKey) ? optionalNumber(value) : value;
    });
    return cleaned;
  });
}

function normalizePost(post: SentimentPost): SentimentPost {
  return {
    ...post,
    title: String(post.title || "Untitled post"),
    primary_ticker: String(post.primary_ticker || "UNKNOWN").toUpperCase(),
    score: optionalNumber(post.score),
    num_comments: optionalNumber(post.num_comments),
    engagement_score: optionalNumber(post.engagement_score),
    confidence: optionalNumber(post.confidence),
    market_relevance: optionalNumber(post.market_relevance),
    rumour_confidence: optionalNumber(post.rumour_confidence),
    is_sarcastic: toBool(post.is_sarcastic),
    is_rumour: toBool(post.is_rumour),
    emotions: parseArrayish(post.emotions),
    tickers: parseArrayish(post.tickers),
  };
}

function topPostsByTicker(posts: SentimentPost[]): SentimentPost[] {
  const sorted = [...posts].sort(
    (a, b) => (b.engagement_score || 0) - (a.engagement_score || 0)
  );
  const counts = new Map<string, number>();
  return sorted.filter((post) => {
    if (post.primary_ticker === "UNKNOWN") return false;
    const count = counts.get(post.primary_ticker) || 0;
    counts.set(post.primary_ticker, count + 1);
    return count < 6;
  });
}

function buildDaily(posts: SentimentPost[]): DailyPoint[] {
  const map = new Map<string, DailyPoint>();
  posts.forEach((post) => {
    if (!post.date || post.primary_ticker === "UNKNOWN") return;
    const day = post.date.slice(0, 10);
    const key = `${post.primary_ticker}:${day}`;
    const point =
      map.get(key) ||
      ({ ticker: post.primary_ticker, day, post_count: 0, bullish: 0, bearish: 0, neutral: 0 } as DailyPoint);
    point.post_count += 1;
    if (post.sentiment === "bullish") point.bullish += 1;
    else if (post.sentiment === "bearish") point.bearish += 1;
    else point.neutral += 1;
    map.set(key, point);
  });
  return Array.from(map.values()).sort((a, b) => a.day.localeCompare(b.day));
}

function buildEmotions(posts: SentimentPost[]): EmotionPoint[] {
  const counts = new Map<string, number>();
  posts.forEach((post) => {
    const emotions = parseArrayish(post.emotions);
    emotions.forEach((emotion) => {
      const key = `${post.primary_ticker}:${emotion}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
  });
  return Array.from(counts.entries()).map(([key, count]) => {
    const [ticker, emotion] = key.split(":");
    return { ticker, emotion, count };
  });
}

function buildPostTypes(posts: SentimentPost[]): PostTypePoint[] {
  const counts = new Map<string, number>();
  posts.forEach((post) => {
    if (post.primary_ticker === "UNKNOWN") return;
    const key = `${post.primary_ticker}:${post.post_type || "other"}`;
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return Array.from(counts.entries()).map(([key, count]) => {
    const [ticker, post_type] = key.split(":");
    return { ticker, post_type, count };
  });
}

function parseArrayish(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value !== "string" || value.trim() === "") return [];
  try {
    const jsonish = value.replaceAll("'", '"');
    const parsed = JSON.parse(jsonish);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return value
      .replace(/^\[/, "")
      .replace(/\]$/, "")
      .split(",")
      .map((item) => item.replaceAll('"', "").replaceAll("'", "").trim())
      .filter(Boolean);
  }
}

function optionalNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === "" || value === "—") return undefined;
  return toNumber(value);
}

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toBool(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return value.toLowerCase() === "true";
  return Boolean(value);
}
