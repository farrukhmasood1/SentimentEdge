import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const envPath = path.join(repoRoot, ".env");
const port = Number(process.env.SENTIMENTEDGE_LOCAL_API_PORT || 8787);

let job = {
  running: false,
  status: "idle",
  startedAt: null,
  finishedAt: null,
  exitCode: null,
  output: "",
};

function send(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(JSON.stringify(payload));
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = Buffer.concat(chunks).toString("utf8");
  return body ? JSON.parse(body) : {};
}

async function readEnv() {
  if (!existsSync(envPath)) return "";
  return readFile(envPath, "utf8");
}

async function hasApiKey() {
  if (process.env.ANTHROPIC_API_KEY) return true;
  const env = await readEnv();
  return /^ANTHROPIC_API_KEY=.+/m.test(env);
}

async function upsertApiKey(apiKey) {
  const trimmed = String(apiKey || "").trim();
  if (!trimmed.startsWith("sk-ant-")) {
    throw new Error("This does not look like an Anthropic API key.");
  }
  const escaped = trimmed.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
  const current = await readEnv();
  const line = `ANTHROPIC_API_KEY="${escaped}"`;
  const next = /^ANTHROPIC_API_KEY=.*/m.test(current)
    ? current.replace(/^ANTHROPIC_API_KEY=.*/m, line)
    : `${current.trimEnd()}${current.trim() ? "\n" : ""}${line}\n`;
  await writeFile(envPath, next, { mode: 0o600 });
}

async function loadEnvForChild() {
  const env = { ...process.env };
  const content = await readEnv();
  for (const line of content.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) continue;
    const [, key, rawValue] = match;
    env[key] = rawValue.replace(/^"(.*)"$/, "$1").replaceAll('\\"', '"').replaceAll("\\\\", "\\");
  }
  return env;
}

function appendOutput(text) {
  const redacted = text.replace(/sk-ant-[A-Za-z0-9_-]+/g, "sk-ant-[redacted]");
  job.output = `${job.output}${redacted}`.slice(-20_000);
}

async function runPipeline() {
  if (job.running) return;
  job = {
    running: true,
    status: "running_pipeline",
    startedAt: new Date().toISOString(),
    finishedAt: null,
    exitCode: null,
    output: "",
  };

  const env = await loadEnvForChild();
  const pipeline = spawn("python", ["main.py"], {
    cwd: repoRoot,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  pipeline.stdout.on("data", (chunk) => appendOutput(chunk.toString()));
  pipeline.stderr.on("data", (chunk) => appendOutput(chunk.toString()));

  pipeline.on("close", (code) => {
    job.exitCode = code;
    if (code !== 0) {
      job.running = false;
      job.status = "failed";
      job.finishedAt = new Date().toISOString();
      appendOutput(`\nPipeline exited with code ${code}.\n`);
      return;
    }

    job.status = "refreshing_cache";
    const cache = spawn("python", ["scripts/cache_frontend_runs.py"], {
      cwd: repoRoot,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    cache.stdout.on("data", (chunk) => appendOutput(chunk.toString()));
    cache.stderr.on("data", (chunk) => appendOutput(chunk.toString()));
    cache.on("close", (cacheCode) => {
      job.running = false;
      job.exitCode = cacheCode;
      job.status = cacheCode === 0 ? "completed" : "cache_failed";
      job.finishedAt = new Date().toISOString();
    });
  });
}

createServer(async (req, res) => {
  if (req.method === "OPTIONS") return send(res, 204, {});

  try {
    if (req.method === "GET" && req.url === "/api/status") {
      return send(res, 200, { apiKeyConfigured: await hasApiKey(), job });
    }

    if (req.method === "POST" && req.url === "/api/key") {
      const { apiKey } = await readJson(req);
      await upsertApiKey(apiKey);
      return send(res, 200, { ok: true, apiKeyConfigured: true });
    }

    if (req.method === "POST" && req.url === "/api/run-analysis") {
      if (!(await hasApiKey())) {
        return send(res, 400, { ok: false, error: "ANTHROPIC_API_KEY is not configured." });
      }
      await runPipeline();
      return send(res, 202, { ok: true, job });
    }

    return send(res, 404, { error: "Not found" });
  } catch (error) {
    return send(res, 500, { error: error instanceof Error ? error.message : "Local API error" });
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`SentimentEdge local API listening on http://127.0.0.1:${port}`);
  console.log("This helper is localhost-only. It never sends your API key to the browser bundle.");
});
