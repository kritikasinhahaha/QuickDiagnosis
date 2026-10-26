"""
QuickDiagnosis - Diagnosis & Medical Knowledge API Router (FastAPI)
Exposes endpoints for symptom screening, combined symptom+lab evaluation,
and NIH/MedlinePlus + openFDA clinical enrichment.
"""

from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Request

from backend.app.models.patient import Patient
from backend.app.models.lab_report import LabReport
from backend.app.services.diagnosis_service import MedicalKnowledgeBase, DiagnosisEngine
from backend.app.services.lab_service import LabReportService
from backend.app.services.medical_source_service import MedicalSourceCoordinator

router = APIRouter(prefix="/api", tags=["Diagnosis & Clinical Knowledge"])
from pathlib import Path

def _resolve_data_dir() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "data",
        Path.cwd() / "data",
        Path("/var/task/data"),
        Path("data").resolve()
    ]
    for c in candidates:
        if (c / "diseases.json").exists():
            return str(c)
    return str(Path(__file__).resolve().parent.parent.parent.parent / "data")

DATA_DIR = _resolve_data_dir()

# Singletons for knowledge base and engines
kb = MedicalKnowledgeBase(DATA_DIR)
engine = DiagnosisEngine(kb)
lab_service = LabReportService(DATA_DIR)
source_coordinator = MedicalSourceCoordinator(DATA_DIR)



@router.get("/config", summary="Get application setup configuration")
def get_config():
    general_symptoms = [s.to_dict() for s in kb.symptoms_by_system.get("general", [])]
    return {
        "app_name": "QuickDiagnosis",
        "tagline": "Gentle, Intelligent & Privacy-First Medical Symptom Screening",
        "gender_options": [
            {"id": "female", "label": "Female", "icon": "👩", "desc": "Includes female-specific and hormonal risk profiles"},
            {"id": "male", "label": "Male", "icon": "👨", "desc": "Includes male-specific and hormonal risk profiles"},
            {"id": "other", "label": "Non-Binary / Other", "icon": "🧑", "desc": "Standard inclusive biological screening"}
        ],
        "age_brackets": [
            {"label": "Child (1-12 yrs)", "min": 1, "max": 12, "default": 8},
            {"label": "Teen (13-19 yrs)", "min": 13, "max": 19, "default": 16},
            {"label": "Young Adult (20-39 yrs)", "min": 20, "max": 39, "default": 26},
            {"label": "Adult (40-59 yrs)", "min": 40, "max": 59, "default": 48},
            {"label": "Senior (60+ yrs)", "min": 60, "max": 100, "default": 68}
        ],
        "weight_ranges": [
            {"id": "underweight", "label": "Light / Under 50 kg", "min": 35, "max": 49, "default": 45},
            {"id": "normal", "label": "Standard (50 - 70 kg)", "min": 50, "max": 70, "default": 62},
            {"id": "moderate", "label": "Moderate (71 - 85 kg)", "min": 71, "max": 85, "default": 78},
            {"id": "heavy", "label": "Above 85 kg", "min": 86, "max": 130, "default": 95}
        ],
        "body_systems": kb.systems,
        "general_symptoms": general_symptoms,
        "welcome_quote": kb.get_motivational_quote("step_transition")
    }


@router.get("/symptoms", summary="Get all clinical symptoms grouped by body system")
def get_all_symptoms():
    categorized = {}
    for system_id, symptom_list in kb.symptoms_by_system.items():
        categorized[system_id] = [s.to_dict() for s in symptom_list]
    return {
        "systems": kb.systems,
        "symptoms_by_system": categorized,
        "total_count": len(kb.symptoms_by_id)
    }


@router.post("/diagnose", summary="Execute multi-factor symptom and optional laboratory screening")
def run_diagnosis(data: Dict[str, Any]):
    gender = data.get("gender", "female")
    age = data.get("age", 25)
    weight = data.get("weight", 60.0)
    selected_symptoms = data.get("symptoms", [])

    try:
        age_int = int(age)
    except (ValueError, TypeError):
        age_int = 25

    try:
        weight_float = float(weight)
    except (ValueError, TypeError):
        weight_float = 60.0

    patient = Patient(gender=gender, age=age_int, weight=weight_float)

    # Normalize symptom inputs
    normalized_symptom_ids: List[str] = []
    for item in selected_symptoms:
        if isinstance(item, dict):
            s_id = item.get("id")
            if s_id:
                normalized_symptom_ids.append(str(s_id))
        elif isinstance(item, str):
            normalized_symptom_ids.append(item)

    # Check for optional laboratory report attachment
    lab_report_obj: Optional[LabReport] = None
    
    # 1. Attached by report ID
    lab_report_id = data.get("lab_report_id")
    if lab_report_id:
        lab_report_obj = lab_service.get_report_by_id(str(lab_report_id))

    # 2. Or passed as inline lab report dict
    if not lab_report_obj and "lab_report" in data and isinstance(data["lab_report"], dict):
        try:
            lab_report_obj = LabReport.from_dict(data["lab_report"])
        except Exception as e:
            print(f"[run_diagnosis] Error parsing inline lab report: {e}")

    # Execute diagnosis engine
    diagnosis_output = engine.diagnose(
        patient=patient,
        selected_symptom_ids=normalized_symptom_ids,
        lab_report=lab_report_obj
    )

    # Enrich candidate disease cards with authoritative MedlinePlus metadata
    if diagnosis_output.get("top_probable_diseases"):
        try:
            diagnosis_output["top_probable_diseases"] = source_coordinator.enrich_candidate_cards(
                diagnosis_output["top_probable_diseases"]
            )
        except Exception as e:
            print(f"[run_diagnosis] Warning: Error enriching candidate cards: {e}")

    return diagnosis_output


@router.get("/disease/{disease_id}", summary="Get comprehensive disease guide with MedlinePlus and FDA enrichment")
def get_disease_detail(disease_id: str):
    disease = kb.get_disease_by_id(disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")

    full_dict = disease.to_full_dict()

    # Enrich with authoritative sources
    try:
        enriched = source_coordinator.enrich_disease_detail(full_dict)
    except Exception as e:
        print(f"[get_disease_detail] Warning: Enrichment fallback: {e}")
        enriched = full_dict
        enriched["primary_source"] = "QuickDiagnosis Clinical Base"
        enriched["authoritative_sources"] = [{
            "authority": "QuickDiagnosis Clinical Base",
            "authority_full": "Verified Clinical Symptom-Disease Knowledge Base (Local)",
            "title": f"Standard Clinical Assessment: {disease.name}",
            "url": None,
            "type": "Local Base Diagnostic Mapping",
            "verified": True
        }]

    return enriched
