import os
import sys
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.schemas import (
    Patient, PatientStatus, RiskLevel, ClinicalCondition,
    StateTransitionRequest, AuditEventType, HL7IngestionRequest,
    FHIRIngestionRequest, AgentExecutionTrace
)
from backend.state_machine import validate_transition, ClinicalStateTransitionError
from backend.audit_logger import log_audit_event, get_audit_logs
from backend.llm_agent import run_agent_coworker
from backend.interop import parse_hl7_message, transform_hl7_to_fhir
from backend.pdf_generator import generate_clinical_html_report, generate_clinical_pdf, REPORTLAB_AVAILABLE

app = FastAPI(
    title="Antigravity Health Psychiatric Platform",
    description="HIPAA compliant clinical state machine & LLM agent coworker simulation"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Patient Database for simulation
PATIENTS_DB: Dict[str, Patient] = {
    "PAT-001": Patient(
        id="PAT-001",
        name="John Doe",
        birthdate="1985-05-12",
        gender="male",
        current_state=PatientStatus.INTAKE,
        risk_level=RiskLevel.MEDIUM,
        conditions=[
            ClinicalCondition(code="F32.9", display="Trastorno Depresivo Mayor, No Especificado", severity="Medio", onset_date="2026-01-10")
        ],
        assigned_clinician="Dr. Evelyn Harper"
    ),
    "PAT-002": Patient(
        id="PAT-002",
        name="Sarah Connor",
        birthdate="1970-11-20",
        gender="female",
        current_state=PatientStatus.EVALUATION,
        risk_level=RiskLevel.HIGH,
        conditions=[
            ClinicalCondition(code="F31.9", display="Trastorno Bipolar, No Especificado", severity="Alto", onset_date="2025-11-05")
        ],
        assigned_clinician="Dr. Evelyn Harper"
    ),
    "PAT-003": Patient(
        id="PAT-003",
        name="Michael Vance",
        birthdate="1992-03-04",
        gender="male",
        current_state=PatientStatus.CRISIS,
        risk_level=RiskLevel.CRITICAL,
        conditions=[
            ClinicalCondition(code="F43.21", display="Trastorno de Adaptación con Estado de Ánimo Deprimido", severity="Crítico", onset_date="2026-05-20")
        ],
        assigned_clinician="Dr. Marcus Aurelius"
    )
}

# Serve Frontend static assets path
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/api/patients", response_model=List[Patient])
def get_patients():
    """
    Retrieves all patients. This counts as PHI access and is audited.
    """
    # For simulation, we log PHI access to patients summary
    log_audit_event(
        event_type=AuditEventType.PHI_ACCESS,
        patient_id="ALL",
        patient_name="Multiple Records",
        operator="Clinician-Dashboard",
        description="Accedió al panel principal de clínico (lista de estados de pacientes)."
    )
    return list(PATIENTS_DB.values())

@app.get("/api/patients/{patient_id}", response_model=Patient)
def get_patient(patient_id: str):
    """
    Retrieve single patient details. Audited for PHI access.
    """
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Registro de paciente no encontrado")
    
    patient = PATIENTS_DB[patient_id]
    log_audit_event(
        event_type=AuditEventType.PHI_ACCESS,
        patient_id=patient.id,
        patient_name=patient.name,
        operator="Clinician-Dashboard",
        description=f"Accedió al historial de salud detallado del paciente."
    )
    return patient

@app.post("/api/patients/transition")
def transition_patient(request: StateTransitionRequest):
    """
    Triggers a state transition. Runs clinical validation.
    Supports overrides (records human override logs).
    """
    patient_id = request.patient_id
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Registro de paciente no encontrado")
        
    patient = PATIENTS_DB[patient_id]
    old_state = patient.current_state
    
    try:
        validate_transition(patient, request)
    except ClinicalStateTransitionError as e:
        # Check if error is block or overrideable
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(e),
                "is_overrideable": e.is_overrideable
            }
        )

    # Perform transition
    patient.current_state = request.target_state
    patient.last_updated = datetime.now()
    
    # Log transition audit event
    event_type = AuditEventType.STATE_TRANSITION
    description = f"Paciente transicionado de '{old_state.value}' a '{request.target_state.value}'."
    
    if request.override:
        event_type = AuditEventType.HUMAN_OVERRIDE
        description += f" [AUTORIZACIÓN MÉDICA ACTIVADA] Razón: {request.reason}"
        
    log_audit_event(
        event_type=event_type,
        patient_id=patient.id,
        patient_name=patient.name,
        operator=request.operator,
        description=description,
        payload_snapshot={"old_state": old_state, "new_state": request.target_state, "reason": request.reason}
    )
    
    return {"status": "success", "patient": patient}

@app.post("/api/patients/{patient_id}/agent-evaluate", response_model=AgentExecutionTrace)
def agent_evaluate_patient(patient_id: str, trigger_payload: Dict[str, str]):
    """
    Invokes the AI coworker simulation loop on a patient.
    """
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Registro de paciente no encontrado")
        
    patient = PATIENTS_DB[patient_id]
    note = trigger_payload.get("note", "Evaluación estándar activada por el sistema.")
    
    # Runs simulated AI agent coworker
    trace = run_agent_coworker(patient, note)
    return trace

@app.post("/api/interop/hl7")
def ingest_hl7(request: HL7IngestionRequest):
    """
    Ingests raw HL7, parses PID and OBX segments, converts to FHIR,
    and updates/creates simulated patient records.
    """
    try:
        parsed = parse_hl7_message(request.raw_message)
        fhir_patient, conditions = transform_hl7_to_fhir(parsed)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fallo al analizar HL7: {str(e)}")

    p_id = fhir_patient["id"]
    if p_id == "UNKNOWN":
        p_id = f"PAT-{len(PATIENTS_DB) + 1:03d}"
        
    # Check if existing patient or create new
    if p_id in PATIENTS_DB:
        patient = PATIENTS_DB[p_id]
        patient.conditions.extend([c for c in conditions if c.code not in [existing.code for existing in patient.conditions]])
        patient.last_updated = datetime.now()
        action_msg = f"Condiciones clínicas actualizadas desde ingesta HL7."
    else:
        patient = Patient(
            id=p_id,
            name=fhir_patient["name"][0]["text"],
            birthdate=fhir_patient["birthDate"] or "1990-01-01",
            gender=fhir_patient["gender"],
            current_state=PatientStatus.INTAKE,
            risk_level=RiskLevel.MEDIUM,
            conditions=conditions,
            assigned_clinician="Dr. Ingestion AI"
        )
        PATIENTS_DB[p_id] = patient
        action_msg = f"Nuevo registro de paciente creado desde ingesta HL7."

    log_audit_event(
        event_type=AuditEventType.INGESTION,
        patient_id=patient.id,
        patient_name=patient.name,
        operator="HL7-Pipeline",
        description=action_msg,
        payload_snapshot={"raw_hl7": request.raw_message, "transformed_fhir_patient": fhir_patient}
    )

    return {"status": "success", "patient": patient}

@app.get("/api/audit-logs", response_model=List[Any])
def fetch_audit_logs(patient_id: Optional[str] = None):
    """
    Returns audit trail records for compliance visualization.
    """
    return get_audit_logs(patient_id)

@app.get("/api/patients/{patient_id}/export")
def export_summary(
    patient_id: str, 
    format: str = "html", 
    notes: Optional[str] = None,
    pending_state: Optional[str] = None
):
    """
    Capa de exportación regulatoria. Genera un resumen clínico de cuidado en PDF o HTML.
    """
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Registro de paciente no encontrado")
        
    patient = PATIENTS_DB[patient_id]
    audit_len = len(get_audit_logs(patient_id))
    
    # Audit this access specifically as regulatory export
    log_audit_event(
        event_type=AuditEventType.PHI_ACCESS,
        patient_id=patient.id,
        patient_name=patient.name,
        operator="EHR-Exporter",
        description=f"Resumen de cuidado regulatorio exportado en formato {format.upper()}."
    )

    if format == "pdf":
        temp_pdf_path = os.path.join(os.path.dirname(__file__), "..", f"clinical_report_{patient_id}.pdf")
        generate_clinical_pdf(patient.dict(), temp_pdf_path, notes, pending_state)
        
        if REPORTLAB_AVAILABLE:
            response = FileResponse(
                temp_pdf_path, 
                media_type="application/pdf", 
                filename=f"clinical_report_{patient_id}.pdf"
            )
            # Remove the file asynchronously or leave for cache
            return response
        else:
            # ReportLab not installed; returning HTML format as PDF backup
            # We state this in header
            return Response(
                content=generate_clinical_html_report(patient.dict(), audit_len, notes, pending_state),
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=clinical_report_{patient_id}.html"}
            )
    else:
        html_str = generate_clinical_html_report(patient.dict(), audit_len, notes, pending_state)
        return HTMLResponse(content=html_str)

# Serve static files for frontend dashboard if folder exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
else:
    @app.get("/")
    def index_fallback():
        return HTMLResponse(
            content="<h2>Servidor backend ejecutándose correctamente. Carpeta 'frontend' no encontrada.</h2>"
        )
