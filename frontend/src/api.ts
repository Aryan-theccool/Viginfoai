import type { AuditEntry, Finding, FindingDetail, Review, Stats } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string; engine: string }>("/api/health"),
  stats: () => req<Stats>("/api/stats"),
  findings: (status?: string) =>
    req<Finding[]>(`/api/findings${status ? `?status=${status}` : ""}`),
  finding: (id: string) => req<FindingDetail>(`/api/findings/${id}`),
  reanalyze: (id: string) => req<Finding>(`/api/findings/${id}/reanalyze`, { method: "POST" }),
  submitReview: (body: {
    finding_id: string;
    reviewer_email: string;
    status: string;
    override_category?: string;
    reviewer_notes?: string;
  }) => req<Review>("/api/reviews", { method: "POST", body: JSON.stringify(body) }),
  audit: (finding_id?: string) =>
    req<AuditEntry[]>(finding_id ? `/api/audit?finding_id=${finding_id}` : "/api/audit?limit=200"),
  ingestPubmed: (query: string, max_results: number) =>
    req<{ records_created: number; findings_created: number; engine: string }>("/api/ingest/pubmed", {
      method: "POST",
      body: JSON.stringify({ query, max_results }),
    }),
  ingestMaude: (device_name: string, limit: number) =>
    req<{ records_created: number; findings_created: number; engine: string }>("/api/ingest/maude", {
      method: "POST",
      body: JSON.stringify({ device_name, limit }),
    }),
  ingestManual: (title: string, text: string, source_type: string) =>
    req<{ records_created: number; findings_created: number; engine: string }>("/api/ingest/manual", {
      method: "POST",
      body: JSON.stringify({ title, text, source_type }),
    }),
};
