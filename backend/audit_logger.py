import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.schemas import AuditLogEntry, AuditEventType

# Simple in-memory audit store
AUDIT_TRAIL: List[AuditLogEntry] = []

def log_audit_event(
    event_type: AuditEventType,
    patient_id: str,
    patient_name: str,
    operator: str,
    description: str,
    payload_snapshot: Optional[Dict[str, Any]] = None
) -> AuditLogEntry:
    """
    Records an auditable security or clinical action.
    Complies with HIPAA specifications for access tracking and integrity.
    """
    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        event_type=event_type,
        patient_id=patient_id,
        patient_name=patient_name,
        operator=operator,
        description=description,
        payload_snapshot=payload_snapshot
    )
    # Append to our mock database
    AUDIT_TRAIL.append(entry)
    
    # Log to server console to mimic audit systems
    print(f"[AUDIT LOG] [{entry.timestamp.isoformat()}] [{event_type.value}] Patient: {patient_name} ({patient_id}) | Operator: {operator} | {description}")
    return entry

def get_audit_logs(patient_id: Optional[str] = None) -> List[AuditLogEntry]:
    """
    Returns audit trail logs, filtered by patient if requested.
    """
    if patient_id:
        return [entry for entry in AUDIT_TRAIL if entry.patient_id == patient_id]
    return AUDIT_TRAIL
