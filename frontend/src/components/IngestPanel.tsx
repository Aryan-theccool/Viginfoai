import { useState } from "react";
import { api } from "../api";

export function IngestPanel({ onDone }: { onDone: () => void }) {
  const [tab, setTab] = useState<"pubmed" | "maude" | "manual">("maude");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [query, setQuery] = useState('("infusion pump") AND ("adverse event" OR "safety")');
  const [device, setDevice] = useState("infusion pump");
  const [count, setCount] = useState(5);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  async function run(fn: () => Promise<{ records_created: number; findings_created: number; engine: string }>) {
    setBusy(true);
    setMsg(null);
    try {
      const r = await fn();
      setMsg(`✓ Ingested ${r.records_created} record(s) → ${r.findings_created} AI finding(s) [${r.engine}]`);
      onDone();
    } catch (e) {
      setMsg(`✗ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold">Ingest evidence</h2>
      <p className="text-sm text-slate-500 mb-4">Pull live data — every record is AI-analyzed on arrival.</p>
      <div className="flex gap-2 mb-4">
        {(
          [
            ["maude", "FDA MAUDE"],
            ["pubmed", "PubMed"],
            ["manual", "Manual / PDF text"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold border ${
              tab === k ? "bg-teal-600 text-white border-teal-600" : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "maude" && (
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="font-medium">Device name</span>
            <input value={device} onChange={(e) => setDevice(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="infusion pump" />
          </label>
          <label className="block text-sm">
            <span className="font-medium">Max records ({count})</span>
            <input type="range" min={1} max={25} value={count} onChange={(e) => setCount(+e.target.value)} className="w-full" />
          </label>
          <button disabled={busy} onClick={() => run(() => api.ingestMaude(device, count))}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50">
            {busy ? "Fetching MAUDE…" : "Fetch adverse events"}
          </button>
        </div>
      )}

      {tab === "pubmed" && (
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="font-medium">PubMed query</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" />
          </label>
          <label className="block text-sm">
            <span className="font-medium">Max articles ({count})</span>
            <input type="range" min={1} max={25} value={count} onChange={(e) => setCount(+e.target.value)} className="w-full" />
          </label>
          <button disabled={busy} onClick={() => run(() => api.ingestPubmed(query, count))}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50">
            {busy ? "Searching PubMed…" : "Search literature"}
          </button>
        </div>
      )}

      {tab === "manual" && (
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="font-medium">Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Paste from PDF, complaint, vigilance report…" />
          </label>
          <label className="block text-sm">
            <span className="font-medium">Source text</span>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={5}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Minimum 20 characters…" />
          </label>
          <button disabled={busy || text.length < 20 || !title} onClick={() => run(() => api.ingestManual(title, text, "Manual"))}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50">
            {busy ? "Analyzing…" : "Analyze text"}
          </button>
        </div>
      )}

      {msg && (
        <div className={`mt-4 rounded-lg border px-3 py-2 text-sm ${msg.startsWith("✓") ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-red-300 bg-red-50 text-red-800"}`}>
          {msg}
        </div>
      )}
    </div>
  );
}
