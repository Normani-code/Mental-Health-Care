from typing import Tuple, Optional
from backend.schemas import Patient, PatientStatus, RiskLevel, StateTransitionRequest

class ClinicalStateTransitionError(Exception):
    def __init__(self, message: str, is_overrideable: bool = True):
        super().__init__(message)
        self.is_overrideable = is_overrideable

VALID_TRANSITIONS = {
    PatientStatus.INTAKE: {PatientStatus.EVALUATION, PatientStatus.CRISIS},
    PatientStatus.EVALUATION: {PatientStatus.TREATMENT_PLANNING, PatientStatus.CRISIS},
    PatientStatus.TREATMENT_PLANNING: {PatientStatus.ACTIVE_THERAPY, PatientStatus.CRISIS, PatientStatus.EVALUATION},
    PatientStatus.ACTIVE_THERAPY: {PatientStatus.DISCHARGED, PatientStatus.CRISIS, PatientStatus.TREATMENT_PLANNING},
    PatientStatus.CRISIS: {PatientStatus.ACTIVE_THERAPY, PatientStatus.TREATMENT_PLANNING, PatientStatus.EVALUATION},
    PatientStatus.DISCHARGED: {PatientStatus.INTAKE}
}

def validate_transition(patient: Patient, request: StateTransitionRequest) -> Tuple[bool, Optional[str]]:
    """
    Validates a state transition based on clinical rules (invariants).
    Returns (success, error_message).
    """
    current = patient.current_state
    target = request.target_state
    
    # Rule 1: Validate transition matrix (standard path check)
    allowed_targets = VALID_TRANSITIONS.get(current, set())
    if target not in allowed_targets:
        msg = f"El flujo clínico estándar no permite la transición directa de '{current.value}' a '{target.value}'."
        if not request.override:
            raise ClinicalStateTransitionError(msg + " Requiere autorización médica (override) con justificación explícita.", is_overrideable=True)
    
    # Rule 2: Risk-level invariants
    if patient.risk_level == RiskLevel.CRITICAL and target != PatientStatus.CRISIS:
        msg = f"El paciente tiene estado de riesgo CRÍTICO. El Alta o Terapia estándar está bloqueada. El paciente debe estar en Intervención de Crisis."
        if not request.override:
            raise ClinicalStateTransitionError(msg + " No se puede omitir el control clínico crítico sin autorización médica de emergencia.", is_overrideable=True)
            
    # Rule 3: Discharge criteria
    if target == PatientStatus.DISCHARGED:
        if patient.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            msg = f"No se puede dar de alta a un paciente con nivel de riesgo '{patient.risk_level.value}'."
            if not request.override:
                raise ClinicalStateTransitionError(msg + " Clínicamente inseguro. Requiere firma del médico (override).", is_overrideable=True)
        
        # Check if patient has conditions without any treatment plan
        if current == PatientStatus.INTAKE or current == PatientStatus.EVALUATION:
            msg = "No se puede dar de alta a un paciente directamente desde Admisión o Evaluación sin un plan de tratamiento registrado."
            raise ClinicalStateTransitionError(msg, is_overrideable=False) # Strictly not allowed!

    return True, None
