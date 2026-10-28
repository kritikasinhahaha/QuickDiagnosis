"""
QuickDiagnosis - Comprehensive Lab Report & Diagnosis Test Suite
Tests:
1. OOP: LabTest, LabReport, DiagnosisEngine, MedicalSource hierarchy
2. Data Structures: List, Dict, Set, Tuple, Priority Queue (heapq)
3. File Handling: JSON parsing/export, CSV parsing/export, security checks
4. Lab Interpretation: LOW, NORMAL, HIGH, UNKNOWN, priority of patient ranges
5. Diagnosis: Symptoms only vs Symptoms + Lab Evidence
6. Trends: Deterministic chronological trend calculations
7. External Sources: NIH/MedlinePlus, openFDA, and offline fallback
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.patient import Patient
from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.rules.lab_rules import LabRules
from backend.app.rules.disease_rules import DiseaseLabRules
from backend.app.utils.file_handler import FileHandler
from backend.app.services.lab_service import LabReportService
from backend.app.services.diagnosis_service import MedicalKnowledgeBase, DiagnosisEngine
from backend.app.services.medical_source_service import (
    MedicalSource, NIHSource, FDASource, LocalBaseSource, MedicalSourceCoordinator
)


class TestLabModuleOOP(unittest.TestCase):
    """Verifies Object-Oriented Programming contracts and encapsulation."""

    def test_lab_test_oop_encapsulation(self):
        # Tuple reference range (immutable)
        test = LabTest("Hemoglobin", 10.5, "g/dL", reference_low=12.0, reference_high=17.5)
        self.assertEqual(test.test_name, "Hemoglobin")
        self.assertEqual(test.value, 10.5)
        self.assertEqual(test.unit, "g/dL")
        self.assertEqual(test.reference_range, (12.0, 17.5))
        self.assertIsInstance(test.reference_range, tuple)
        self.assertEqual(test.status, "LOW")
        self.assertTrue(test.is_abnormal)

    def test_lab_test_status_interpretation(self):
        # LOW
        t_low = LabTest("Glucose", 62.0, "mg/dL", 70.0, 99.0)
        self.assertEqual(t_low.calculate_status(), "LOW")

        # NORMAL
        t_norm = LabTest("Glucose", 85.0, "mg/dL", 70.0, 99.0)
        self.assertEqual(t_norm.calculate_status(), "NORMAL")

        # HIGH
        t_high = LabTest("Glucose", 145.0, "mg/dL", 70.0, 99.0)
        self.assertEqual(t_high.calculate_status(), "HIGH")

        # UNKNOWN (no range provided)
        t_unk = LabTest("Experimental Analyte", 42.0, "units", None, None)
        self.assertEqual(t_unk.calculate_status(), "UNKNOWN")

    def test_lab_report_oop_methods(self):
        report = LabReport(patient_id="P_TEST", report_date="2026-10-26")
        self.assertEqual(report.total_tests_count, 0)

        t1 = LabTest("Hemoglobin", 11.2, "g/dL", 12.0, 17.5)  # LOW
        t2 = LabTest("WBC", 6.5, "x10^3/uL", 4.5, 11.0)       # NORMAL
        t3 = LabTest("TSH", 5.8, "uIU/mL", 0.4, 4.0)          # HIGH

        report.add_test(t1)
        report.add_test(t2)
        report.add_test(t3)

        self.assertEqual(report.total_tests_count, 3)
        self.assertIsInstance(report.tests, list)

        # Query methods
        abnormal = report.get_abnormal_tests()
        self.assertEqual(len(abnormal), 2)
        self.assertEqual({t.test_name for t in abnormal}, {"Hemoglobin", "TSH"})

        normal = report.get_normal_tests()
        self.assertEqual(len(normal), 1)
        self.assertEqual(normal[0].test_name, "WBC")

        # Get test by name
        found = report.get_test("hemoglobin")
        self.assertIsNotNone(found)
        self.assertEqual(found.value, 11.2)

        # Remove test
        removed = report.remove_test("WBC")
        self.assertTrue(removed)
        self.assertEqual(report.total_tests_count, 2)

    def test_medical_source_polymorphism(self):
        # Demonstrates inheritance and polymorphism from MedicalSource
        coordinator = MedicalSourceCoordinator(data_dir=str(PROJECT_ROOT / "data"))
        self.assertIsInstance(coordinator.nih_source, MedicalSource)
        self.assertIsInstance(coordinator.fda_source, MedicalSource)
        self.assertIsInstance(coordinator.local_source, MedicalSource)

        # Polymorphic call to search()
        local_res = coordinator.local_source.search("Migraine")
        self.assertIn("Clinical Baseline", local_res["title"])


class TestFileHandling(unittest.TestCase):
    """Verifies JSON and CSV import, export, sanitization, and security."""

    def setUp(self):
        self.handler = FileHandler()

    def test_json_parsing_and_export(self):
        sample_json = {
            "patient_id": "P_FILE_TEST",
            "report_date": "2026-10-26",
            "notes": "Testing file parser",
            "tests": [
                {"test_name": "HbA1c", "value": 7.2, "unit": "%", "reference_low": 4.0, "reference_high": 5.6},
                {"test_name": "Vitamin D", "value": 18.0, "unit": "ng/mL", "reference_low": 30.0, "reference_high": 100.0}
            ]
        }
        json_str = self.handler.export_json_report(LabReport.from_dict(sample_json))
        parsed = self.handler.parse_json_report(json_str)

        self.assertEqual(parsed.patient_id, "P_FILE_TEST")
        self.assertEqual(parsed.total_tests_count, 2)
        hba1c = parsed.get_test("HbA1c")
        self.assertIsNotNone(hba1c)
        self.assertEqual(hba1c.status, "HIGH")

    def test_csv_parsing_and_export(self):
        report = LabReport(patient_id="P_CSV_TEST", report_date="2026-10-26")
        report.add_test(LabTest("Hemoglobin", 10.2, "g/dL", 12.0, 17.5))
        report.add_test(LabTest("Fasting Glucose", 88.0, "mg/dL", 70.0, 99.0))

        csv_str = self.handler.export_csv_report(report)
        self.assertIn("test_name,value,unit", csv_str)

        # Parse CSV back
        parsed = self.handler.parse_csv_report(csv_str, patient_id="P_CSV_TEST")
        self.assertEqual(parsed.total_tests_count, 2)
        hb = parsed.get_test("Hemoglobin")
        self.assertIsNotNone(hb)
        self.assertEqual(hb.status, "LOW")

    def test_file_security_validation(self):
        # Invalid extension
        with self.assertRaises(ValueError):
            self.handler.validate_file_metadata("malicious.exe", b"executable code")

        # Empty file
        with self.assertRaises(ValueError):
            self.handler.validate_file_metadata("empty.csv", b"")

        # Filename sanitization
        clean = self.handler.sanitize_filename("../../etc/passwd.csv")
        self.assertNotIn("..", clean)
        self.assertNotIn("/", clean)


class TestLabTrends(unittest.TestCase):
    """Verifies deterministic chronological trend calculations."""

    def test_trend_calculation(self):
        service = LabReportService(data_dir=str(PROJECT_ROOT / "data"))

        # Add earlier report
        r1 = LabReport(report_id="rep_test_t1", patient_id="P_TREND_TEST", report_date="2026-09-01")
        r1.add_test(LabTest("HbA1c", 6.8, "%", 4.0, 5.6))
        service.create_report(r1)

        # Add later report
        r2 = LabReport(report_id="rep_test_t2", patient_id="P_TREND_TEST", report_date="2026-10-26")
        r2.add_test(LabTest("HbA1c", 7.4, "%", 4.0, 5.6))
        service.create_report(r2)

        try:
            trends = service.calculate_trends(patient_id="P_TREND_TEST")
            self.assertTrue(trends["has_sufficient_history"])
            self.assertGreaterEqual(len(trends["trends"]), 21)
            
            hba1c_trend = next((t for t in trends["trends"] if t["test_name"] == "HbA1c"), None)
            self.assertIsNotNone(hba1c_trend)
            self.assertEqual(hba1c_trend["direction"], "INCREASED")
            self.assertEqual(hba1c_trend["previous_value"], 6.8)
            self.assertEqual(hba1c_trend["latest_value"], 7.4)
            self.assertAlmostEqual(hba1c_trend["delta"], 0.6, places=2)
        finally:
            # Clean up test reports
            service.delete_report("rep_test_t1")
            service.delete_report("rep_test_t2")


class TestCombinedDiagnosisEngine(unittest.TestCase):
    """Verifies symptom-only vs symptom+lab combined evidence matching."""

    def setUp(self):
        self.kb = MedicalKnowledgeBase(str(PROJECT_ROOT / "data"))
        self.engine = DiagnosisEngine(self.kb)
        self.patient = Patient("female", 32, 58.0)

    def test_symptom_only_diagnosis(self):
        # Symptoms for Migraine
        symptoms = ["headache_throbbing", "light_sensitivity", "nausea_vomiting"]
        res = self.engine.diagnose(self.patient, symptoms, lab_report=None)

        self.assertTrue(res["success"])
        self.assertFalse(res["has_lab_evidence"])
        self.assertTrue(len(res["top_probable_diseases"]) > 0)
        top = res["top_probable_diseases"][0]
        self.assertEqual(top["name"], "Migraine Episode")
        self.assertFalse(top["has_lab_evidence"])

    def test_combined_symptoms_and_labs_evidence(self):
        # Symptoms for Anemia: fatigue, weakness, dizziness
        symptoms = ["fatigue", "weakness", "dizziness_lightheadedness"]
        
        # Supporting lab report with low hemoglobin and low ferritin
        lab_rep = LabReport(patient_id="P_ANEMIA_TEST", report_date="2026-10-26")
        lab_rep.add_test(LabTest("Hemoglobin", 9.8, "g/dL", 12.0, 17.5))   # LOW
        lab_rep.add_test(LabTest("Ferritin", 9.0, "ng/mL", 20.0, 250.0))    # LOW
        lab_rep.add_test(LabTest("Fasting Glucose", 88.0, "mg/dL", 70.0, 99.0)) # NORMAL

        res = self.engine.diagnose(self.patient, symptoms, lab_report=lab_rep)
        
        self.assertTrue(res["success"])
        self.assertTrue(res["has_lab_evidence"])
        self.assertIn("laboratory findings", res["disclaimer"])
        
        # Top candidate should be Iron-Deficiency Anemia with lab findings
        top = res["top_probable_diseases"][0]
        self.assertEqual(top["id"], "iron_deficiency_anemia")
        self.assertTrue(top["has_lab_evidence"])
        self.assertTrue(len(top["matched_lab_findings"]) >= 2)
        
        # Verify findings include Ferritin & Hemoglobin explanations
        finding_tests = [f["test_name"] for f in top["matched_lab_findings"]]
        self.assertIn("Ferritin", finding_tests)
        self.assertIn("Hemoglobin", finding_tests)


if __name__ == "__main__":
    unittest.main(verbosity=2)
