import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestFastAPILabEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("QuickDiagnosis", res.text)
        self.assertIn("Lab Reports", res.text)

    def test_get_lab_definitions(self):
        res = self.client.get("/api/lab-reports/definitions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("definitions", data)
        self.assertGreaterEqual(len(data["definitions"]), 15)

    def test_get_lab_reports(self):
        res = self.client.get("/api/lab-reports")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reports", data)
        self.assertTrue(data.get("success"))

    def test_get_lab_trends(self):
        res = self.client.get("/api/lab-reports/trends")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("trends", data["data"])

    def test_create_and_delete_report(self):
        new_report = {
            "patient_id": "P_TEST_API",
            "report_date": "2026-10-26",
            "tests": [
                {
                    "test_name": "Fasting Glucose",
                    "value": 140,
                    "unit": "mg/dL",
                    "reference_low": 70,
                    "reference_high": 99
                }
            ]
        }
        res = self.client.post("/api/lab-reports", json=new_report)
        self.assertEqual(res.status_code, 200)
        created = res.json()
        report_id = created["report"]["report_id"]
        self.assertTrue(report_id)
        self.assertEqual(created["report"]["tests"][0]["status"], "HIGH")

        # Get specific report
        res_get = self.client.get(f"/api/lab-reports/{report_id}")
        self.assertEqual(res_get.status_code, 200)

        # Export as json
        res_exp_json = self.client.get(f"/api/lab-reports/{report_id}/export?format=json")
        self.assertEqual(res_exp_json.status_code, 200)

        # Export as csv
        res_exp_csv = self.client.get(f"/api/lab-reports/{report_id}/export?format=csv")
        self.assertEqual(res_exp_csv.status_code, 200)

        # Delete report
        res_del = self.client.delete(f"/api/lab-reports/{report_id}")
        self.assertEqual(res_del.status_code, 200)

    def test_diagnose_with_attached_lab(self):
        # Symptom only diagnosis
        payload_symptom = {
            "symptoms": ["fatigue", "fever", "cough"]
        }
        res_symp = self.client.post("/api/diagnose", json=payload_symptom)
        self.assertEqual(res_symp.status_code, 200)
        data_symp = res_symp.json()
        self.assertIn("top_probable_diseases", data_symp)
        self.assertIn("disclaimer", data_symp)
        self.assertFalse(data_symp.get("has_lab_evidence"))

        # Combined diagnosis with lab report rep_demo_followup (which has low hemoglobin/ferritin)
        payload_combined = {
            "symptoms": ["fatigue", "weakness"],
            "lab_report_id": "rep_demo_followup"
        }
        res_comb = self.client.post("/api/diagnose", json=payload_combined)
        self.assertEqual(res_comb.status_code, 200)
        data_comb = res_comb.json()
        self.assertIn("top_probable_diseases", data_comb)
        self.assertTrue(data_comb.get("has_lab_evidence"))
        self.assertEqual(data_comb.get("attached_lab_report_id"), "rep_demo_followup")
        
        # Verify iron deficiency anemia receives matched lab findings
        top_disease = data_comb["top_probable_diseases"][0]
        self.assertEqual(top_disease["id"], "iron_deficiency_anemia")
        self.assertTrue(top_disease["has_lab_evidence"])
        self.assertGreater(len(top_disease["matched_lab_findings"]), 0)


if __name__ == "__main__":
    unittest.main()
