import os
from typing import Dict, Any, Optional
from datetime import datetime

# Importación opcional para el compilador de PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def clean_status(val) -> str:
    if not val:
        return ""
    # If it is an Enum object, extract its value
    if hasattr(val, 'value'):
        val = val.value
    
    val_str = str(val).strip()
    
    # Map raw enum representations or English names to readable Spanish
    mapping = {
        "PatientStatus.INTAKE": "Admisión",
        "PatientStatus.EVALUATION": "Evaluación Clínica",
        "PatientStatus.TREATMENT_PLANNING": "Planificación de Tratamiento",
        "PatientStatus.ACTIVE_THERAPY": "Terapia Activa",
        "PatientStatus.CRISIS": "Intervención de Crisis",
        "PatientStatus.DISCHARGED": "Alta Médica",
        "INTAKE": "Admisión",
        "EVALUATION": "Evaluación Clínica",
        "TREATMENT_PLANNING": "Planificación de Tratamiento",
        "ACTIVE_THERAPY": "Terapia Activa",
        "CRISIS": "Intervención de Crisis",
        "DISCHARGED": "Alta Médica",
        
        "RiskLevel.LOW": "Bajo",
        "RiskLevel.MEDIUM": "Medio",
        "RiskLevel.HIGH": "Alto",
        "RiskLevel.CRITICAL": "Crítico",
        "LOW": "Bajo",
        "MEDIUM": "Medio",
        "HIGH": "Alto",
        "CRITICAL": "Crítico",
        "High": "Alto",
        "Medium": "Medio",
        "Low": "Bajo",
        "Critical": "Crítico"
    }
    return mapping.get(val_str, val_str)

def generate_clinical_html_report(patient: Dict[str, Any], audit_trail_len: int, clinical_notes: Optional[str] = None, pending_state: Optional[str] = None) -> str:
    """
    Genera un informe médico HTML en cumplimiento con las regulaciones de salud.
    Incluye encabezados clínicos, advertencias de seguridad de HIPAA, historial de estado y bloques de firma.
    """
    conditions_html = "".join([
        f"<tr><td><code>{c['code']}</code></td><td>{c['display']}</td><td>{clean_status(c['severity'])}</td><td>{c['onset_date']}</td></tr>"
        for c in patient.get("conditions", [])
    ])
    if not conditions_html:
        conditions_html = "<tr><td colspan='4' style='text-align:center;'>No se registraron diagnósticos clínicos activos.</td></tr>"

    # Traducir género al español
    gender_es = "Masculino" if patient.get("gender") == "male" else ("Femenino" if patient.get("gender") == "female" else "No especificado")

    # Determinar las notas a incluir
    if clinical_notes and clinical_notes.strip():
        notes_content = clinical_notes.strip()
    else:
        current_state_clean = clean_status(patient.get("current_state"))
        risk_level_clean = clean_status(patient.get("risk_level"))
        notes_content = f"El paciente se encuentra actualmente en estado de <strong>{current_state_clean}</strong>. La evaluación de riesgo indica estado <strong>{risk_level_clean}</strong>. El plan de cuidado consiste en terapia cognitivo-conductual estándar y controles de seguridad continuos."

    # Bloque de petición de cambio de estado si existe
    pending_section_html = ""
    if pending_state:
        pending_state_clean = clean_status(pending_state)
        pending_section_html = f"""
    <div class="section-title">Proceso de Petición de Estado</div>
    <div class="pending-status-box" style="border: 2px dashed #ab5852; background-color: #fdf2f2; padding: 15px; border-radius: 6px; margin-top: 10px; color: #ab5852;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="border: none;">
                <td style="width: 30%; font-weight: bold; border: none; padding: 5px;">Transición Solicitada:</td>
                <td style="border: none; padding: 5px;">a <strong>{pending_state_clean}</strong></td>
            </tr>
            <tr style="border: none;">
                <td style="font-weight: bold; border: none; padding: 5px;">Estado del Proceso:</td>
                <td style="border: none; padding: 5px;"><strong>Pendiente por Validación (Autorización Médica)</strong></td>
            </tr>
            <tr style="border: none;">
                <td style="font-weight: bold; border: none; padding: 5px;">Detalle Clínico:</td>
                <td style="border: none; padding: 5px; font-style: italic;">La transición se encuentra en espera de la firma del médico principal y del oficial de cumplimiento HIPAA.</td>
            </tr>
        </table>
    </div>
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Resumen Clínico EHR - {patient['name']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            color: #333;
            margin: 40px;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #ab5852;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .confidential-banner {{
            background-color: #fdf2f2;
            color: #ab5852;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #ab5852;
            border-radius: 4px;
            margin-bottom: 20px;
            text-transform: uppercase;
            font-size: 13px;
        }}
        .section-title {{
            font-size: 18px;
            color: #ab5852;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            margin-top: 25px;
        }}
        .grid-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .grid-table th, .grid-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        .grid-table th {{
            background-color: #f2f2f2;
        }}
        .meta-info {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .meta-item {{
            width: 48%;
        }}
        .footer {{
            margin-top: 50px;
            font-size: 12px;
            color: #777;
            text-align: center;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
        .signature-block {{
            margin-top: 40px;
            display: flex;
            justify-content: space-between;
        }}
        .sig {{
            border-top: 1px solid #333;
            width: 45%;
            text-align: center;
            padding-top: 5px;
            margin-top: 40px;
        }}
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="confidential-banner">
        CONFIDENCIAL - Información de Salud Protegida (PHI) - Sujeto a las Regulaciones de HIPAA y Ley de Privacidad
    </div>
    
    <div class="header">
        <h1>Resumen de Cuidado Clínico Psiquiátrico</h1>
        <p>Referencia de Exportación EHR: <strong>EHR-{patient['id']}-{int(datetime.now().timestamp())}</strong></p>
    </div>

    <div class="meta-info">
        <div class="meta-item">
            <strong>Nombre del Paciente:</strong> {patient['name']}<br>
            <strong>Fecha de Nacimiento:</strong> {patient['birthdate']}<br>
            <strong>Género:</strong> {gender_es}<br>
            <strong>ID de Paciente:</strong> {patient['id']}
        </div>
        <div class="meta-item" style="text-align: right;">
            <strong>Estado Actual:</strong> {clean_status(patient.get('current_state'))}<br>
            <strong>Nivel de Riesgo Clínico:</strong> {clean_status(patient.get('risk_level'))}<br>
            <strong>Clínico Asignado:</strong> {patient['assigned_clinician']}<br>
            <strong>Documento Generado:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>

    <div class="section-title">Diagnósticos Clínicos Activos (Mapeados por FHIR)</div>
    <table class="grid-table">
        <thead>
            <tr>
                <th>Código ICD-10/SNOMED</th>
                <th>Descripción del Diagnóstico</th>
                <th>Severidad</th>
                <th>Fecha de Inicio</th>
            </tr>
        </thead>
        <tbody>
            {conditions_html}
        </tbody>
    </table>

    <div class="section-title">Contexto de Auditoría de Seguridad y Cumplimiento</div>
    <p>
        Este registro médico está vinculado con el libro de auditoría de transacciones en vivo que contiene <strong>{audit_trail_len}</strong> eventos auditables.
        Todos los accesos, overrides clínicos y decisiones automatizadas del copiloto de IA se rastrean criptográficamente en nuestro libro mayor HIPAA.
    </p>

    <div class="section-title">Notas del Médico y Directivas Clínicas</div>
    <div style="border: 1px solid #ccc; padding: 15px; border-radius: 4px; background-color: #fafafa; min-height: 100px; margin-top: 10px; white-space: pre-wrap;">{notes_content}</div>
    {pending_section_html}

    <div class="signature-block">
        <div class="sig">
            Firma del Médico / Clínico Autorizado
        </div>
        <div class="sig">
            Fecha de Validación del Oficial de Cumplimiento / Auditoría
        </div>
    </div>

    <div class="footer">
        Generado por la Plataforma de Salud Asclia | Código de cumplimiento: HITRUST-164.312(a)(2)(iv) | Página 1 de 1
    </div>
</body>
</html>
"""
    return html_content

def generate_clinical_pdf(patient: Dict[str, Any], filepath: str, clinical_notes: Optional[str] = None, pending_state: Optional[str] = None):
    """
    Compila un archivo PDF regulatorio para el expediente del paciente.
    Usa reportlab si está disponible, de lo contrario escribe el contenido HTML con formato en la ruta.
    """
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Banner de Encabezado
        c.setFillColorRGB(0.67, 0.35, 0.32) # terracota
        c.rect(40, height - 60, width - 80, 25, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(width / 2.0, height - 50, "CONFIDENCIAL - INFORMACION DE SALUD PROTEGIDA (PHI) - REGULADO POR HIPAA")
        
        # Título
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, height - 95, "Resumen de Cuidado Clinico Psiquiatrico")
        
        # Línea divisoria
        c.setStrokeColorRGB(0.67, 0.35, 0.32)
        c.setLineWidth(2)
        c.line(40, height - 105, width - 40, height - 105)
        
        # Traducir género al español
        gender_es = "Masculino" if patient.get("gender") == "male" else ("Femenino" if patient.get("gender") == "female" else "No especificado")

        # Meta info
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, height - 130, "Informacion del Paciente")
        c.setFont("Helvetica", 9)
        c.drawString(40, height - 150, f"Nombre: {patient['name']}")
        c.drawString(40, height - 165, f"Fecha de Nacimiento: {patient['birthdate']}")
        c.drawString(40, height - 180, f"Genero: {gender_es}")
        c.drawString(40, height - 195, f"ID de Paciente: {patient['id']}")
        
        c.drawString(300, height - 150, f"Estado Actual: {clean_status(patient.get('current_state'))}")
        c.drawString(300, height - 165, f"Nivel de Riesgo: {clean_status(patient.get('risk_level'))}")
        c.drawString(300, height - 180, f"Clinico Asignado: {patient['assigned_clinician']}")
        c.drawString(300, height - 195, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Título de sección
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, height - 225, "Diagnosticos Activos / Condiciones Clinicas")
        c.setLineWidth(1)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(40, height - 230, width - 40, height - 230)
        
        # Renderizar cabeceras de tabla
        y_pos = height - 248
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y_pos, "Codigo ICD-10")
        c.drawString(140, y_pos, "Descripcion Clinica")
        c.drawString(350, y_pos, "Severidad")
        c.drawString(450, y_pos, "Fecha de Inicio")
        
        # Renderizar condiciones
        c.setFont("Helvetica", 9)
        for cond in patient.get("conditions", []):
            y_pos -= 18
            c.drawString(40, y_pos, cond["code"])
            c.drawString(140, y_pos, cond["display"][:38]) # limitar largo
            c.drawString(350, y_pos, clean_status(cond["severity"]))
            c.drawString(450, y_pos, cond["onset_date"])
            
        # Cuadro de notas clínicas
        y_pos -= 45
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y_pos, "Directivas Clinicas")
        c.setLineWidth(1)
        c.line(40, y_pos - 5, width - 40, y_pos - 5)
        
        y_pos -= 25
        c.setFont("Helvetica-Oblique", 9)
        if clinical_notes and clinical_notes.strip():
            notes_lines = [clinical_notes.strip()[i:i+85] for i in range(0, len(clinical_notes.strip()), 85)]
            for line in notes_lines[:4]: # limitar a 4 líneas en PDF
                c.drawString(45, y_pos, line)
                y_pos -= 15
        else:
            c.drawString(45, y_pos, f"El paciente esta bajo protocolo de monitoreo '{clean_status(patient.get('current_state'))}'.")
            c.drawString(45, y_pos - 15, f"Se han desplegado esquemas de tratamiento estandar para {patient['name']}.")
            y_pos -= 30
        
        # Sección de petición de estado en PDF
        if pending_state:
            y_pos -= 15
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.67, 0.35, 0.32) # terracota
            c.drawString(40, y_pos, "Peticion de Estado Pendiente")
            c.setFillColorRGB(0, 0, 0)
            y_pos -= 12
            c.setFont("Helvetica", 9)
            c.drawString(45, y_pos, f"Transicion Solicitada: a {clean_status(pending_state)}")
            y_pos -= 12
            c.drawString(45, y_pos, "Estado del Proceso: Pendiente por Validacion (Autorizacion Medica)")
            y_pos -= 10

        # Sección de firmas
        y_pos -= 50
        c.setLineWidth(1)
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.line(40, y_pos, 220, y_pos)
        c.line(320, y_pos, 500, y_pos)
        
        c.setFont("Helvetica", 8)
        c.drawString(40, y_pos - 12, "Firma de Clinico Autorizado")
        c.drawString(320, y_pos - 12, "Validacion de Oficial de Cumplimiento")
        
        # Pie de página
        c.drawCentredString(width / 2.0, 30, "Generado por la Plataforma de Salud Asclia | Codigo de cumplimiento: HITRUST-164.312(a)(2)(iv)")
        c.save()
    else:
        # Fallback: Escribir HTML directamente en archivo
        html_str = generate_clinical_html_report(patient, 0, clinical_notes, pending_state)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_str)
