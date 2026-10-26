"""
QuickDiagnosis - Diagnosis Engine & Evidence Fusion Service (OOP & Data Structures)
Implements:
- match_symptoms() using Set intersection operations
- match_labs() using Dictionary mappings of test results
- combine_evidence() integrating multivariable clinical evidence
- rank_conditions() using Priority Queue / heap structures
"""

import heapq
import json
import os
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

from backend.app.models.patient import Patient
from backend.app.models.disease import Symptom, Disease, DiagnosisMatch
from backend.app.models.lab_report import LabReport
from backend.app.rules.disease_rules import DiseaseLabRules


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
            # Attempt multi-environment candidate paths (Vercel lambda, Docker, parent root)
            alt_candidates = [
                os.path.join(os.getcwd(), "data", filename),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", filename),
                os.path.join("/var/task/data", filename),
                os.path.join("/var/task", filename)
            ]
            for alt in alt_candidates:
                if os.path.exists(alt):
                    filepath = alt
                    break
            else:
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


class DiagnosisEngine:
    """
    Intelligent evidence-combining diagnostic engine.
    Fuses symptom presentations with optional laboratory test evidence
    using deterministic rules and priority queue ranking.
    """
    def __init__(self, knowledge_base: MedicalKnowledgeBase):
        self.kb = knowledge_base

    # -------------------------------------------------------------------------
    # OOP Contract Methods
    # -------------------------------------------------------------------------
    def match_symptoms(
        self,
        patient: Patient,
        selected_symptom_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculates symptom overlap scores using Set operations.
        Returns mapping: disease_id -> score breakdown dict.
        """
        # Set data structure for fast O(1) membership and deduplication
        selected_set: Set[str] = set(selected_symptom_ids or [])
        if not selected_set:
            return {}

        symptom_scores: Dict[str, Dict[str, Any]] = {}

        for disease in self.kb.diseases:
            # Set intersections
            matched_core = list(selected_set.intersection(disease.core_symptoms))
            matched_secondary = list(selected_set.intersection(disease.secondary_symptoms))
            unmatched_core = list(disease.core_symptoms.difference(selected_set))

            total_core = len(disease.core_symptoms)
            total_secondary = len(disease.secondary_symptoms)

            if not matched_core and not matched_secondary:
                continue

            # Core symptom weight calculation
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

            core_coverage = len(matched_core) / max(1, total_core)
            secondary_coverage = len(matched_secondary) / max(1, total_secondary) if total_secondary > 0 else 0

            raw_score = (core_score * 1.8) + (secondary_score * 0.9) + (core_coverage * 15.0) + (secondary_coverage * 5.0)

            # Demographic Multiplier
            demographic_multiplier = disease.evaluate_demographic_risk(patient)
            adjusted_score = raw_score * demographic_multiplier

            # Coverage factor penalty if disease requires 3+ core symptoms and patient only has 1
            if total_core >= 3 and len(matched_core) == 1 and not matched_secondary:
                adjusted_score *= 0.65

            symptom_scores[disease.id] = {
                "disease": disease,
                "score": adjusted_score,
                "matched_core": matched_core,
                "matched_secondary": matched_secondary,
                "unmatched_core": unmatched_core,
                "demographic_multiplier": demographic_multiplier
            }

        return symptom_scores

    def match_labs(
        self,
        lab_report: Optional[LabReport]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluates laboratory findings against disease correlation rules.
        Returns mapping: disease_id -> {score_boost, matched_findings}.
        """
        if not lab_report or not lab_report.tests:
            return {}

        # Dictionary mapping test names to LabTest objects for fast O(1) lookup
        labs_by_name: Dict[str, Any] = {t.test_name: t for t in lab_report.tests}
        lab_evidence_map: Dict[str, Dict[str, Any]] = {}

        for disease in self.kb.diseases:
            evidence = DiseaseLabRules.evaluate_lab_evidence(disease.id, labs_by_name)
            if evidence["score_boost"] > 0:
                lab_evidence_map[disease.id] = evidence

        return lab_evidence_map

    def combine_evidence(
        self,
        symptom_scores: Dict[str, Dict[str, Any]],
        lab_evidence_map: Dict[str, Dict[str, Any]]
    ) -> List[DiagnosisMatch]:
        """
        Fuses symptom match scores with laboratory evidence.
        Lab findings act as supporting or pathognomonic corroboration.
        """
        matches: List[DiagnosisMatch] = []

        # Evaluate candidate diseases that have symptom matches
        for d_id, sym_data in symptom_scores.items():
            disease: Disease = sym_data["disease"]
            base_score: float = sym_data["score"]
            
            # Check for lab evidence
            lab_data = lab_evidence_map.get(d_id, {})
            lab_boost = lab_data.get("score_boost", 0.0)
            matched_findings = lab_data.get("matched_findings", [])

            # Combined score: symptom score + (lab boost * weight factor)
            combined_score = base_score + (lab_boost * 4.8)

            matches.append(
                DiagnosisMatch(
                    disease=disease,
                    raw_score=combined_score,
                    probability_pct=0,  # Calculated in rank_conditions
                    matched_core=sym_data["matched_core"],
                    matched_secondary=sym_data["matched_secondary"],
                    unmatched_core=sym_data["unmatched_core"],
                    demographic_multiplier=sym_data["demographic_multiplier"],
                    matched_lab_findings=matched_findings,
                    lab_evidence_boost=lab_boost
                )
            )

        return matches

    def rank_conditions(
        self,
        candidates: List[DiagnosisMatch],
        top_k: int = 5
    ) -> List[DiagnosisMatch]:
        """
        Ranks candidate conditions using a heap priority queue structure (Python heapq).
        Data structure requirement: Priority Queue.
        """
        if not candidates:
            return []

        # Max-heap priority queue simulation via heapq (negative raw_score as key)
        # Heap elements: (priority, counter, candidate_object)
        heap: List[Tuple[float, int, DiagnosisMatch]] = []
        for i, cand in enumerate(candidates):
            # Using -cand.raw_score because heapq is min-heap by default
            heapq.heappush(heap, (-cand.raw_score, i, cand))

        ranked: List[DiagnosisMatch] = []
        while heap and len(ranked) < top_k:
            _, _, cand = heapq.heappop(heap)
            ranked.append(cand)

        # Normalize probability percentages
        max_score = ranked[0].raw_score
        for i, cand in enumerate(ranked):
            if i == 0:
                base_pct = min(94, max(68, int((cand.raw_score / (max_score + 10.0)) * 100) + 15))
            else:
                relative_ratio = cand.raw_score / max(1.0, max_score)
                base_pct = max(35, int(ranked[0].probability_pct * relative_ratio * 0.92))
            cand.probability_pct = base_pct

        return ranked

    # -------------------------------------------------------------------------
    # Main Diagnostic Entry Point
    # -------------------------------------------------------------------------
    def diagnose(
        self,
        patient: Patient,
        selected_symptom_ids: List[str],
        lab_report: Optional[LabReport] = None
    ) -> Dict[str, Any]:
        """
        Executes complete diagnostic pipeline:
        Symptoms + Optional Labs -> Match Symptoms -> Match Labs -> Combine -> Priority Rank
        """
        selected_set: Set[str] = set(selected_symptom_ids or [])
        
        if not selected_set and not lab_report:
            return {
                "success": False,
                "error": "Please provide symptoms or upload a laboratory report to evaluate.",
                "patient": patient.to_dict(),
                "top_probable_diseases": [],
                "has_lab_evidence": False,
                "motivational_message": self.kb.get_motivational_quote("step_transition")
            }

        # 1. Match Symptoms
        symptom_scores = self.match_symptoms(patient, selected_symptom_ids)

        # 2. Match Labs
        lab_evidence_map = self.match_labs(lab_report)

        # 3. Combine Evidence
        candidate_matches = self.combine_evidence(symptom_scores, lab_evidence_map)

        # 4. Rank Candidates via Priority Queue
        top_candidates = self.rank_conditions(candidate_matches, top_k=5)

        # Format output
        results_list = [c.to_dict(self.kb.symptom_name_map) for c in top_candidates]

        has_lab = lab_report is not None and len(lab_report.tests) > 0
        abnormal_lab_count = len(lab_report.get_abnormal_tests()) if lab_report else 0

        # Disclaimer logic
        if has_lab:
            disclaimer = (
                "Your selected symptoms and laboratory findings may be relevant to the conditions "
                "shown below. This preliminary assessment combines clinical symptom overlap with "
                "reported laboratory test findings, but it does NOT confirm a diagnosis. Always consult "
                "a qualified physician or licensed healthcare provider for formal clinical diagnosis, "
                "repeat confirmatory testing, and personalized medical treatment."
            )
        else:
            disclaimer = (
                "QuickDiagnosis is an intelligent probabilistic symptom screening tool designed "
                "for educational and preliminary assessment. This report lists the most probable "
                "conditions based on symptom overlap and demographic risk factors, but it is NOT "
                "a definitive medical diagnosis. Always seek direct consultation with a qualified "
                "physician or healthcare professional for clinical testing, diagnosis, and prescription treatments."
            )

        # Log session safely
        self._log_diagnosis_session(patient, selected_symptom_ids, results_list, has_lab)

        return {
            "success": True,
            "patient": patient.to_dict(),
            "selected_symptoms_count": len(selected_set),
            "top_probable_diseases": results_list,
            "has_lab_evidence": has_lab,
            "attached_lab_report_id": lab_report.report_id if lab_report else None,
            "attached_lab_abnormal_count": abnormal_lab_count,
            "disclaimer": disclaimer,
            "motivational_message": self.kb.get_motivational_quote("after_result")
        }

    def _log_diagnosis_session(
        self,
        patient: Patient,
        symptoms: List[str],
        results: List[Dict[str, Any]],
        has_lab_evidence: bool = False
    ) -> None:
        """Appends anonymous screening metrics to local JSON log file."""
        log_file = os.path.join(self.kb.data_dir, "diagnosis_logs.json")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gender": patient.gender,
            "age": patient.age,
            "weight": patient.weight,
            "symptom_count": len(symptoms),
            "has_lab_evidence": has_lab_evidence,
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
            if len(logs) > 100:
                logs = logs[-100:]
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass
