import time
from typing import List, Dict, Any
from backend.schemas import AgentExecutionTrace, AgentAction, Patient, PatientStatus, RiskLevel
from backend.audit_logger import log_audit_event, AuditEventType

def run_agent_coworker(patient: Patient, trigger_note: str) -> AgentExecutionTrace:
    """
    Simulates a production LLM agent coworker evaluating a patient's psychiatric event.
    Features:
      - Memory context loading.
      - Tool executions (FHIR fetch, clinical standards lookup).
      - Multi-step reasoning loops.
      - Safety guardrails verification.
      - Auto-retry upon safety failure.
      - Full execution tracing.
    """
    agent_id = "psych-helper-agent-v1"
    steps: List[AgentAction] = []
    
    # 1. Cargar contexto de memoria
    memory_context = [
        "Paciente diagnosticado anteriormente con Trastorno Depresivo Mayor (TDM).",
        "Última nota clínica (hace 2 semanas): El paciente expresó insomnio leve, negó ideación suicida activa."
    ]
    
    # Simular retraso de procesamiento del agente
    time.sleep(0.1)
    
    # Paso 1: Consultar base de datos FHIR usando herramienta
    steps.append(AgentAction(
        tool_name="QueryFHIRDatabase",
        tool_input=f"patient_id={patient.id}, resource=Observation",
        tool_output=f"Se encontró código activo de TDM y 3 observaciones recientes que indican incremento de ansiedad. Nivel de riesgo = {patient.risk_level.value}."
    ))
    
    # Registrar acceso a PHI por parte del agente
    log_audit_event(
        event_type=AuditEventType.PHI_ACCESS,
        patient_id=patient.id,
        patient_name=patient.name,
        operator=agent_id,
        description=f"El Agente consultó observaciones clínicas usando la herramienta QueryFHIRDatabase."
    )
    
    # Paso 2: Consultar protocolos de guías clínicas
    steps.append(AgentAction(
        tool_name="ClinicalProtocolsGuide",
        tool_input="symptom='ansiedad severa + aumento de riesgo'",
        tool_output="Coincidencia de guía: Recomendar escalado a 'Evaluación Clínica' o 'Intervención de Crisis' según estado de riesgo."
    ))
    
    # Paso 3: Ejecutar evaluación de IA y controles de seguridad (safety rails)
    retries = 0
    safety_passed = False
    final_decision = ""
    
    # Simulación de un bucle de reintento si falla el control de seguridad
    if patient.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] and "crisis" not in trigger_note.lower():
        retries += 1
        steps.append(AgentAction(
            tool_name="EvaluateRiskLevel",
            tool_input="Borrador de recomendación: Programar cita de seguimiento de rutina en 30 días.",
            tool_output="SAFETY_RAIL_FAILED: El nivel de riesgo del paciente es alto. Programar rutina no es seguro. Se requiere reintento correctivo."
        ))
        
        # El agente aprende del error, recupera la política de seguridad de la memoria
        time.sleep(0.1)
        steps.append(AgentAction(
            tool_name="EvaluateRiskLevel",
            tool_input="Borrador actualizado: Transicionar al paciente inmediatamente a 'Intervención de Crisis' y notificar al supervisor.",
            tool_output="SAFETY_RAIL_PASSED: Protocolo de emergencia invocado con éxito."
        ))
        safety_passed = True
        final_decision = "Escalar estado a 'Intervención de Crisis' y marcar al paciente para llamada inmediata del médico de guardia."
    else:
        # Flujo estándar
        steps.append(AgentAction(
            tool_name="EvaluateRiskLevel",
            tool_input=f"Borrador de recomendación basado en: {trigger_note}",
            tool_output="SAFETY_RAIL_PASSED: La propuesta se encuentra dentro de los límites operativos seguros."
        ))
        safety_passed = True
        if patient.current_state == PatientStatus.INTAKE:
            final_decision = "Transicionar al paciente a 'Evaluación Clínica' para diagnóstico de admisión completo."
        elif patient.current_state == PatientStatus.EVALUATION:
            final_decision = "Desarrollar un plan de tratamiento estándar de terapia cognitivo-conductual (Planificación de Tratamiento)."
        else:
            final_decision = f"Mantener estado '{patient.current_state.value}' y actualizar las notas de la sesión con el mensaje recibido."

    # Registrar la recomendación final del agente en la bitácora de auditoría
    log_audit_event(
        event_type=AuditEventType.AGENT_ACTION,
        patient_id=patient.id,
        patient_name=patient.name,
        operator=agent_id,
        description=f"El Agente completó la simulación. Recomendación: {final_decision}"
    )

    trace = AgentExecutionTrace(
        agent_id=agent_id,
        patient_id=patient.id,
        prompt_context=trigger_note,
        steps=steps,
        final_decision=final_decision,
        safety_checks_passed=safety_passed,
        retries_count=retries,
        memory_context_used=memory_context
    )
    
    return trace
