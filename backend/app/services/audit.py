"""Append-only audit ledger helpers (EU MDR / 21 CFR Part 11 spirit).

The audit_trail table is never updated or deleted by application code —
PostgreSQL deployments additionally enforce this with a trigger (schema.sql).
"""
from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEntry

ACTOR_SYSTEM = "system-ai"


def log_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    payload: dict[str, Any] | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        payload=payload or {},
    )
    db.add(entry)
    db.flush()
    return entry
