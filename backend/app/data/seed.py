"""Demo seed data — realistic infusion-pump & glucose-monitor evidence.

Run on first startup (AUTO_SEED=true) so the review UI is populated
immediately. Idempotent: skips seeding when records already exist.
"""
from sqlalchemy.orm import Session

from ..models import SourceRecord
from ..services.pipeline import store_record_with_analysis

SEED_RECORDS: list[dict] = [
    {
        "source_type": "FDA MAUDE",
        "external_id": "MW5098214",
        "title": "MDR Report: Alaris Infusion Pump — Over-infusion event",
        "text": (
            "During post-market surveillance of the Alaris infusion pump, 3 cases of over-infusion "
            "were reported due to software logic errors in flow rate calculation. One patient experienced "
            "transient hypotension requiring IV fluids and prolonged hospitalization for observation. "
            "The manufacturer investigation confirmed a software defect in the dose calculation module. "
            "No death was reported."
        ),
        "metadata": {"event_type": "Injury", "manufacturer": "Becton Dickinson", "device_name": "Infusion Pump"},
    },
    {
        "source_type": "PubMed",
        "external_id": "38491025",
        "title": "Continuous glucose monitoring accuracy in adults with type 1 diabetes: a randomized crossover trial",
        "text": (
            "In this randomized crossover trial of 142 adults with type 1 diabetes, the continuous glucose "
            "monitor demonstrated a mean absolute relative difference of 9.1% compared with reference venous "
            "glucose. Time in range (70-180 mg/dL) improved from 58% to 71% (p < 0.001), with no serious "
            "adverse events attributable to the device. These results support the clinical performance and "
            "safety of the system for routine glycemic management."
        ),
        "metadata": {"publication_year": "2024", "journal": "Diabetes Technology & Therapeutics",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/38491025/"},
    },
    {
        "source_type": "FDA MAUDE",
        "external_id": "MW5112007",
        "title": "MDR Report: Glucose Monitor — False low readings",
        "text": (
            "The patient received repeated false low glucose readings from the continuous glucose monitor "
            "sensor, showing 55 mg/dL while confirmatory fingerstick readings were 148-165 mg/dL. Relying on "
            "the erroneous sensor data, the patient consumed fast-acting carbohydrates and subsequently "
            "experienced hyperglycemia requiring correction insulin. The sensor was replaced and the issue "
            "did not recur. Investigation points to possible sensor drift and inaccurate measurement."
        ),
        "metadata": {"event_type": "Malfunction", "manufacturer": "Example Devices Inc", "device_name": "Glucose Monitor"},
    },
    {
        "source_type": "PubMed",
        "external_id": "37665512",
        "title": "Alarm fatigue and infusion pump safety in intensive care units: prospective cohort",
        "text": (
            "In a prospective cohort across 6 intensive care units, infusion pumps generated a median of 41 "
            "alarms per patient-day, of which 72% required no clinical intervention. In two cases, critical "
            "occlusion alarms were missed during high-workload periods, delaying therapy by up to 40 minutes. "
            "One patient experienced transient hypertension. The authors warn that alarm fatigue remains a "
            "significant hazard and recommend human-factors redesign of alarm prioritization."
        ),
        "metadata": {"publication_year": "2023", "journal": "Journal of Patient Safety",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/37665512/"},
    },
    {
        "source_type": "FDA MAUDE",
        "external_id": "MW5088331",
        "title": "MDR Report: Infusion Pump — Battery failure, therapy interruption",
        "text": (
            "The infusion pump unexpectedly shut down during ambulatory use due to battery failure, "
            "interrupting delivery of vasoactive medication for approximately 25 minutes. The device failed "
            "to sound a low-battery alarm before shutting down. The patient was transferred to backup therapy "
            "with no lasting harm reported. The battery pack was 14 months old, beyond the recommended "
            "replacement interval, though the labeling regarding battery life was described as unclear."
        ),
        "metadata": {"event_type": "Malfunction", "manufacturer": "Example Devices Inc", "device_name": "Infusion Pump"},
    },
    {
        "source_type": "PubMed",
        "external_id": "37990041",
        "title": "Machine-learning triage for dermatology referrals: retrospective validation",
        "text": (
            "We retrospectively validated a machine-learning triage model for dermatology referrals using "
            "12,000 annotated cases from primary care. The model achieved an AUC of 0.91 for prioritizing "
            "urgent referrals. This study concerns a software-only triage aid unrelated to infusion pumps or "
            "glucose monitors and contains no device-specific safety or performance outcomes relevant to the "
            "current clinical evaluation scope."
        ),
        "metadata": {"publication_year": "2023", "journal": "NPJ Digital Medicine",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/37990041/"},
    },
]


def seed_demo_data(db: Session) -> int:
    """Insert demo records (with AI analysis) if the database is empty."""
    if db.query(SourceRecord).count() > 0:
        return 0
    count = 0
    for item in SEED_RECORDS:
        store_record_with_analysis(
            db,
            source_type=item["source_type"],
            external_id=item["external_id"],
            title=item["title"],
            text=item["text"],
            metadata=item["metadata"],
        )
        count += 1
    return count
