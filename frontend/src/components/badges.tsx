const CATEGORY_STYLES: Record<string, string> = {
  "Safety Signal": "bg-red-100 text-red-800 border-red-300",
  "Clinical Performance": "bg-emerald-100 text-emerald-800 border-emerald-300",
  Risk: "bg-orange-100 text-orange-800 border-orange-300",
  Irrelevant: "bg-slate-200 text-slate-600 border-slate-300",
};

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800 border-yellow-300",
  APPROVED: "bg-green-100 text-green-800 border-green-300",
  REJECTED: "bg-slate-200 text-slate-600 border-slate-300",
  MODIFIED: "bg-purple-100 text-purple-800 border-purple-300",
};

export function CategoryBadge({ category }: { category: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
        CATEGORY_STYLES[category] ?? "bg-slate-100 text-slate-700 border-slate-300"
      }`}
    >
      {category}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700 border-slate-300"
      }`}
    >
      {status}
    </span>
  );
}

export function ConfidenceBar({ value }: { value?: number | null }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-28 rounded-full bg-slate-200 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600">{pct}%</span>
    </div>
  );
}

export function ImdrfBadge({ code, label, annex }: { code: string; label?: string | null; annex: "A" | "E" }) {
  const style = annex === "A" ? "bg-indigo-100 text-indigo-800 border-indigo-300" : "bg-cyan-100 text-cyan-800 border-cyan-300";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs ${style}`} title={label ?? code}>
      <span className="font-mono font-bold">
        {annex === "A" ? "Annex A" : "Annex E"}: {code}
      </span>
      {label && <span className="font-medium opacity-80">— {label}</span>}
    </span>
  );
}
