import type { AuditEntry } from "../types";

const ACTION_STYLES: Record<string, string> = {
  CREATE: "bg-slate-200 text-slate-700",
  AI_EXTRACT: "bg-indigo-100 text-indigo-800",
  AI_REANALYZE: "bg-indigo-100 text-indigo-800",
  REVIEW_SUBMIT: "bg-green-100 text-green-800",
  REVIEW_OVERRIDE: "bg-purple-100 text-purple-800",
};

function fmt(ts?: string) {
  if (!ts) return "—";
  const d = new Date(ts.endsWith("Z") ? ts : ts + "Z");
  return d.toLocaleString();
}

export function AuditTrail({ entries, compact }: { entries: AuditEntry[]; compact?: boolean }) {
  if (!entries.length) return <p className="text-sm text-slate-500">No audit events yet.</p>;
  return (
    <ol className="space-y-2">
      {entries.map((e) => (
        <li key={e.audit_id} className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2">
          <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-bold ${ACTION_STYLES[e.action] ?? "bg-slate-100 text-slate-600"}`}>
            {e.action}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
              <span className="font-semibold text-slate-700">{e.actor}</span>
              <span>·</span>
              <span>{e.entity_type}/{String(e.entity_id).slice(0, 8)}</span>
              <span>·</span>
              <span className="font-mono">{fmt(e.timestamp)}</span>
            </div>
            {!compact && (
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] text-slate-600">
                {JSON.stringify(e.payload, null, 1)}
              </pre>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
