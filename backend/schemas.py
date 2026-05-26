from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PatientStatus(str, Enum):
    INTAKE = "Admisión"
    EVALUATION = "Evaluación Clínica"
    TREATMENT_PLANNING = "Planificación de Tratamiento"
    ACTIVE_THERAPY = "Terapia Activa"
    CRISIS = "Intervención de Crisis"
    DISCHARGED = "Alta Médica"

class RiskLevel(str, Enum):
    LOW = "Bajo"
    MEDIUM = "Medio"
    HIGH = "Alto"
    CRITICAL = "Crítico"

class ClinicalCondition(BaseModel):
    code: str
    display: str
    severity: str
    onset_date: str

class Patient(BaseModel):
    id: str
    name: str
    birthdate: str
    gender: str
    current_state: PatientStatus
    risk_level: RiskLevel
    conditions: List[ClinicalCondition] = []
    assigned_clinician: str
    last_updated: datetime = Field(default_factory=datetime.now)

class StateTransitionRequest(BaseModel):
    patient_id: str
    target_state: PatientStatus
    operator: str  # e.g., "Dr. Smith" or "Agent-01"
    reason: str
    override: bool = False

class AuditEventType(str, Enum):
    PHI_ACCESS = "PHI_ACCESS"
    AGENT_ACTION = "AGENT_ACTION"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"
    INGESTION = "INGESTION"
    STATE_TRANSITION = "STATE_TRANSITION"

class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: AuditEventType
    patient_id: str
    patient_name: str
    operator: str
    description: str
    payload_snapshot: Optional[Dict[str, Any]] = None  # To demonstrate data tracking

class HL7IngestionRequest(BaseModel):
    raw_message: str

class FHIRIngestionRequest(BaseModel):
    resource_type: str
    resource_data: Dict[str, Any]

class AgentAction(BaseModel):
    tool_name: str
    tool_input: str
    tool_output: str
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentExecutionTrace(BaseModel):
    agent_id: str
    patient_id: str
    prompt_context: str
    steps: List[AgentAction] = []
    final_decision: str
    safety_checks_passed: bool
    retries_count: int
    memory_context_used: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)
