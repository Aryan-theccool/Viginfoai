# VigInfo AI — 90-Second Demo Script (Loom)

## 0:00–0:10 — Hook
> "Notified Bodies reject CERs for one reason above all: untraceable literature evidence.
> VigInfo AI is the system of record that fixes it — every AI claim linked to an exact source quote,
> IMDRF-coded, and human-approved with a full audit trail."

## 0:10–0:35 — Live ingestion (MAUDE)
1. Open the **Ingest** tab → FDA MAUDE → device `infusion pump` → Fetch.
2. Narrate: "Live adverse-event records from openFDA, each auto-analyzed on arrival —
   no black box: category, verbatim quote, confidence, and IMDRF Annex A/E suggestions."

## 0:35–1:05 — Review workspace (the money shot)
1. Open the **Review workspace** → click the new Safety Signal finding.
2. Point at the **highlighted quote** in the source record (left) matching the AI card (right).
3. Read the plain-language rationale; point at IMDRF badges (e.g. A0501 software, E0102 hypotension).
4. Enter reviewer email → **Approve**. Show the status flip and the toast.

## 1:05–1:25 — Audit trail
1. Scroll to the audit drawer: CREATE → AI_EXTRACT → REVIEW_SUBMIT, timestamped, actor-stamped.
2. Narrate: "EU MDR Articles 61 and 83–90, MEDDEV 2.7/1 appraisal workflow, 21 CFR Part 11-style
   append-only ledger. Decision-support only — non-high-risk under the EU AI Act."

## 1:25–1:30 — Close
> "That was real FDA data to audit-ready evidence in under a minute. Happy to walk through
> the CER/PSUR export next."

---

## Backup one-liners (if live API is slow)
- Pre-seeded demo data (infusion pump + glucose monitor) loads instantly — use the queue.
- `POST /api/ingest/manual` accepts pasted PDF text for offline demos.
- `GET /docs` shows the full OpenAPI spec for technical reviewers.
