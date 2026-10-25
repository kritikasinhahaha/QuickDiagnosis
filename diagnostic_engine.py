"""
QuickDiagnosis - Core Diagnostic Engine & Knowledgebase
Implements probabilistic symptom matching, demographic risk analysis,
data structure operations, and JSON file handling.
"""

import json
import os
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from models import Patient, Symptom, Disease, DiagnosisMatch


class MedicalKnowledgeBase:
    """Handles loading, querying, and managing medical data files."""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.systems: List[Dict[str, Any]] = []
        self.symptoms_by_id: Dict[str, Symptom] = {}
        self.symptoms_by_system: Dict[str, List[Symptom]] = {}
        self.diseases: List[Disease] = []
        self.motivational_quotes: Dict[str, List[str]] = {}
        self.symptom_name_map: Dict[str, str] = {}
        
        self._load_all_data()

    def _load_json_file(self, filename: str) -> Any:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Required medical data file '{filename}' was not found at {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all_data(self) -> None:
        """Loads body systems, symptoms, diseases, and motivational quotes from disk."""
        # 1. Load Body Systems
        systems_data = self._load_json_file("body_systems.json")
        self.systems = systems_data

        # 2. Load Symptoms
        symptoms_raw = self._load_json_file("symptoms.json")
        for item in symptoms_raw:
            symptom = Symptom(
                symptom_id=item["id"],
                name=item["name"],
                system=item["system"],
                weight=item.get("weight", 1.5)
            )
            self.symptoms_by_id[symptom.id] = symptom
            self.symptom_name_map[symptom.id] = symptom.name
            
            if symptom.system not in self.symptoms_by_system:
                self.symptoms_by_system[symptom.system] = []
            self.symptoms_by_system[symptom.system].append(symptom)

        # 3. Load Diseases
        diseases_raw = self._load_json_file("diseases.json")
        for item in diseases_raw:
            self.diseases.append(Disease(item))

        # 4. Load Quotes
        self.motivational_quotes = self._load_json_file("motivational_quotes.json")

    def get_motivational_quote(self, context: str = "after_result") -> str:
        """Retrieves a random empathetic quote based on context."""
        quote_list = self.motivational_quotes.get(context, self.motivational_quotes.get("general_comfort", []))
        if quote_list:
            return random.choice(quote_list)
        return "You are stronger than you know, and your health journey starts with awareness."

    def get_disease_by_id(self, disease_id: str) -> Optional[Disease]:
        """Looks up a disease by unique identifier."""
        for d in self.diseases:
            if d.id == disease_id:
                return d
        return None


class DiagnosticEngine:
    """
    Evaluates patient demographics and symptom inputs against medical knowledgebase
    using multi-factor probabilistic ranking algorithms.
    """
    def __init__(self, knowledge_base: MedicalKnowledgeBase):
        self.kb = knowledge_base

    def diagnose(self, patient: Patient, selected_symptom_ids: List[str]) -> Dict[str, Any]:
        """
        Calculates match scores for all known diseases and returns the top 4-5
        most probable conditions with comprehensive explanations.
        """
        selected_set: Set[str] = set(selected_symptom_ids or [])
        
        if not selected_set:
            return {
                "success": False,
                "error": "No symptoms provided. Please select at least one symptom to evaluate.",
                "patient": patient.to_dict(),
                "top_probable_diseases": [],
                "motivational_message": self.kb.get_motivational_quote("step_transition")
            }

        candidates: List[DiagnosisMatch] = []

        for disease in self.kb.diseases:
            # Set intersections for fast O(1) membership operations
            matched_core = list(selected_set.intersection(disease.core_symptoms))
            matched_secondary = list(selected_set.intersection(disease.secondary_symptoms))
            unmatched_core = list(disease.core_symptoms.difference(selected_set))

            total_core = len(disease.core_symptoms)
            total_secondary = len(disease.secondary_symptoms)

            # Skip diseases with zero matches
            if not matched_core and not matched_secondary:
                continue

            # Core symptom weight calculation (core symptoms are strongly pathognomonic)
            core_score = 0.0
            for sym_id in matched_core:
                sym_obj = self.kb.symptoms_by_id.get(sym_id)
                w = sym_obj.weight if sym_obj else 1.5
                core_score += (w * 2.5)

            # Secondary symptom weight calculation
            secondary_score = 0.0
            for sym_id in matched_secondary:
                sym_obj = self.kb.symptoms_by_id.get(sym_id)
                w = sym_obj.weight if sym_obj else 1.5
                secondary_score += (w * 1.2)

            # Proportion coverage score
            core_coverage = len(matched_core) / max(1, total_core)
            secondary_coverage = len(matched_secondary) / max(1, total_secondary) if total_secondary > 0 else 0

            # Raw base score
            raw_score = (core_score * 1.8) + (secondary_score * 0.9) + (core_coverage * 15.0) + (secondary_coverage * 5.0)

            # Demographic Multiplier (Gender + Age factors)
            demographic_multiplier = disease.evaluate_demographic_risk(patient)
            adjusted_score = raw_score * demographic_multiplier

            # Coverage factor penalty if disease requires 3+ core symptoms and patient only has 1
            if total_core >= 3 and len(matched_core) == 1 and not matched_secondary:
                adjusted_score *= 0.65

            candidates.append(
                DiagnosisMatch(
                    disease=disease,
                    raw_score=adjusted_score,
                    probability_pct=0,  # Will be normalized below
                    matched_core=matched_core,
                    matched_secondary=matched_secondary,
                    unmatched_core=unmatched_core,
                    demographic_multiplier=demographic_multiplier
                )
            )

        if not candidates:
            # Fallback if selected symptoms didn't meet criteria
            return {
                "success": True,
                "patient": patient.to_dict(),
                "selected_symptoms_count": len(selected_set),
                "top_probable_diseases": [],
                "disclaimer": "No common medical conditions directly match this exact cluster of symptoms.",
                "motivational_message": self.kb.get_motivational_quote("after_result")
            }

        # Sort candidates descending by adjusted score
        candidates.sort(key=lambda x: x.raw_score, reverse=True)

        # Take top 4 or 5 diseases
        top_candidates = candidates[:5] if len(candidates) >= 5 else candidates[:4]

        # Calculate normalized probability percentages
        # We ensure highest candidate is comfortably between 65% and 94%
        max_score = top_candidates[0].raw_score
        for i, cand in enumerate(top_candidates):
            if i == 0:
                base_pct = min(92, max(68, int((cand.raw_score / (max_score + 10.0)) * 100) + 15))
            else:
                relative_ratio = cand.raw_score / max(1.0, max_score)
                base_pct = max(35, int(top_candidates[0].probability_pct * relative_ratio * 0.92))
            cand.probability_pct = base_pct

        # Format output
        results_list = [c.to_dict(self.kb.symptom_name_map) for c in top_candidates]

        # Log session to file safely (File Handling requirement)
        self._log_diagnosis_session(patient, selected_symptom_ids, results_list)

        return {
            "success": True,
            "patient": patient.to_dict(),
            "selected_symptoms_count": len(selected_set),
            "top_probable_diseases": results_list,
            "disclaimer": (
                "QuickDiagnosis is an intelligent probabilistic symptom screening tool designed "
                "for educational and preliminary assessment. This report lists the most probable "
                "conditions based on symptom overlap and demographic risk factors, but it is NOT "
                "a definitive medical diagnosis. Always seek direct consultation with a qualified "
                "physician or healthcare professional for clinical testing, diagnosis, and prescription treatments."
            ),
            "motivational_message": self.kb.get_motivational_quote("after_result")
        }

    def _log_diagnosis_session(
        self,
        patient: Patient,
        symptoms: List[str],
        results: List[Dict[str, Any]]
    ) -> None:
        """Appends anonymous screening metrics to a local JSON log file."""
        log_file = os.path.join(self.kb.data_dir, "diagnosis_logs.json")
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "gender": patient.gender,
            "age": patient.age,
            "weight": patient.weight,
            "symptom_count": len(symptoms),
            "top_probable_disease": results[0]["name"] if results else None,
            "top_probability": results[0]["probability_percentage"] if results else None
        }

        try:
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                except Exception:
                    logs = []
            logs.append(entry)
            # Keep only last 100 entries to manage file size
            if len(logs) > 100:
                logs = logs[-100:]
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            # Non-blocking logging failure
            pass
