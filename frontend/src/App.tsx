import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { AuditEntry, Finding, FindingDetail, Stats } from "./types";
import { CategoryBadge, ConfidenceBar, ImdrfBadge, StatusBadge } from "./components/badges";
import { HighlightedText } from "./components/HighlightedText";
import { IngestPanel } from "./components/IngestPanel";
import { AuditTrail } from "./components/AuditTrail";

type View = "review" | "ingest" | "audit";

const CATEGORIES = ["Clinical Performance", "Safety Signal", "Risk", "Irrelevant"];

export default function App() {
  const [view, setView] = useState<View>("review");
  const [stats, setStats] = useState<Stats | null>(null);
  const [queue, setQueue] = useState<Finding[]>([]);
  const [filter, setFilter] = useState<string>("PENDING");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<FindingDetail | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [globalAudit, setGlobalAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);

  // Review form
  const [email, setEmail] = useState("reviewer@viginfo.ai");
  const [notes, setNotes] = useState("");
  const [overrideCat, setOverrideCat] = useState(CATEGORIES[0]);
  const [showOverride, setShowOverride] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const refreshStats = useCallback(async () => {
    try {
      setStats(await api.stats());
    } catch {
      /* backend offline */
    }
  }, []);

  const refreshQueue = useCallback(async () => {
    try {
      const q = await api.findings(filter === "ALL" ? undefined : filter);
      setQueue(q);
      if (!selectedId && q.length) setSelectedId(q[0].id);
    } catch {
      setQueue([]);
    }
  }, [filter, selectedId]);

  const refreshDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const [d, a] = await Promise.all([api.finding(id), api.audit(id)]);
      setDetail(d);
      setAudit(a);
    } catch (e) {
      setToast(`Failed to load finding: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);
  useEffect(() => {
    refreshQueue();
  }, [refreshQueue]);
  useEffect(() => {
    if (selectedId) refreshDetail(selectedId);
  }, [selectedId, refreshDetail]);
  useEffect(() => {
    if (view === "audit") api.audit().then(setGlobalAudit).catch(() => setGlobalAudit([]));
  }, [view]);

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  }

  async function submitReview(status: "APPROVED" | "REJECTED" | "MODIFIED") {
    if (!detail) return;
    if (!email.includes("@")) return flash("Enter a valid reviewer email.");
    setSaving(true);
    try {
      await api.submitReview({
        finding_id: detail.id,
        reviewer_email: email,
        status,
        override_category: status === "MODIFIED" ? overrideCat : undefined,
        reviewer_notes: notes || undefined,
      });
      setNotes("");
      setShowOverride(false);
      await Promise.all([refreshDetail(detail.id), refreshQueue(), refreshStats()]);
      flash(`Finding ${status.toLowerCase()} — audit trail updated.`);
    } catch (e) {
      flash(`Review failed: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  async function reanalyze() {
    if (!detail) return;
    setLoading(true);
    try {
      await api.reanalyze(detail.id);
      await Promise.all([refreshDetail(detail.id), refreshQueue(), refreshStats()]);
      flash("Re-analysis complete.");
    } catch (e) {
      flash(`Re-analysis failed: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  const meta = useMemo(() => detail?.source_record?.record_metadata ?? {}, [detail]);

  return (
    <div className="min-h-screen">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-slate-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500 font-extrabold text-lg">V</div>
          <div>
            <h1 className="text-lg font-extrabold leading-tight tracking-tight">VigInfo AI</h1>
            <p className="text-[11px] uppercase tracking-widest text-slate-400">MDR evidence &amp; vigilance · EU 2017/745</p>
          </div>
          <nav className="ml-6 flex gap-1">
            {(
              [
                ["review", "Review workspace"],
                ["ingest", "Ingest"],
                ["audit", "Audit ledger"],
              ] as [View, string][]
            ).map(([v, label]) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
                  view === v ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="ml-auto hidden items-center gap-3 md:flex">
            {stats && (
              <>
                <span className="rounded-full bg-slate-800 px-2.5 py-1 font-mono text-[11px] text-slate-300">
                  engine: {stats.engine}
                </span>
                <span className="rounded-full bg-amber-500/20 px-2.5 py-1 text-xs font-bold text-amber-300">
                  {stats.pending} pending
                </span>
                <span className="rounded-full bg-red-500/20 px-2.5 py-1 text-xs font-bold text-red-300">
                  {stats.safety_signals} safety signals
                </span>
              </>
            )}
          </div>
        </div>
      </header>

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-30 -translate-x-1/2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-xl">
          {toast}
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* ── Stats strip ──────────────────────────────────── */}
        {stats && (
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-6">
            {[
              ["Records", stats.records],
              ["Findings", stats.findings],
              ["Pending", stats.pending],
              ["Approved", stats.approved],
              ["Modified", stats.modified],
              ["Rejected", stats.rejected],
            ].map(([label, v]) => (
              <div key={label as string} className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <div className="text-2xl font-extrabold">{v as number}</div>
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label as string}</div>
              </div>
            ))}
          </div>
        )}

        {view === "ingest" && (
          <div className="max-w-2xl">
            <IngestPanel
              onDone={() => {
                refreshQueue();
                refreshStats();
              }}
            />
          </div>
        )}

        {view === "audit" && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
            <h2 className="text-lg font-bold mb-1">Immutable audit ledger</h2>
            <p className="text-sm text-slate-500 mb-4">
              Append-only record of every AI extraction and human decision — EU MDR / 21 CFR Part 11 aligned.
            </p>
            <AuditTrail entries={globalAudit} />
          </div>
        )}

        {view === "review" && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
            {/* ── Queue ─────────────────────────────────── */}
            <aside className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm h-fit lg:sticky lg:top-[76px]">
              <div className="mb-2 flex items-center justify-between px-1">
                <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Review queue</h2>
                <select
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setSelectedId(null);
                  }}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold"
                >
                  {["PENDING", "APPROVED", "MODIFIED", "REJECTED", "ALL"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="scroll-thin max-h-[60vh] space-y-2 overflow-y-auto">
                {queue.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedId(f.id)}
                    className={`w-full rounded-lg border p-3 text-left transition ${
                      selectedId === f.id
                        ? "border-teal-500 bg-teal-50 ring-1 ring-teal-500"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="mb-1.5 flex flex-wrap gap-1.5">
                      <CategoryBadge category={f.category} />
                      <StatusBadge status={f.review_status} />
                    </div>
                    <p className="line-clamp-2 text-[13px] font-medium leading-snug text-slate-800">
                      {f.source_title ?? f.id}
                    </p>
                    <p className="mt-1 font-mono text-[11px] text-slate-400">
                      {f.source_type} · {Math.round((f.confidence_score ?? 0) * 100)}%
                    </p>
                  </button>
                ))}
                {!queue.length && <p className="p-4 text-center text-sm text-slate-500">Queue empty — ingest evidence to begin.</p>}
              </div>
            </aside>

            {/* ── Split view ────────────────────────────── */}
            <section>
              {!detail ? (
                <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-500">
                  {loading ? "Loading…" : "Select a finding from the queue."}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    {/* Left: source record */}
                    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                      <div className="mb-3 flex items-center justify-between">
                        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">Source record</h3>
                        <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-600">
                          {detail.source_type} · {detail.source_record?.external_id}
                        </span>
                      </div>
                      <h2 className="mb-3 text-[15px] font-bold leading-snug">{detail.source_title}</h2>
                      <div className="scroll-thin max-h-[420px] overflow-y-auto rounded-lg bg-slate-50 p-4">
                        <HighlightedText text={detail.source_record?.raw_text ?? ""} quote={detail.exact_quote} />
                      </div>
                      {Object.keys(meta).length > 0 && (
                        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                          {Object.entries(meta).slice(0, 6).map(([k, v]) => (
                            <div key={k} className="flex gap-1 truncate">
                              <dt className="font-semibold text-slate-500">{k}:</dt>
                              <dd className="truncate text-slate-700">{String(v)}</dd>
                            </div>
                          ))}
                        </dl>
                      )}
                    </div>

                    {/* Right: AI finding + review */}
                    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                      <div className="mb-2 flex items-center justify-between">
                        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">AI finding &amp; human review</h3>
                        <button onClick={reanalyze} className="text-xs font-semibold text-teal-700 hover:underline">
                          ⟳ Re-analyze
                        </button>
                      </div>
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <CategoryBadge category={detail.category} />
                        <StatusBadge status={detail.review_status} />
                        <ConfidenceBar value={detail.confidence_score} />
                      </div>

                      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                        <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-amber-700">Exact quote (verbatim)</p>
                        <p className="font-mono text-[13px] leading-relaxed text-amber-950">“{detail.exact_quote}”</p>
                      </div>

                      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-slate-500">Plain-language rationale</p>
                        <p className="text-sm leading-relaxed text-slate-800">{detail.plain_language_rationale}</p>
                      </div>

                      {(detail.imdrf_annex_a || detail.imdrf_annex_e) && (
                        <div className="mt-3">
                          <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                            IMDRF coding <span className="font-medium normal-case">(suggested — confirm below)</span>
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {detail.imdrf_annex_a && (
                              <ImdrfBadge code={detail.imdrf_annex_a} label={detail.imdrf_annex_a_label} annex="A" />
                            )}
                            {detail.imdrf_annex_e && (
                              <ImdrfBadge code={detail.imdrf_annex_e} label={detail.imdrf_annex_e_label} annex="E" />
                            )}
                          </div>
                        </div>
                      )}

                      {/* Decision */}
                      <div className="mt-4 border-t border-slate-200 pt-4">
                        <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-slate-500">Human decision (required)</p>
                        <input
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="reviewer@company.com"
                          className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                        <textarea
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          placeholder="Reviewer notes (stored in audit trail)…"
                          rows={2}
                          className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                        {showOverride && (
                          <select
                            value={overrideCat}
                            onChange={(e) => setOverrideCat(e.target.value)}
                            className="mb-2 w-full rounded-lg border border-purple-300 bg-purple-50 px-3 py-2 text-sm font-semibold"
                          >
                            {CATEGORIES.map((c) => (
                              <option key={c} value={c}>
                                Override to: {c}
                              </option>
                            ))}
                          </select>
                        )}
                        <div className="flex gap-2">
                          <button
                            disabled={saving}
                            onClick={() => submitReview("APPROVED")}
                            className="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                          >
                            ✓ Approve
                          </button>
                          <button
                            disabled={saving}
                            onClick={() => submitReview("REJECTED")}
                            className="flex-1 rounded-lg bg-slate-200 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-300 disabled:opacity-50"
                          >
                            ✕ Reject
                          </button>
                          {showOverride ? (
                            <button
                              disabled={saving}
                              onClick={() => submitReview("MODIFIED")}
                              className="flex-1 rounded-lg bg-purple-600 px-3 py-2 text-sm font-bold text-white hover:bg-purple-700 disabled:opacity-50"
                            >
                              Confirm override
                            </button>
                          ) : (
                            <button
                              onClick={() => setShowOverride(true)}
                              className="flex-1 rounded-lg border-2 border-purple-600 px-3 py-2 text-sm font-bold text-purple-700 hover:bg-purple-50"
                            >
                              ⇄ Override
                            </button>
                          )}
                        </div>
                        <p className="mt-2 font-mono text-[11px] text-slate-400">
                          model: {detail.ai_model_version} · decision-support only (EU AI Act non-high-risk)
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Bottom: audit drawer */}
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                    <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Audit trail — this finding ({audit.length} events)
                    </h3>
                    <AuditTrail entries={audit} />
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        VigInfo AI MVP · Human-in-the-loop decision support for EU MDR Art. 61 &amp; 83–90 · IMDRF-coded · Audit-trailed
      </footer>
    </div>
  );
}
