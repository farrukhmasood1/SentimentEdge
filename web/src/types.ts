export type Sentiment = "bullish" | "bearish" | "neutral";
export type ReviewStatus = "pending" | "approved" | "rejected" | "escalated";

export interface RunMetadata {
  run_timestamp?: string;
  run_dir?: string;
  pipeline_duration_seconds?: number;
  n_posts_raw?: number;
  n_comments_raw?: number;
  n_filtered?: number;
  n_analyzed?: number;
  errors?: number;
  tickers_found?: number;
  rumours_flagged?: number;
  avg_confidence?: number;
  sarcastic_count?: number;
  config?: Record<string, number | string | boolean>;
}

export interface TickerSummary {
  ticker: string;
  post_count: number;
  bullish_pct: number;
  bearish_pct: number;
  neutral_pct: number;
  avg_confidence: number;
  avg_relevance?: number;
  sarcastic_count?: number;
  avg_engagement?: number;
  low_confidence?: boolean;
  low_sample?: boolean;
}

export interface SentimentPost {
  post_id?: string;
  title: string;
  permalink?: string;
  score?: number;
  num_comments?: number;
  date?: string;
  flair?: string;
  engagement_score?: number;
  sentiment: Sentiment | string;
  confidence?: number;
  tickers?: string[] | string;
  primary_ticker: string;
  emotions?: string[] | string;
  post_type?: string;
  is_sarcastic?: boolean;
  market_relevance?: number;
  key_insight?: string;
  is_rumour?: boolean;
  rumour_type?: string;
  rumour_confidence?: number;
  rumour_summary?: string;
}

export interface RumorItem extends SentimentPost {
  rumour_type: string;
  rumour_confidence: number;
  rumour_summary: string;
}

export interface DailyPoint {
  ticker: string;
  day: string;
  post_count: number;
  bullish: number;
  bearish: number;
  neutral: number;
}

export interface EmotionPoint {
  ticker: string;
  emotion: string;
  count: number;
}

export interface PostTypePoint {
  ticker: string;
  post_type: string;
  count: number;
}

export interface RunDataset {
  id: string;
  run_dir?: string;
  metadata: RunMetadata;
  source_files: Array<string | null>;
  tickers: TickerSummary[];
  posts: SentimentPost[];
  rumours: RumorItem[];
  daily: DailyPoint[];
  emotions: EmotionPoint[];
  post_types: PostTypePoint[];
  uploaded?: boolean;
}

export interface RunCache {
  runs: RunDataset[];
}
