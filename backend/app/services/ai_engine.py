"""Explainable AI Signal & Evidence Engine.

Never a black box: every extraction returns a category, an EXACT source
quote, a plain-language rationale (auditor-friendly), a confidence score,
and IMDRF Annex A/E coding suggestions where applicable.

Two backends:
  1. OpenAI structured outputs (gpt-4o) when OPENAI_API_KEY is configured.
  2. Built-in explainable heuristic engine — deterministic, fully offline,
     ideal for demos and tests. Every decision is traceable to matched
     evidence phrases (no hidden weights).
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from ..config import get_settings

log = logging.getLogger(__name__)

ENGINE_VERSION_HEURISTIC = "viginfo-heuristic-v1"
CATEGORIES = ("Clinical Performance", "Safety Signal", "Risk", "Irrelevant")

SYSTEM_PROMPT = """You are an expert EU MDR (2017/745) Regulatory Affairs Auditor and Clinical Evaluator.
Analyze the provided text for medical device safety signals, clinical performance evidence, or risks.

Guidelines:
1. Always quote the source text EXACTLY. Never paraphrase quotes. The quote must be a verbatim substring.
2. Provide clear, plain-language rationales suitable for a Notified Body auditor. Reference EU MDR Art. 61
   (clinical evaluation) or Art. 83-90 (post-market surveillance / vigilance) where relevant.
3. If an adverse event or device failure is found, suggest IMDRF Annex A (Device Problem) and/or
   Annex E (Health Effect) codes. Mark them as suggestions for human confirmation.
4. Categories: exactly one of 'Clinical Performance', 'Safety Signal', 'Risk', 'Irrelevant'.
"""


class IMDRFCoding(BaseModel):
    annex_a_code: Optional[str] = Field(default=None, description="IMDRF Annex A device-problem code, e.g. A0501")
    annex_a_label: Optional[str] = Field(default=None, description="Plain-language label for the Annex A code")
    annex_e_code: Optional[str] = Field(default=None, description="IMDRF Annex E health-effect code, e.g. E0102")
    annex_e_label: Optional[str] = Field(default=None, description="Plain-language label for the Annex E code")


class EvidenceExtraction(BaseModel):
    category: str = Field(description="One of: 'Clinical Performance', 'Safety Signal', 'Risk', 'Irrelevant'")
    relevance_rationale: str = Field(description="Plain-language explanation referencing EU MDR Art. 61 or 83-90.")
    exact_quote: str = Field(description="Exact verbatim substring from the input text supporting this finding.")
    confidence_score: float = Field(description="Confidence between 0.0 and 1.0", ge=0.0, le=1.0)
    imdrf_coding: Optional[IMDRFCoding] = Field(default=None)
    matched_indicators: list[str] = Field(default_factory=list, description="Evidence phrases that drove the decision")


# ── Heuristic knowledge base ─────────────────────────────────────
# (keyword → IMDRF suggestion). Codes follow the IMDRF AE terminology
# structure: Annex A = Medical Device Problem, Annex E = Health Effect.
# These are *suggestions* — the human reviewer confirms or overrides.

ANNEX_A_PATTERNS: list[tuple[str, str, list[str]]] = [
    ("A0501", "Software problem / logic error", ["software", "algorithm", "firmware", "logic error", "calculation error", "programming error", "app crash", "update failure"]),
    ("A0601", "Infusion / delivery problem (over- or under-delivery)", ["over-infusion", "overinfusion", "under-infusion", "free flow", "flow rate", "over-delivery", "under-delivery", "bolus error"]),
    ("A0701", "Alarm / alert failure", ["alarm fail", "no alarm", "alarm did not sound", "missed alarm", "alarm fatigue", "silent alarm"]),
    ("A0801", "Mechanical failure / breakage", ["crack", "broke", "broken", "fracture", "leak", "occlusion", "kink", "dislodg", "detach", "separation", "rupture"]),
    ("A0901", "Electrical / power / battery problem", ["battery", "power loss", "shut down unexpectedly", "electrical", "short circuit", "failed to power", "charging"]),
    ("A1001", "Inaccurate measurement / sensing error", ["inaccurate", "false reading", "erroneous reading", "sensor error", "drift", "miscalibrat", "false positive", "false negative"]),
    ("A1101", "Use error / human-factors issue", ["use error", "user error", "misuse", "confusing interface", "mislabeled", "labeling", "instructions unclear"]),
    ("A1201", "Material / biocompatibility issue", ["biocompatib", "allergic", "irritation", "material degradation", "corrosion", "particulate", "contamination"]),
    ("A1301", "Sterility / infection-control failure", ["non-sterile", "unsterile", "sterilization fail", "contaminated", "infection control", "pyrogen"]),
    ("A1401", "Connectivity / cybersecurity issue", ["bluetooth", "wireless", "connectivity", "cybersecurity", "hacked", "data loss", "failed to transmit"]),
]

ANNEX_E_PATTERNS: list[tuple[str, str, list[str]]] = [
    ("E0101", "Death", ["death", "fatal", "patient died", "mortality"]),
    ("E0102", "Hypotension / blood pressure change", ["hypotension", "blood pressure drop", "hypertension"]),
    ("E0201", "Hypoglycemia / hyperglycemia", ["hypoglycemia", "hyperglycemia", "low blood sugar", "high blood sugar", "glucose excursion", "ketoacidosis"]),
    ("E0301", "Injury / trauma", ["injur", "trauma", "laceration", "burn", "bleeding", "hemorrhage", "hematoma"]),
    ("E0401", "Infection", ["infection", "sepsis", "septic", "abscess", "fever", "cellulitis"]),
    ("E0501", "Hospitalization / prolonged hospitalization", ["hospitaliz", "admitted", "readmission", "emergency department", "icu "]),
    ("E0601", "Therapeutic / surgical intervention required", ["intervention", "surgery", "required treatment", "iv fluids", "resuscitat", "intubat"]),
    ("E0701", "Pain / discomfort", ["pain", "discomfort", "nausea", "vomiting", "dizziness", "syncope", "faint"]),
    ("E0801", "Skin reaction", ["rash", "erythema", "dermatitis", "blister", "skin tear", "pressure ulcer"]),
    ("E0901", "No patient harm (near miss)", ["no harm", "no injury", "no adverse", "intercepted", "near miss", "no patient impact"]),
]

SAFETY_TRIGGERS = [
    "adverse event", "serious injury", "malfunction", "failure", "recall", "death", "injury",
    "over-infusion", "overinfusion", "under-infusion", "free flow", "hypotension", "hypertension",
    "hypoglycemia", "hyperglycemia", "alarm", "software", "defect", "complaint", "incident",
    "harm", "hospitaliz", "emergency", "unexpected", "faulty", "error", "erroneous",
    "inaccurate", "false reading", "false low", "false high", "bleeding", "hemorrhage",
    "sepsis", "shut down", "missed", "interrupted", "interrupting",
]
# Weak triggers only count when corroborated (they often just name the device
# type, e.g. "a software-only triage aid", or appear in benign contexts).
WEAK_TRIGGERS = frozenset({"software", "alarm", "error", "complaint", "incident"})

PERFORMANCE_TRIGGERS = [
    "efficacy", "effective", "accuracy", "sensitivity", "specificity", "clinical trial", "randomized",
    "cohort", "endpoint", "outcome", "survival", "success rate", "performance", "benefit", "improved",
    "compared", "statistically significant", "p <", "confidence interval", "auc", "time in range",
]
STRONG_PERF = frozenset({"randomized", "clinical trial", "sensitivity", "specificity", "endpoint",
                         "statistically significant", "p <", "confidence interval", "time in range", "cohort"})
RISK_TRIGGERS = [
    "risk", "hazard", "may cause", "could lead", "potential", "warning", "precaution",
    "contraindicat", "should be monitored", "requires further", "limitation", "concern",
]

# Safety/performance language under a negation ("no serious adverse events")
# must not escalate the finding.
NEGATIONS = ("no ", "not ", "without", "free of", "absence of", "never", "unrelated",
             "contains no", "no evidence", "ruled out", "denies", "none ")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def _find_code(
    sentences: list[str], patterns: list[tuple[str, str, list[str]]]
) -> tuple[Optional[tuple[str, str]], list[str]]:
    """Return best (code, label) match plus all matched indicator phrases.

    Sentence-aware with negation discounting: "No death was reported" must not
    code E0101 (Death). Keywords that are themselves negations (E0901 "no harm")
    are still allowed to match inside negated sentences.
    """
    best: Optional[tuple[str, str]] = None
    matched: list[str] = []
    best_hits = 0
    lowered = [s.lower() for s in sentences] or [""]
    for code, label, keywords in patterns:
        hits: list[str] = []
        for kw in keywords:
            inherently_negated = kw.startswith(("no ", "without", "free of", "absence of"))
            for sl in lowered:
                if kw not in sl:
                    continue
                negated = any(n in sl for n in NEGATIONS)
                if not negated or inherently_negated:
                    hits.append(kw)
                    break
        if hits:
            matched.extend(hits)
            if len(hits) > best_hits:
                best_hits = len(hits)
                best = (code, label)
    return best, matched


def heuristic_extract(text: str) -> EvidenceExtraction:
    """Deterministic, explainable extraction. No API keys, no randomness."""
    text = (text or "").strip()
    if not text:
        return EvidenceExtraction(
            category="Irrelevant",
            relevance_rationale="No text was provided, so there is no evidence to assess under EU MDR Article 61 or Articles 83–90.",
            exact_quote="",
            confidence_score=0.0,
        )

    text_lower = text.lower()
    sentences = _split_sentences(text)

    # Sentence-level matching with negation discounting: a trigger inside a
    # negated sentence ("no serious adverse events were observed") is dropped.
    def _hits(triggers: list[str]) -> list[str]:
        found: set[str] = set()
        for s in sentences:
            sl = s.lower()
            negated = any(n in sl for n in NEGATIONS)
            for t in triggers:
                if t in sl and not negated:
                    found.add(t)
        if not sentences:  # no sentence boundaries: fall back to whole-text match
            found.update(t for t in triggers if t in text_lower)
        return sorted(found)

    safety_hits = _hits(SAFETY_TRIGGERS)
    perf_hits = _hits(PERFORMANCE_TRIGGERS)
    risk_hits = _hits(RISK_TRIGGERS)

    annex_a, a_indicators = _find_code(sentences, ANNEX_A_PATTERNS)
    annex_e, e_indicators = _find_code(sentences, ANNEX_E_PATTERNS)

    # Annex A matched only on generic vocabulary (e.g. "software" merely naming
    # the device type) without corroborating problem language is noise — drop it.
    if annex_a and all(i in ("software",) for i in a_indicators):
        corroborated = any(
            t in text_lower
            for t in ("malfunction", "failure", "error", "defect", "bug", "fault",
                      "adverse", "recall", "harm", "injury", "unexpected")
        )
        if not corroborated:
            annex_a, a_indicators = None, []

    health_effect = annex_e is not None and annex_e[0] != "E0901"  # E0901 = explicit no-harm

    # Death / serious harm (non-negated) always escalates to a safety signal.
    severe = any(
        k in s.lower() and not any(n in s.lower() for n in NEGATIONS)
        for s in sentences
        for k in ("death", "fatal", "patient died", "serious injury", "life-threaten")
    )

    strong_safety = [h for h in safety_hits if h not in WEAK_TRIGGERS]
    # A lone weak trigger with no health effect and no corroboration is noise
    # (e.g. "software" in "a software-only triage aid").
    if safety_hits and not strong_safety and not health_effect and not severe:
        safety_hits = []

    strong_perf = [h for h in perf_hits if h in STRONG_PERF]
    perf_evidence = len(perf_hits) >= 2 or bool(strong_perf)

    if severe or strong_safety or health_effect:
        category = "Safety Signal"
    elif safety_hits and (annex_a or annex_e):
        category = "Safety Signal"
    elif safety_hits and not perf_evidence:
        category = "Safety Signal"
    elif perf_evidence and not safety_hits and not severe:
        category = "Clinical Performance"
    elif risk_hits and not safety_hits:
        category = "Risk"
    elif safety_hits:
        category = "Safety Signal"
    elif annex_a or annex_e:
        category = "Risk"  # device problem / health effect without a clear safety narrative
    else:
        category = "Irrelevant"

    # Best supporting sentence: the one with the most indicator coverage.
    indicators = safety_hits + perf_hits + risk_hits + a_indicators + e_indicators

    def _score(sentence: str) -> int:
        s = sentence.lower()
        return sum(1 for ind in set(indicators) if ind and ind in s)

    exact_quote = max(sentences, key=_score) if sentences else text[:500]
    if category == "Irrelevant":
        exact_quote = sentences[0][:500] if sentences else text[:500]

    imdrf = None
    if category in ("Safety Signal", "Risk") and (annex_a or annex_e):
        imdrf = IMDRFCoding(
            annex_a_code=annex_a[0] if annex_a else None,
            annex_a_label=annex_a[1] if annex_a else None,
            annex_e_code=annex_e[0] if annex_e else None,
            annex_e_label=annex_e[1] if annex_e else None,
        )

    rationale = _build_rationale(category, safety_hits, perf_hits, risk_hits, annex_a, annex_e)

    # Confidence: calibrated from independent evidence cues (transparent formula).
    if category == "Irrelevant":
        confidence = 0.85 if not indicators else 0.55
    else:
        cues = bool(safety_hits) + bool(perf_hits) + bool(risk_hits) + bool(annex_a) + bool(annex_e)
        confidence = min(0.95, 0.55 + 0.10 * cues + (0.10 if severe else 0.0))
        confidence = round(confidence, 2)

    return EvidenceExtraction(
        category=category,
        relevance_rationale=rationale,
        exact_quote=exact_quote,
        confidence_score=confidence,
        imdrf_coding=imdrf,
        matched_indicators=sorted(set(indicators))[:20],
    )


def _build_rationale(
    category: str,
    safety_hits: list[str],
    perf_hits: list[str],
    risk_hits: list[str],
    annex_a: Optional[tuple[str, str]],
    annex_e: Optional[tuple[str, str]],
) -> str:
    if category == "Safety Signal":
        device = f" The device problem suggests IMDRF Annex A {annex_a[0]} ({annex_a[1]})" if annex_a else ""
        health = f" The reported health effect suggests IMDRF Annex E {annex_e[0]} ({annex_e[1]})" if annex_e else ""
        cues = ", ".join(f"'{h}'" for h in safety_hits[:5]) or "adverse-event language"
        return (
            f"This text describes a potential device-related safety issue (indicators: {cues}).{device}{health} "
            "Under EU MDR Articles 83–90 it is reportable vigilance / post-market surveillance input, and under "
            "Article 61 it must feed the clinical evaluation as safety evidence. Recommend human confirmation of the IMDRF coding."
        )
    if category == "Clinical Performance":
        cues = ", ".join(f"'{h}'" for h in perf_hits[:5]) or "performance language"
        return (
            f"This text reports clinical performance or effectiveness evidence (indicators: {cues}). Under EU MDR "
            "Article 61 and Annex XIV it supports the Clinical Evaluation Report (CER) as evidence of safety and "
            "performance, subject to MEDDEV 2.7/1 appraisal of methodological quality."
        )
    if category == "Risk":
        cues = ", ".join(f"'{h}'" for h in risk_hits[:5]) or "risk language"
        return (
            f"This text flags a potential hazard or residual risk (indicators: {cues}) without a confirmed adverse event. "
            "Under EU MDR Annex I (risk management) and Articles 83–90 it should be tracked in PMS trending to detect "
            "emerging signals early."
        )
    perf = f" Performance terms ({', '.join(perf_hits[:3])}) appear but without device-specific outcomes." if perf_hits else ""
    return (
        "No device-specific safety, performance, or risk evidence was identified for clinical evaluation (Art. 61) "
        f"or vigilance (Art. 83–90).{perf} Safe to exclude from the CER/PMS evidence set, pending human review."
    )


# ── OpenAI backend ───────────────────────────────────────────────


def openai_extract(text: str, model: str) -> EvidenceExtraction:
    """Structured-output extraction via OpenAI (temperature 0 for auditability)."""
    from openai import OpenAI  # local import: optional dependency at runtime

    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this medical device text:\n\n{text}"},
        ],
        response_format=EvidenceExtraction,
        temperature=0.0,
    )
    parsed = response.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed output")
    if parsed.category not in CATEGORIES:
        parsed.category = "Irrelevant"
    return parsed


def extract_evidence(text: str) -> tuple[EvidenceExtraction, str]:
    """Run the configured engine. Returns (extraction, engine_version).

    Falls back to the heuristic engine if OpenAI is unconfigured or fails,
    so ingestion pipelines never break during a live demo.
    """
    settings = get_settings()
    if settings.use_openai:
        try:
            result = openai_extract(text, model=settings.OPENAI_MODEL)
            return result, f"openai-{settings.OPENAI_MODEL}"
        except Exception as exc:  # noqa: BLE001 — demo resilience by design
            log.warning("OpenAI extraction failed, using heuristic fallback: %s", exc)
    return heuristic_extract(text), ENGINE_VERSION_HEURISTIC


def current_engine_version() -> str:
    settings = get_settings()
    return f"openai-{settings.OPENAI_MODEL}" if settings.use_openai else ENGINE_VERSION_HEURISTIC
