"""Tests for the explainable heuristic engine (offline, deterministic)."""
from app.services.ai_engine import heuristic_extract


def test_safety_signal_with_imdrf_coding():
    text = (
        "During post-market surveillance of the Alaris infusion pump, 3 cases of over-infusion "
        "were reported due to software logic errors in flow rate calculation. One patient experienced "
        "transient hypotension requiring IV fluids."
    )
    result = heuristic_extract(text)
    assert result.category == "Safety Signal"
    assert result.exact_quote in text  # verbatim quote guarantee
    assert result.imdrf_coding is not None
    assert result.imdrf_coding.annex_a_code == "A0501"
    assert result.imdrf_coding.annex_e_code == "E0102"
    assert "83" in result.relevance_rationale  # cites PMS articles
    assert 0.0 <= result.confidence_score <= 1.0


def test_clinical_performance():
    text = (
        "In this randomized trial of 200 patients, the device demonstrated 98% sensitivity and "
        "significantly improved clinical outcomes compared with standard care (p < 0.001)."
    )
    result = heuristic_extract(text)
    assert result.category == "Clinical Performance"
    assert result.exact_quote in text
    assert "61" in result.relevance_rationale  # cites Art. 61


def test_risk_category():
    text = "The labeling warns that prolonged use may cause skin irritation and should be monitored as a potential hazard."
    result = heuristic_extract(text)
    assert result.category == "Risk"
    assert result.exact_quote in text


def test_irrelevant():
    text = "This paper reviews hospital cafeteria nutrition policies and staff satisfaction surveys from 2019."
    result = heuristic_extract(text)
    assert result.category == "Irrelevant"
    assert result.imdrf_coding is None


def test_empty_text_is_irrelevant():
    result = heuristic_extract("")
    assert result.category == "Irrelevant"
    assert result.confidence_score == 0.0
