"""
QuickDiagnosis - Disease & Diagnosis Domain Models (OOP Architecture)
Defines structured classes for Symptom, Disease, and DiagnosisMatch.
"""

from typing import List, Dict, Any, Optional, Set
from backend.app.models.patient import Patient


class Symptom:
    """Represents an individual clinical symptom."""
    def __init__(self, symptom_id: str, name: str, system: str, weight: float = 1.5):
        self.id = symptom_id
        self.name = name
        self.system = system
        self.weight = float(weight)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "system": self.system,
            "weight": self.weight
        }

    def __repr__(self) -> str:
        return f"<Symptom {self.id}: {self.name}>"


class Disease:
    """Represents a medical disease with symptom associations, lab profiles, and demographic predispositions."""
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.system: str = data.get("system", "")
        self.category: str = data.get("category", "General")
        self.urgency: str = data.get("urgency", "Moderate")
        self.demographic_risk: Dict[str, Any] = data.get("demographic_risk", {})
        self.core_symptoms: Set[str] = set(data.get("core_symptoms", []))
        self.secondary_symptoms: Set[str] = set(data.get("secondary_symptoms", []))
        self.description: str = data.get("description", "")
        self.measurements_and_cures: Dict[str, Any] = data.get("measurements_and_cures", {})
        
        # Associated laboratory patterns (e.g. {"Hemoglobin": "LOW", "Ferritin": "LOW"})
        self.expected_lab_patterns: Dict[str, str] = data.get("expected_lab_patterns", {})

    def evaluate_demographic_risk(self, patient: Patient) -> float:
        """
        Calculates a demographic multiplier based on patient's gender and age.
        Returns a float multiplier typically between 0.85 and 1.6.
        """
        multiplier = 1.0
        gender_bias = self.demographic_risk.get("gender_bias", "any").lower()
        gender_mult = float(self.demographic_risk.get("gender_multiplier", 1.0))
        
        if gender_bias in ["female", "male"]:
            if patient.gender == gender_bias:
                multiplier *= gender_mult
            elif patient.gender in ["female", "male"]:
                multiplier *= max(0.85, 2.0 - gender_mult)

        age_min = int(self.demographic_risk.get("age_min", 0))
        age_max = int(self.demographic_risk.get("age_max", 120))
        age_mult = float(self.demographic_risk.get("age_multiplier", 1.0))

        if age_min <= patient.age <= age_max:
            multiplier *= age_mult
        else:
            if patient.age < age_min:
                diff = age_min - patient.age
                multiplier *= max(0.7, 1.0 - (diff * 0.02))
            elif patient.age > age_max:
                diff = patient.age - age_max
                multiplier *= max(0.7, 1.0 - (diff * 0.02))

        return multiplier

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "system": self.system,
            "category": self.category,
            "urgency": self.urgency,
            "description": self.description,
            "core_symptoms_count": len(self.core_symptoms),
            "risk_explanation": self.demographic_risk.get("risk_explanation", "")
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "system": self.system,
            "category": self.category,
            "urgency": self.urgency,
            "demographic_risk": self.demographic_risk,
            "description": self.description,
            "measurements_and_cures": self.measurements_and_cures,
            "core_symptoms": list(self.core_symptoms),
            "secondary_symptoms": list(self.secondary_symptoms),
            "expected_lab_patterns": self.expected_lab_patterns
        }

    def __repr__(self) -> str:
        return f"<Disease {self.id}: {self.name}>"


class DiagnosisMatch:
    """Holds calculated probability and diagnostic breakdown for a disease candidate."""
    def __init__(
        self,
        disease: Disease,
        raw_score: float,
        probability_pct: int,
        matched_core: List[str],
        matched_secondary: List[str],
        unmatched_core: List[str],
        demographic_multiplier: float,
        matched_lab_findings: Optional[List[Dict[str, Any]]] = None,
        lab_evidence_boost: float = 0.0
    ):
        self.disease = disease
        self.raw_score = raw_score
        self.probability_pct = probability_pct
        self.matched_core = matched_core
        self.matched_secondary = matched_secondary
        self.unmatched_core = unmatched_core
        self.demographic_multiplier = demographic_multiplier
        self.matched_lab_findings = matched_lab_findings or []
        self.lab_evidence_boost = lab_evidence_boost

    def to_dict(self, symptom_name_map: Dict[str, str]) -> Dict[str, Any]:
        return {
            "id": self.disease.id,
            "name": self.disease.name,
            "system": self.disease.system,
            "category": self.disease.category,
            "urgency": self.disease.urgency,
            "probability_percentage": self.probability_pct,
            "matched_core": [symptom_name_map.get(s, s) for s in self.matched_core],
            "matched_secondary": [symptom_name_map.get(s, s) for s in self.matched_secondary],
            "unmatched_core": [symptom_name_map.get(s, s) for s in self.unmatched_core],
            "risk_explanation": self.disease.demographic_risk.get("risk_explanation", ""),
            "description": self.disease.description,
            "demographic_relevance": "High" if self.demographic_multiplier > 1.15 else "Standard",
            "matched_lab_findings": self.matched_lab_findings,
            "has_lab_evidence": len(self.matched_lab_findings) > 0
        }

    def __repr__(self) -> str:
        return f"<DiagnosisMatch {self.disease.name} ({self.probability_pct}%)>"
