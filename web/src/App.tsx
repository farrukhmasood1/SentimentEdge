import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Circle,
  KeyRound,
  Play,
  RotateCcw,
  ShieldCheck,
  Upload,
  XCircle,
} from "lucide-react";
import { buildRunFromFiles, loadCachedRuns } from "./runData";
import type { ReviewStatus, RunDataset, SentimentPost, TickerSummary } from "./types";

const FALLBACK_TICKER = "SPY";
const FALLBACK_COMPARE = "TSLA";
const LOCAL_API = "http://127.0.0.1:8787";

interface LocalJob {
  running: boolean;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
  exitCode: number | null;
  output: string;
}

export default function App() {
  const [runs, setRuns] = useState<RunDataset[]>([]);
  const [activeRunId, setActiveRunId] = useState("");
  const [route, setRoute] = useState(window.location.pathname);
  const [focusTicker, setFocusTicker] = useState(FALLBACK_TICKER);
  const [compareTicker, setCompareTicker] = useState(FALLBACK_COMPARE);
  const [uploadStatus, setUploadStatus] = useState("");
  const [reviewStatus, setReviewStatus] = useState<Record<string, ReviewStatus>>({});
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [localApiMessage, setLocalApiMessage] = useState("Local API not checked yet.");
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [localJob, setLocalJob] = useState<LocalJob | null>(null);

  useEffect(() => {
    loadCachedRuns()
      .then((cachedRuns) => {
        setRuns(cachedRuns);
        setActiveRunId(cachedRuns[0]?.id || "");
      })
      .catch((error) => setUploadStatus(error.message));
  }, []);

  useEffect(() => {
    void refreshLocalStatus();
    const timer = window.setInterval(() => {
      void refreshLocalStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const onPopState = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const activeRun = runs.find((run) => run.id === activeRunId) || runs[0];
  const tickers = activeRun?.tickers || [];
  const selectedTicker = pickTicker(tickers, focusTicker) || tickers[0];
  const comparisonTicker =
    pickTicker(tickers, compareTicker) ||
    tickers.find((ticker) => ticker.ticker !== selectedTicker?.ticker) ||
    tickers[1];

  useEffect(() => {
    if (!activeRun) return;
    const initial: Record<string, ReviewStatus> = {};
    const defaultStatus: ReviewStatus = hasSplitGovernance(activeRun) ? "approved" : "pending";
    activeRun.rumours.forEach((rumour, index) => {
      initial[rumourKey(rumour, index)] = defaultStatus;
    });
    setReviewStatus(initial);
  }, [activeRun?.id]);

  function navigate(path: string) {
    window.history.pushState(null, "", path);
    setRoute(path);
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    try {
      const uploadedRun = await buildRunFromFiles(files);
      setRuns((current) => [uploadedRun, ...current.filter((run) => run.id !== uploadedRun.id)]);
      setActiveRunId(uploadedRun.id);
      setFocusTicker(pickTicker(uploadedRun.tickers, FALLBACK_TICKER)?.ticker || uploadedRun.tickers[0]?.ticker || "");
      setCompareTicker(
        pickTicker(uploadedRun.tickers, FALLBACK_COMPARE)?.ticker || uploadedRun.tickers[1]?.ticker || ""
      );
      setUploadStatus(`Loaded ${uploadedRun.id} from uploaded run files.`);
    } catch (error) {
      setUploadStatus(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  async function refreshLocalStatus() {
    try {
      const response = await fetch(`${LOCAL_API}/api/status`);
      if (!response.ok) throw new Error("Local API unavailable.");
      const data = (await response.json()) as { apiKeyConfigured: boolean; job: LocalJob };
      setApiKeyConfigured(data.apiKeyConfigured);
      setLocalJob(data.job);
      setLocalApiMessage(data.apiKeyConfigured ? "Local API connected. API key configured." : "Local API connected. API key not set.");
      if (data.job.status === "completed") {
        const cachedRuns = await loadCachedRuns();
        setRuns(cachedRuns);
        setActiveRunId(cachedRuns[0]?.id || "");
      }
    } catch {
      setLocalApiMessage("Local API is offline. Run npm run local-api in a second terminal.");
    }
  }

  async function saveApiKey() {
    try {
      const response = await fetch(`${LOCAL_API}/api/key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apiKey: apiKeyInput }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not save API key.");
      setApiKeyInput("");
      setApiKeyConfigured(true);
      setLocalApiMessage("API key saved to local .env. The key was not stored in the browser bundle.");
    } catch (error) {
      setLocalApiMessage(error instanceof Error ? error.message : "Could not save API key.");
    }
  }

  async function runAnalysis() {
    try {
      const response = await fetch(`${LOCAL_API}/api/run-analysis`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not start analysis.");
      setLocalJob(data.job);
      setLocalApiMessage("Pipeline started locally. This can take several minutes.");
    } catch (error) {
      setLocalApiMessage(error instanceof Error ? error.message : "Could not start analysis.");
    }
  }

  if (!activeRun) {
    return (
      <Shell route={route} navigate={navigate}>
        <main className="page-shell empty-state">
          <h1>SentimentEdge</h1>
          <p>No cached run is loaded yet.</p>
          <p className="muted">{uploadStatus || "Run npm run cache-runs inside web/ and refresh."}</p>
        </main>
      </Shell>
    );
  }

  const commonProps = {
    run: activeRun,
    runs,
    selectedTicker,
    comparisonTicker,
    focusTicker,
    compareTicker,
    uploadStatus,
    reviewStatus,
    apiKeyInput,
    apiKeyConfigured,
    localApiMessage,
    localJob,
    setActiveRunId,
    setFocusTicker,
    setCompareTicker,
    setReviewStatus,
    setApiKeyInput,
    saveApiKey,
    runAnalysis,
    handleUpload,
    navigate,
  };

  return (
    <Shell route={route} navigate={navigate}>
      {route.startsWith("/ticker") ? (
        <TickerView {...commonProps} />
      ) : route.startsWith("/review") ? (
        <ReviewQueue {...commonProps} />
      ) : (
        <Dashboard {...commonProps} />
      )}
    </Shell>
  );
}

function Shell({
  children,
  route,
  navigate,
}: {
  children: React.ReactNode;
  route: string;
  navigate: (path: string) => void;
}) {
  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => navigate("/")} type="button">
          <span className="mark">SE</span>
          <span>
            <strong>SentimentEdge</strong>
            <small>r/wallstreetbets · evidence pipeline</small>
          </span>
        </button>
        <nav>
          <button className={route === "/" ? "active" : ""} onClick={() => navigate("/")} type="button">
            Dashboard
          </button>
          <button
            className={route.startsWith("/ticker") ? "active" : ""}
            onClick={() => navigate("/ticker/spy")}
            type="button"
          >
            SPY · TSLA
          </button>
          <button
            className={route.startsWith("/review") ? "active" : ""}
            onClick={() => navigate("/review")}
            type="button"
          >
            Review Queue
          </button>
        </nav>
      </header>
      {children}
      <footer>
        <span>SentimentEdge · prototype for evaluation only</span>
        <span>Not investment advice. No live market data. Local seed data only.</span>
      </footer>
    </>
  );
}

interface ViewProps {
  run: RunDataset;
  runs: RunDataset[];
  selectedTicker?: TickerSummary;
  comparisonTicker?: TickerSummary;
  focusTicker: string;
  compareTicker: string;
  uploadStatus: string;
  reviewStatus: Record<string, ReviewStatus>;
  apiKeyInput: string;
  apiKeyConfigured: boolean;
  localApiMessage: string;
  localJob: LocalJob | null;
  setActiveRunId: (id: string) => void;
  setFocusTicker: (ticker: string) => void;
  setCompareTicker: (ticker: string) => void;
  setReviewStatus: React.Dispatch<React.SetStateAction<Record<string, ReviewStatus>>>;
  setApiKeyInput: (value: string) => void;
  saveApiKey: () => Promise<void>;
  runAnalysis: () => Promise<void>;
  handleUpload: (files: FileList | null) => void;
  navigate: (path: string) => void;
}

function Dashboard({
  run,
  runs,
  selectedTicker,
  comparisonTicker,
  focusTicker,
  compareTicker,
  uploadStatus,
  apiKeyInput,
  apiKeyConfigured,
  localApiMessage,
  localJob,
  setActiveRunId,
  setFocusTicker,
  setCompareTicker,
  setApiKeyInput,
  saveApiKey,
  runAnalysis,
  handleUpload,
  navigate,
}: ViewProps) {
  const topTickers = run.tickers.slice(0, 6);
  const topThree = run.tickers.slice(0, 3);

  return (
    <main>
      <section className="hero page-shell">
        <div>
          <p className="eyebrow green-dot">SentimentEdge · evidence pipeline</p>
          <h1>Decision-support for r/wallstreetbets sentiment, with the receipts.</h1>
          <p className="lede">
            A 5-agent sequential pipeline turns subreddit posts and comments into per-ticker sentiment,
            calibrated confidence, sarcasm flags, and human-in-the-loop governance for rumors.
          </p>
          <p className="mono subtle">
            Analyst workflow: load saved run → inspect ticker signals → review rumor alerts.
          </p>
        </div>
        <RunScope run={run} />
      </section>

      <section className="page-shell band">
        <SectionTitle title="Pipeline · 5 sequential agents" aside="Collector → Filter → Sentiment → Aggregator → Output" />
        <div className="pipeline">
          {[
            ["Collector", "Ingests r/wallstreetbets posts and comments.", `${fmt(run.metadata.n_posts_raw)} posts · ${fmt(run.metadata.n_comments_raw)} comments`],
            ["Filter", "Removes off-topic and low-quality content.", `${fmt(run.metadata.n_filtered)} posts retained for analysis`],
            ["Sentiment", "Per-post classified with confidence and sarcasm detection.", `${fmt(run.metadata.sarcastic_count)} sarcastic posts identified`],
            ["Aggregator", "Rolls up scores per ticker and flags rumor clusters.", `${fmt(run.metadata.tickers_found)} tickers · ${fmt(run.metadata.rumours_flagged)} rumors flagged`],
            ["Output", "Publishes ticker summaries and routes flagged rumors to Analyst Review.", "Human review before publication"],
          ].map(([title, body, stat], index) => (
            <article className="agent-card" key={title}>
              <span className="agent-index">{String(index + 1).padStart(2, "0")}</span>
              <h3>{title}</h3>
              <p>{body}</p>
              <small>{stat}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="page-shell">
        <SectionTitle title={`Run summary · ${runDate(run)}`} aside={`${runWindowLabel(run)} · local cache`} />
        <div className="stat-grid">
          <Stat label="Raw posts" value={fmt(run.metadata.n_posts_raw)} />
          <Stat label="Raw comments" value={fmt(run.metadata.n_comments_raw)} />
          <Stat label="Analyzed posts" value={fmt(run.metadata.n_analyzed)} hint={`${pct(run.metadata.n_analyzed, run.metadata.n_posts_raw)} of raw`} />
          <Stat label="Tickers found" value={fmt(run.metadata.tickers_found)} />
          <Stat label="Rumors flagged" value={fmt(run.metadata.rumours_flagged)} tone="amber" hint="≥ 0.70 confidence" />
          <Stat label="Avg confidence" value={fixed(run.metadata.avg_confidence)} hint="across analyzed posts" />
          <Stat label="Sarcastic posts" value={fmt(run.metadata.sarcastic_count)} hint={`${pct(run.metadata.sarcastic_count, run.metadata.n_analyzed)} of analyzed`} />
          <Stat label="Replay mode" value="ON" tone="green" hint="deterministic re-runs" />
        </div>
      </section>

      <section className="page-shell">
        <SectionTitle title="Analyst input" aside="saved run · direct browser workflow" />
        <div className="input-grid">
          <RunAnalysisPanel
            apiKeyInput={apiKeyInput}
            apiKeyConfigured={apiKeyConfigured}
            localApiMessage={localApiMessage}
            localJob={localJob}
            setApiKeyInput={setApiKeyInput}
            saveApiKey={saveApiKey}
            runAnalysis={runAnalysis}
          />
          <div className="control-panel">
            <div className="active-run-line">
              <span>Active saved run</span>
              <strong>{run.id}</strong>
            </div>
            <div className="controls-row">
              <label>
                <span>Saved run</span>
                <select value={run.id} onChange={(event) => setActiveRunId(event.target.value)}>
                  {runs.map((candidate) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Focus ticker</span>
                <select value={focusTicker} onChange={(event) => setFocusTicker(event.target.value)}>
                  {run.tickers.map((ticker) => (
                    <option key={ticker.ticker} value={ticker.ticker}>
                      {ticker.ticker}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Compare with</span>
                <select value={compareTicker} onChange={(event) => setCompareTicker(event.target.value)}>
                  {run.tickers.map((ticker) => (
                    <option key={ticker.ticker} value={ticker.ticker}>
                      {ticker.ticker}
                    </option>
                  ))}
                </select>
              </label>
              <button className="accent-button" onClick={() => navigate("/review")} type="button">
                Open Review queue
              </button>
            </div>
            <div className="file-tags">
              {run.source_files.filter(Boolean).map((file) => (
                <span key={file}>{file}</span>
              ))}
            </div>
            <p className="mono subtle">
              Frontend prototype uses local seed data from completed pipeline runs. Selectors update the
              browser UI and do not trigger live Reddit ingestion.
            </p>
          </div>
          <div className="upload-panel">
            <h3>Use your own completed run</h3>
            <p>Upload the files produced by `python main.py`: metadata, ticker summary, sentiment results, and optional rumor alerts.</p>
            <label className="upload-zone">
              <Upload size={18} />
              <span>Upload completed run files</span>
              <input
                type="file"
                multiple
                accept=".csv,.json,.txt"
                onChange={(event) => handleUpload(event.target.files)}
              />
            </label>
            {uploadStatus && <p className="status-line">{uploadStatus}</p>}
          </div>
        </div>
      </section>

      <section className="page-shell dashboard-grid">
        <article className="panel chart-panel wide">
          <SectionTitle title="Net sentiment per ticker" aside="bullish % − bearish %" />
          <NetSentimentChart tickers={topThree} />
        </article>
        <TrustPanel />
      </section>

      <section className="page-shell dashboard-grid">
        <article className="panel wide">
          <SectionTitle title="Ticker leaderboard" aside={`${topTickers.length} shown · ordered by post volume`} />
          <TickerTable tickers={topTickers} onTicker={(ticker) => {
            setFocusTicker(ticker);
            navigate(`/ticker/${ticker.toLowerCase()}`);
          }} />
        </article>
        <div className="side-stack">
          <RouteCard
            icon={<BarChart3 size={16} />}
            label="Detail view"
            title={`${selectedTicker?.ticker || "SPY"} · ${comparisonTicker?.ticker || "TSLA"} comparison`}
            body="Side-by-side sentiment mix, confidence, engagement, and classifier examples for the selected tickers."
            action="Open comparison"
            onClick={() => navigate("/ticker/spy")}
          />
          <RouteCard
            icon={<ShieldCheck size={16} />}
            label="Governance"
            title="Analyst Review queue"
            body="High-confidence rumors are split into released alerts and held review items when governance policy triggers."
            action="Open review queue"
            onClick={() => navigate("/review")}
            badge={`${fmt(heldRumorCount(run))} held · ${fmt(releasedRumorCount(run))} released`}
          />
        </div>
      </section>
    </main>
  );
}

function TickerView({ run, selectedTicker, comparisonTicker, reviewStatus, navigate }: ViewProps) {
  if (!selectedTicker) return null;
  const compare = comparisonTicker || selectedTicker;
  const posts = postsForTicker(run, selectedTicker.ticker).slice(0, 3);
  const daily = run.daily.filter((point) => point.ticker === selectedTicker.ticker);
  const expandedWindow = runDayCount(run) >= 28;
  const timeline = expandedWindow ? monthlyFromDaily(daily) : daily;
  const postTypes = run.post_types
    .filter((point) => point.ticker === selectedTicker.ticker)
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
  const linkedRumours = run.rumours.filter((rumour) => rumour.primary_ticker === selectedTicker.ticker);
  const defaultReviewStatus: ReviewStatus = hasSplitGovernance(run) ? "approved" : "pending";
  const pendingLinked = linkedRumours.filter(
    (rumour, index) => (reviewStatus[rumourKey(rumour, index)] || defaultReviewStatus) === "pending"
  ).length;
  const governanceCopy = hasSplitGovernance(run)
    ? `${linkedRumours.length} ${selectedTicker.ticker}-linked released alert${linkedRumours.length === 1 ? "" : "s"}`
    : `${pendingLinked} ${selectedTicker.ticker}-linked rumor pending`;

  return (
    <main>
      <section className="page-shell detail-header">
        <p className="eyebrow">Deep dive · {runDate(run)}</p>
        <div className="split">
          <div>
            <h1>{selectedTicker.ticker}</h1>
            <p className="lede small">
              {runWindowLabel(run)} read on {selectedTicker.ticker} from r/wallstreetbets. This is a decision-support
              surface from a saved run, not a live forecast.
            </p>
          </div>
          <div className="header-chips">
            <Chip tone="red">Net {netSentiment(selectedTicker).toFixed(1)} pp</Chip>
            <Chip>{fmt(selectedTicker.post_count)} posts · {runDayCount(run)} days</Chip>
            {selectedTicker.sarcastic_count ? (
              <Chip tone="amber">Sarcasm {pct(selectedTicker.sarcastic_count, selectedTicker.post_count)}</Chip>
            ) : null}
          </div>
        </div>
      </section>

      <section className="page-shell">
        <div className="selection-strip">
          <span>Run <strong>{run.id}</strong></span>
          <span>Focus <strong>{selectedTicker.ticker}</strong></span>
          <span>Compare <strong>{compare.ticker}</strong></span>
          <span className="amber-text">Governance status {governanceCopy}</span>
          <button onClick={() => navigate("/review")} type="button">Review queue →</button>
        </div>
      </section>

      {selectedTicker.sarcastic_count && selectedTicker.sarcastic_count / selectedTicker.post_count > 0.1 ? (
        <section className="page-shell">
          <div className="warning-banner">
            <AlertTriangle size={16} />
            <strong>Sarcasm warning</strong>
            <span>High sarcasm rate ({pct(selectedTicker.sarcastic_count, selectedTicker.post_count)}) — scores adjusted by Claude.</span>
          </div>
        </section>
      ) : null}

      <section className="page-shell two-col">
        <article className="panel summary-panel">
          <SectionTitle title={`${selectedTicker.ticker} · sentiment summary`} aside={runWindowLabel(run)} />
          <div className="metric-row">
            <Stat label="Posts" value={fmt(selectedTicker.post_count)} hint="this run" />
            <Stat label="Avg confidence" value={fixed(selectedTicker.avg_confidence)} hint="model calibration" />
            <Stat label="Avg relevance" value={fixed(selectedTicker.avg_relevance)} hint="filter score" />
            <Stat
              label="Sarcastic posts"
              value={`${fmt(selectedTicker.sarcastic_count)} / ${fmt(selectedTicker.post_count)}`}
              tone="amber"
              hint={`${pct(selectedTicker.sarcastic_count, selectedTicker.post_count)} rate`}
            />
          </div>
          <SentimentMix ticker={selectedTicker} />
        </article>
        <article className="panel center-panel">
          <SectionTitle title="Mix · donut" aside="signal quality at a glance" />
          <Donut ticker={selectedTicker} />
        </article>
      </section>

      <section className="page-shell two-col">
        <article className="panel">
          <SectionTitle title="Post types" aside={`what kind of posts drive ${selectedTicker.ticker}`} />
          <BarList rows={postTypes.map((item) => [item.post_type, item.count])} total={selectedTicker.post_count} />
        </article>
        <article className="panel">
          <SectionTitle
            title={expandedWindow ? "Monthly sentiment timeline" : "Daily sentiment timeline"}
            aside={`${runWindowLabel(run)} · do not extrapolate`}
          />
          <StackedTimelineChart points={timeline} />
        </article>
      </section>

      <section className="page-shell">
        <SectionTitle title={`Top insights · ${selectedTicker.ticker}`} aside={`${posts.length} shown`} />
        <div className="insight-grid">
          {posts.map((post) => (
            <InsightCard key={`${post.post_id}-${post.title}`} post={post} />
          ))}
        </div>
      </section>

      <section className="page-shell two-col compact">
        <article className="panel governance-note">
          <ShieldCheck size={18} />
          <div>
            <h3>Governance note</h3>
            <p>
              {linkedRumours.length || "No"} released rumor alert involving {selectedTicker.ticker} met the threshold in this run.
              High-stakes matches are held in the review track before publication.
            </p>
          </div>
        </article>
        <RouteCard
          label="Next"
          title="Open Analyst Review queue"
          body="Inspect released alerts and any held high-stakes rumors before publication."
          action="Open queue"
          onClick={() => navigate("/review")}
        />
      </section>

      <section className="page-shell">
        <SectionTitle
          title={`${selectedTicker.ticker} vs ${compare.ticker} · side by side`}
          aside="single-run comparison · not a trend"
        />
        <p className="muted">
          Same metrics, same chart type. Lower confidence and higher sarcasm indicate weaker reads.
        </p>
        <div className="compare-grid">
          <ComparePanel ticker={selectedTicker} />
          <ComparePanel ticker={compare} emphasized={compare.low_confidence} />
        </div>
        <article className="panel delta-panel">
          <span className="eyebrow">Confidence delta</span>
          <strong>{Math.abs((selectedTicker.avg_confidence || 0) - (compare.avg_confidence || 0)).toFixed(2)}</strong>
          <span>{confidenceDeltaCopy(selectedTicker, compare)}</span>
        </article>
      </section>
    </main>
  );
}

function ReviewQueue({ run, reviewStatus, setReviewStatus }: ViewProps) {
  const [filter, setFilter] = useState<ReviewStatus | "all">("all");
  const [selected, setSelected] = useState(0);
  const defaultReviewStatus: ReviewStatus = hasSplitGovernance(run) ? "approved" : "pending";
  const counts = countStatuses(run, reviewStatus, defaultReviewStatus);
  const heldCount = heldRumorCount(run);
  const releasedCount = releasedRumorCount(run);
  const reviewThreshold = numericConfig(run, "rumour_human_review_min_conf") ?? 0.8;
  const visible = run.rumours.filter((rumour, index) => {
    const status = reviewStatus[rumourKey(rumour, index)] || (hasSplitGovernance(run) ? "approved" : "pending");
    return filter === "all" || status === filter;
  });

  function setStatus(index: number, status: ReviewStatus) {
    const key = rumourKey(run.rumours[index], index);
    setReviewStatus((current) => ({ ...current, [key]: status }));
  }

  return (
    <main>
      <section className="page-shell detail-header">
        <p className="eyebrow">Governance · human checkpoint · analyst input</p>
        <h1>Analyst Review queue</h1>
        <p className="lede small">
          This is where high-stakes rumor alerts would stop for analyst input before publication. Released
          alerts remain visible with unverified-source disclaimers.
        </p>
      </section>

      <section className="page-shell review-layout">
        <div className="policy-banner">
          <ShieldCheck size={18} />
          <div>
            <span className="eyebrow amber-text">Policy</span>
            <p>
              High-confidence rumors enter the governance track. Items matching the high-stakes hold policy
              are withheld before publication; released alerts stay labeled as unverified.
            </p>
            <div className="policy-grid">
              <span><strong>Owner</strong> Analyst Review</span>
              <span><strong>Hold trigger</strong> confidence ≥ {reviewThreshold.toFixed(2)} and high-stakes rumour type.</span>
              <span><strong>This run</strong> {fmt(heldCount)} held · {fmt(releasedCount)} released</span>
            </div>
          </div>
        </div>

        <div className="input-required">
          <strong>{heldCount > 0 ? "Input required" : "No held items in this run"}</strong>
          <span>
            {heldCount > 0
              ? "Approve, reject, or escalate each held rumor."
              : "Inspect the released high-confidence alerts and source evidence."}
          </span>
          <span>{fmt(heldCount)} held of {fmt(run.metadata.rumours_flagged)}</span>
        </div>

        <div className="status-tabs">
          {(["pending", "approved", "rejected", "escalated", "all"] as const).map((status) => (
            <button
              className={filter === status ? "active" : ""}
              key={status}
              onClick={() => setFilter(status)}
              type="button"
            >
              {labelStatus(status)} {status === "all" ? run.rumours.length : counts[status]}
            </button>
          ))}
        </div>

        <div className="queue-list">
          {visible.map((rumour) => {
            const originalIndex = run.rumours.indexOf(rumour);
            const status = reviewStatus[rumourKey(rumour, originalIndex)] || (hasSplitGovernance(run) ? "approved" : "pending");
            const expanded = selected === originalIndex;
            return (
              <article className={`queue-card ${expanded ? "expanded" : ""}`} key={rumourKey(rumour, originalIndex)}>
                <button className="queue-summary" onClick={() => setSelected(originalIndex)} type="button">
                  <span className="queue-ticker">{rumour.primary_ticker}</span>
                  <span>
                    <strong>{rumour.title}</strong>
                    <small>{rumour.rumour_summary}</small>
                  </span>
                  <Chip tone={statusTone(status)}>{labelStatus(status)}</Chip>
                </button>
                {expanded ? (
                  <div className="queue-detail">
                    <p>{rumour.rumour_summary}</p>
                    <div className="detail-grid">
                      <span><strong>Detected</strong>{rumour.date ? formatDate(rumour.date) : "Saved run"}</span>
                      <span><strong>Rumor type</strong>{rumour.rumour_type}</span>
                      <span><strong>Confidence</strong>{fixed(rumour.rumour_confidence)} · {status === "approved" ? "released alert" : "review required"}</span>
                    </div>
                    <a href={`https://www.reddit.com${rumour.permalink || ""}`} target="_blank" rel="noreferrer">
                      Source thread
                    </a>
                    <div className="action-row">
                      <button className="approve" onClick={() => setStatus(originalIndex, "approved")} type="button">
                        <CheckCircle2 size={14} /> Mark released
                      </button>
                      <button className="reject" onClick={() => setStatus(originalIndex, "rejected")} type="button">
                        <XCircle size={14} /> Reject
                      </button>
                      <button className="escalate" onClick={() => setStatus(originalIndex, "escalated")} type="button">
                        <AlertTriangle size={14} /> Escalate for review
                      </button>
                      <span className="mono subtle">Session-only · no persistence</span>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>

        <div className="audit-note">
          <Circle size={16} />
          <p>
            Prototype audit note: review actions update local UI state only. In production, held actions
            would be written to an immutable audit log with reviewer identity and timestamp.
          </p>
        </div>
      </section>
    </main>
  );
}

function RunAnalysisPanel({
  apiKeyInput,
  apiKeyConfigured,
  localApiMessage,
  localJob,
  setApiKeyInput,
  saveApiKey,
  runAnalysis,
}: {
  apiKeyInput: string;
  apiKeyConfigured: boolean;
  localApiMessage: string;
  localJob: LocalJob | null;
  setApiKeyInput: (value: string) => void;
  saveApiKey: () => Promise<void>;
  runAnalysis: () => Promise<void>;
}) {
  const command = "export ANTHROPIC_API_KEY=your_key_here\npython main.py\ncd web && npm run cache-runs && npm run dev";
  const [copied, setCopied] = useState(false);

  async function copyCommand() {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="run-panel key-panel">
      <span className="key-kicker">API key setup · local only</span>
      <h3>Paste your Anthropic key here</h3>
      <p>
        Save the Anthropic key into this repo's local `.env`, then start the Python pipeline from the browser.
        The helper runs only on localhost and never returns the key to the frontend.
      </p>
      <div className="key-form">
        <label>
          <span>Local Anthropic key</span>
          <input
            type="password"
            value={apiKeyInput}
            placeholder={apiKeyConfigured ? "Configured in .env" : "Paste key here only in local browser"}
            onChange={(event) => setApiKeyInput(event.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <button onClick={saveApiKey} type="button" disabled={!apiKeyInput.trim()}>
          <KeyRound size={14} /> Save API key to .env
        </button>
      </div>
      <button onClick={runAnalysis} type="button" disabled={!apiKeyConfigured || localJob?.running}>
        <Play size={14} /> {localJob?.running ? "Analysis running" : "Run analysis"}
      </button>
      <p className="status-line">{localApiMessage}</p>
      {localJob && localJob.status !== "idle" ? (
        <div className="job-box">
          <strong>Status: {localJob.status}</strong>
          {localJob.output ? <pre>{localJob.output}</pre> : <small>No output yet.</small>}
        </div>
      ) : null}
      <details>
        <summary>Terminal fallback</summary>
        <pre>{command}</pre>
        <button onClick={copyCommand} type="button">
          <Play size={14} /> {copied ? "Copied" : "Copy run commands"}
        </button>
      </details>
    </div>
  );
}

function TrustPanel() {
  return (
    <article className="panel trust-panel">
      <SectionTitle title="Why trust this output?" aside="reproducible and reviewable" />
      <div className="trust-item">
        <RotateCcw size={16} />
        <div><strong>Replay mode</strong><p>Completed runs can be replayed from saved CSVs without API calls.</p></div>
      </div>
      <div className="trust-item">
        <CheckCircle2 size={16} />
        <div><strong>Test cases</strong><p>Eight documented cases cover ticker reports, sarcasm handling, and rumor routing.</p></div>
      </div>
      <div className="trust-item">
        <ShieldCheck size={16} />
        <div><strong>Governance</strong><p>High-stakes rumors are held for review; released alerts remain marked as unverified.</p></div>
      </div>
    </article>
  );
}

function RunScope({ run }: { run: RunDataset }) {
  return (
    <aside className="run-scope">
      <span className="eyebrow">Run scope</span>
      <strong>{runDate(run)}</strong>
      <small>{runWindowLabel(run)} · {dateRange(run)}</small>
      <p>Frontend cache from a completed pipeline run. Treat outputs as decision support, not a forecast.</p>
    </aside>
  );
}

function SectionTitle({ title, aside }: { title: string; aside?: string }) {
  return (
    <div className="section-title">
      <h2>{title}</h2>
      {aside ? <span>{aside}</span> : null}
    </div>
  );
}

function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "green" | "amber" }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong className={tone ? `${tone}-text` : ""}>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

function TickerTable({ tickers, onTicker }: { tickers: TickerSummary[]; onTicker: (ticker: string) => void }) {
  return (
    <div className="ticker-table">
      <div className="table-head">
        <span>Ticker</span>
        <span>Posts</span>
        <span>Sentiment mix</span>
        <span>Avg conf.</span>
        <span>Avg rel.</span>
        <span>Sarcasm</span>
        <span>Avg eng.</span>
      </div>
      {tickers.map((ticker) => (
        <button className="table-row" key={ticker.ticker} onClick={() => onTicker(ticker.ticker)} type="button">
          <span><strong>{ticker.ticker}</strong><small>{tickerName(ticker.ticker)}</small></span>
          <span>{fmt(ticker.post_count)}</span>
          <span>
            {ticker.low_sample ? <em>not reported · low sample</em> : <SentimentMix ticker={ticker} compact />}
          </span>
          <span>{fixed(ticker.avg_confidence)}</span>
          <span>{ticker.avg_relevance === undefined ? "—" : fixed(ticker.avg_relevance)}</span>
          <span>{ticker.sarcastic_count ?? "—"}</span>
          <span>{ticker.avg_engagement ? fixed(ticker.avg_engagement) : "—"}</span>
        </button>
      ))}
    </div>
  );
}

function SentimentMix({ ticker, compact = false }: { ticker: TickerSummary; compact?: boolean }) {
  return (
    <div className={`sentiment-mix ${compact ? "compact" : ""}`}>
      <div className="mix-bar">
        <span className="green-bg" style={{ width: `${ticker.bullish_pct}%` }} />
        <span className="neutral-bg" style={{ width: `${ticker.neutral_pct}%` }} />
        <span className="red-bg" style={{ width: `${ticker.bearish_pct}%` }} />
      </div>
      <div className="mix-labels">
        <span className="green-text">▲ {ticker.bullish_pct.toFixed(1)}%</span>
        <span>◇ {ticker.neutral_pct.toFixed(1)}%</span>
        <span className="red-text">▼ {ticker.bearish_pct.toFixed(1)}%</span>
      </div>
    </div>
  );
}

function NetSentimentChart({ tickers }: { tickers: TickerSummary[] }) {
  return (
    <div className="net-chart">
      <div className="axis-line" />
      {tickers.map((ticker) => {
        const net = netSentiment(ticker);
        return (
          <div className="net-bar-col" key={ticker.ticker}>
            <div className="net-bar-wrap">
              <span
                className={net >= 0 ? "net-bar positive" : "net-bar negative"}
                style={{ height: `${Math.max(12, Math.abs(net) * 2)}px` }}
              />
            </div>
            <strong>{ticker.ticker}</strong>
          </div>
        );
      })}
    </div>
  );
}

function Donut({ ticker }: { ticker: TickerSummary }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const bull = (ticker.bullish_pct / 100) * circumference;
  const neutral = (ticker.neutral_pct / 100) * circumference;
  const bear = (ticker.bearish_pct / 100) * circumference;
  return (
    <svg className="donut" viewBox="0 0 120 120" role="img" aria-label={`${ticker.ticker} sentiment mix`}>
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#c9ced3" strokeWidth="16" />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#2f8556" strokeWidth="16" strokeDasharray={`${bull} ${circumference - bull}`} strokeDashoffset="0" transform="rotate(-90 60 60)" />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#6b737c" strokeWidth="16" strokeDasharray={`${neutral} ${circumference - neutral}`} strokeDashoffset={-bull} transform="rotate(-90 60 60)" />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#b63a3a" strokeWidth="16" strokeDasharray={`${bear} ${circumference - bear}`} strokeDashoffset={-(bull + neutral)} transform="rotate(-90 60 60)" />
      <text x="60" y="57" textAnchor="middle" className="donut-label">Posts</text>
      <text x="60" y="76" textAnchor="middle" className="donut-value">{ticker.post_count}</text>
    </svg>
  );
}

function BarList({ rows, total }: { rows: Array<[string, number]>; total: number }) {
  return (
    <div className="bar-list">
      {rows.map(([label, count]) => (
        <div className="bar-list-row" key={label}>
          <span>{label}</span>
          <div><span style={{ width: `${Math.max(4, (count / Math.max(total, 1)) * 100)}%` }} /></div>
          <small>{count} · {pct(count, total)}</small>
        </div>
      ))}
    </div>
  );
}

function StackedTimelineChart({
  points,
}: {
  points: Array<{ label?: string; day?: string; bullish: number; bearish: number; neutral: number; post_count: number }>;
}) {
  const max = Math.max(...points.map((point) => point.post_count), 1);
  return (
    <div className="daily-chart">
      {points.map((point) => (
        <div className="day-col" key={point.label || point.day}>
          <div className="stack" style={{ height: `${Math.max(30, (point.post_count / max) * 150)}px` }}>
            <span className="green-bg" style={{ flex: point.bullish || 0.01 }} />
            <span className="neutral-bg" style={{ flex: point.neutral || 0.01 }} />
            <span className="red-bg" style={{ flex: point.bearish || 0.01 }} />
          </div>
          <small>{point.label || shortDate(point.day || "")}</small>
        </div>
      ))}
    </div>
  );
}

function InsightCard({ post }: { post: SentimentPost }) {
  return (
    <article className="insight-card">
      <div className="chip-row">
        <Chip tone={post.sentiment === "bearish" ? "red" : post.sentiment === "bullish" ? "green" : undefined}>
          {String(post.sentiment || "neutral").toUpperCase()}
        </Chip>
        {post.post_type ? <Chip>{post.post_type.toUpperCase()}</Chip> : null}
        {post.is_sarcastic ? <Chip tone="amber">Sarcasm</Chip> : null}
        {post.score ? <span className="score">▲ {fmt(post.score)}</span> : null}
      </div>
      <h3>{post.title}</h3>
      <p>{post.key_insight || "Source withheld · governance review retained."}</p>
      <small>confidence {fixed(post.confidence)} · source withheld · governance</small>
    </article>
  );
}

function ComparePanel({ ticker, emphasized = false }: { ticker: TickerSummary; emphasized?: boolean }) {
  return (
    <article className={`panel compare-panel ${emphasized ? "emphasized" : ""}`}>
      <div className="compare-head">
        <div><h3>{ticker.ticker}</h3><span>{tickerName(ticker.ticker)}</span></div>
        <Chip tone="red">Net {netSentiment(ticker).toFixed(1)} pp</Chip>
      </div>
      <div className="chip-row">
        {ticker.low_confidence ? <Chip tone="amber">Low confidence</Chip> : null}
        {ticker.sarcastic_count ? <Chip tone="amber">Sarcasm {pct(ticker.sarcastic_count, ticker.post_count)}</Chip> : null}
      </div>
      <div className="metric-row compact-metrics">
        <Stat label="Posts" value={fmt(ticker.post_count)} />
        <Stat label="Avg confidence" value={fixed(ticker.avg_confidence)} tone={ticker.low_confidence ? "amber" : undefined} />
        <Stat label="Avg relevance" value={fixed(ticker.avg_relevance)} />
        <Stat label="Sarcasm rate" value={pct(ticker.sarcastic_count, ticker.post_count)} tone="amber" />
        <Stat label="Avg engagement" value={fmt(Math.round(ticker.avg_engagement || 0))} />
        <Stat label="Sarcastic posts" value={fmt(ticker.sarcastic_count)} hint={`of ${ticker.post_count}`} />
      </div>
      <SentimentMix ticker={ticker} />
      <Donut ticker={ticker} />
    </article>
  );
}

function RouteCard({
  icon,
  label,
  title,
  body,
  action,
  onClick,
  badge,
}: {
  icon?: React.ReactNode;
  label: string;
  title: string;
  body: string;
  action: string;
  onClick: () => void;
  badge?: string;
}) {
  return (
    <article className="panel route-card">
      <span className="eyebrow">{icon}{label}{badge ? <b>{badge}</b> : null}</span>
      <h3>{title}</h3>
      <p>{body}</p>
      <button onClick={onClick} type="button">{action} →</button>
    </article>
  );
}

function Chip({ children, tone }: { children: React.ReactNode; tone?: "green" | "red" | "amber" | "blue" }) {
  return <span className={`chip ${tone ? `chip-${tone}` : ""}`}>{children}</span>;
}

function pickTicker(tickers: TickerSummary[], ticker: string) {
  return tickers.find((item) => item.ticker.toUpperCase() === ticker.toUpperCase());
}

function postsForTicker(run: RunDataset, ticker: string) {
  return run.posts.filter((post) => post.primary_ticker === ticker);
}

function countStatuses(run: RunDataset, statuses: Record<string, ReviewStatus>, defaultStatus: ReviewStatus = "pending") {
  return run.rumours.reduce(
    (acc, rumour, index) => {
      const status = statuses[rumourKey(rumour, index)] || defaultStatus;
      acc[status] += 1;
      return acc;
    },
    { pending: 0, approved: 0, rejected: 0, escalated: 0 } as Record<ReviewStatus, number>
  );
}

function rumourKey(rumour: SentimentPost, index: number) {
  return `${rumour.post_id || rumour.title}-${index}`;
}

function labelStatus(status: ReviewStatus | "all") {
  return {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    escalated: "Escalated",
    all: "All",
  }[status];
}

function statusTone(status: ReviewStatus): "green" | "red" | "amber" | "blue" {
  return { pending: "amber", approved: "green", rejected: "red", escalated: "blue" }[status] as
    | "green"
    | "red"
    | "amber"
    | "blue";
}

function tickerName(ticker: string) {
  return (
    {
      SPY: "SPDR S&P 500 ETF",
      TSLA: "Tesla, Inc.",
      TACO: "TACO subreddit slang ticker",
      QQQ: "Invesco QQQ Trust",
      META: "Meta Platforms, Inc.",
      INTC: "Intel Corporation",
    }[ticker] || "Ticker from saved run"
  );
}

function runDate(run: RunDataset) {
  const timestamp = run.metadata.run_timestamp || "";
  return timestamp ? timestamp.slice(0, 10) : run.id.replace("run_", "");
}

function runDays(run: RunDataset) {
  return Array.from(new Set(run.daily.map((point) => point.day).filter(Boolean))).sort();
}

function runDayCount(run: RunDataset) {
  return runDays(run).length || 0;
}

function runWindowLabel(run: RunDataset) {
  const count = runDayCount(run);
  if (!count) return "saved run";
  return count >= 28 ? `${count}-day expanded run` : `${count}-day saved run`;
}

function monthlyFromDaily(
  points: Array<{ day: string; bullish: number; bearish: number; neutral: number; post_count: number }>
) {
  const byMonth = new Map<string, { bullish: number; bearish: number; neutral: number; post_count: number }>();
  points.forEach((point) => {
    const month = point.day.slice(0, 7);
    const bucket = byMonth.get(month) || { bullish: 0, bearish: 0, neutral: 0, post_count: 0 };
    bucket.bullish += (point.bullish / 100) * point.post_count;
    bucket.bearish += (point.bearish / 100) * point.post_count;
    bucket.neutral += (point.neutral / 100) * point.post_count;
    bucket.post_count += point.post_count;
    byMonth.set(month, bucket);
  });
  return Array.from(byMonth.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([month, bucket]) => ({
      label: monthLabel(month),
      post_count: bucket.post_count,
      bullish: bucket.post_count ? (bucket.bullish / bucket.post_count) * 100 : 0,
      bearish: bucket.post_count ? (bucket.bearish / bucket.post_count) * 100 : 0,
      neutral: bucket.post_count ? (bucket.neutral / bucket.post_count) * 100 : 0,
    }));
}

function dateRange(run: RunDataset) {
  const days = runDays(run);
  if (!days.length) return "saved output files";
  return `${days[0]} → ${days[days.length - 1]}`;
}

function hasSplitGovernance(run: RunDataset) {
  return run.metadata.rumours_released !== undefined || run.metadata.rumours_pending_review !== undefined;
}

function releasedRumorCount(run: RunDataset) {
  return run.metadata.rumours_released ?? run.rumours.length;
}

function heldRumorCount(run: RunDataset) {
  return run.metadata.rumours_pending_review ?? run.rumours.length;
}

function numericConfig(run: RunDataset, key: string) {
  const value = run.metadata.config?.[key];
  return typeof value === "number" ? value : undefined;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function shortDate(value: string) {
  const [, month, day] = value.split("-");
  return `${month}/${day}`;
}

function monthLabel(value: string) {
  const [year, month] = value.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function netSentiment(ticker: TickerSummary) {
  return (ticker.bullish_pct || 0) - (ticker.bearish_pct || 0);
}

function confidenceDeltaCopy(left: TickerSummary, right: TickerSummary) {
  const leftConfidence = left.avg_confidence || 0;
  const rightConfidence = right.avg_confidence || 0;
  const comparison =
    Math.abs(leftConfidence - rightConfidence) < 0.005
      ? "matches"
      : leftConfidence > rightConfidence
        ? "is higher than"
        : "is lower than";
  return `${left.ticker}'s average classifier confidence (${fixed(left.avg_confidence)}) ${comparison} ${right.ticker}'s (${fixed(right.avg_confidence)}) in this run.`;
}

function fmt(value: number | undefined) {
  return value === undefined ? "—" : Math.round(value).toLocaleString();
}

function fixed(value: number | undefined) {
  return value === undefined ? "—" : value.toFixed(2);
}

function pct(value: number | undefined, total: number | undefined) {
  if (!value || !total) return "0%";
  return `${Math.round((value / total) * 100)}%`;
}
