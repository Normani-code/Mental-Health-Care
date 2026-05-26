import re
from typing import Dict, Any, Tuple
from datetime import datetime
from backend.schemas import ClinicalCondition

def parse_hl7_message(raw_hl7: str) -> Dict[str, Any]:
    """
    Parses a raw HL7 v2 message (ADT or ORU) into a structured dictionary.
    Supports PID (Patient Identification) and OBX (Observation) segments.
    """
    lines = raw_hl7.strip().split('\n')
    parsed_data = {}
    observations = []

    for line in lines:
        if not line:
            continue
        parts = line.split('|')
        segment_type = parts[0]

        if segment_type == "MSH":
            # MSH|^~\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|...
            parsed_data["message_type"] = parts[8] if len(parts) > 8 else "UNKNOWN"
            
        elif segment_type == "PID":
            # PID|seq|id|alt_id|...|family_name^given_name|birthdate|gender
            patient_id = parts[3] if len(parts) > 3 else "UNKNOWN"
            name_parts = parts[5].split('^') if len(parts) > 5 else ["Unknown", "Patient"]
            family_name = name_parts[0]
            given_name = name_parts[1] if len(name_parts) > 1 else ""
            
            birthdate_raw = parts[7] if len(parts) > 7 else ""
            # Format YYYYMMDD -> YYYY-MM-DD
            birthdate = birthdate_raw
            if len(birthdate_raw) == 8:
                birthdate = f"{birthdate_raw[0:4]}-{birthdate_raw[4:6]}-{birthdate_raw[6:8]}"
                
            gender = parts[8] if len(parts) > 8 else "U"
            if gender == "M":
                gender = "male"
            elif gender == "F":
                gender = "female"
            else:
                gender = "unknown"

            parsed_data["patient_id"] = patient_id
            parsed_data["patient_name"] = f"{given_name} {family_name}".strip()
            parsed_data["birthdate"] = birthdate
            parsed_data["gender"] = gender

        elif segment_type == "OBX":
            # OBX|seq|value_type|identifier^text|...|value|units|reference_range|abnormal_flags
            obs_id = parts[3].split('^')[0] if len(parts) > 3 else "UNKNOWN"
            obs_text = parts[3].split('^')[1] if len(parts) > 3 and len(parts[3].split('^')) > 1 else "Observation"
            value = parts[5] if len(parts) > 5 else ""
            severity = parts[8] if len(parts) > 8 else "N" # N = Normal, A = Abnormal, H = High
            
            observations.append({
                "code": obs_id,
                "display": obs_text,
                "value": value,
                "severity": "Alto" if severity in ["H", "A"] else "Bajo"
            })

    if observations:
        parsed_data["observations"] = observations
        
    return parsed_data

def transform_hl7_to_fhir(parsed_hl7: Dict[str, Any]) -> Tuple[Dict[str, Any], list]:
    """
    Transforms parsed HL7 segments into FHIR Patient and Observation resource models.
    """
    # 1. FHIR Patient Resource
    fhir_patient = {
        "resourceType": "Patient",
        "id": parsed_hl7.get("patient_id", "new-patient"),
        "name": [
            {
                "use": "official",
                "text": parsed_hl7.get("patient_name", "Unknown Patient")
            }
        ],
        "gender": parsed_hl7.get("gender", "unknown"),
        "birthDate": parsed_hl7.get("birthdate", "")
    }

    # 2. FHIR Observation Resources mapped to app conditions
    conditions = []
    for obs in parsed_hl7.get("observations", []):
        condition = ClinicalCondition(
            code=obs["code"],
            display=obs["display"],
            severity=obs["severity"],
            onset_date=datetime.now().strftime("%Y-%m-%d")
        )
        conditions.append(condition)

    return fhir_patient, conditions
