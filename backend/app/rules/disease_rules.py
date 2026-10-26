"""
QuickDiagnosis - Disease Lab Correlation Rules
Defines deterministic, rule-based associations between clinical conditions
and laboratory test patterns (abnormalities and corroborating normals).
"""

from typing import Dict, Any, List, Optional


class DiseaseLabRules:
    """
    Encapsulates medical knowledge rules connecting diseases to expected lab test findings.
    Provides evidence correlation without any generative AI or LLMs.
    """
    
    # Static rule definitions mapping disease IDs to characteristic lab patterns
    # Format:
    # disease_id -> list of rules: {test_name, expected_status, weight, significance, explanation}
    CORRELATION_RULES: Dict[str, List[Dict[str, Any]]] = {
        "iron_deficiency_anemia": [
            {
                "test_name": "Hemoglobin",
                "expected_status": "LOW",
                "weight": 2.8,
                "significance": "High",
                "explanation": "Decreased hemoglobin is the definitive hallmark of anemic syndromes."
            },
            {
                "test_name": "Ferritin",
                "expected_status": "LOW",
                "weight": 3.0,
                "significance": "Pathognomonic",
                "explanation": "Low serum ferritin directly indicates depleted reticuloendothelial iron stores."
            },
            {
                "test_name": "RBC (Red Blood Cells)",
                "expected_status": "LOW",
                "weight": 1.5,
                "significance": "Supporting",
                "explanation": "Reduced total erythrocyte mass commonly accompanies microcytic hypochromic anemia."
            }
        ],
        "influenza_flu": [
            {
                "test_name": "WBC (White Blood Cells)",
                "expected_status": "LOW",
                "weight": 1.2,
                "significance": "Supporting",
                "explanation": "Mild leukopenia or normal leukocyte count frequently characterizes uncomplicated viral influenza."
            },
            {
                "test_name": "WBC (White Blood Cells)",
                "expected_status": "NORMAL",
                "weight": 0.8,
                "significance": "Supporting",
                "explanation": "Normal leukocyte count without marked leukocytosis supports viral over bacterial respiratory etiologies."
            }
        ],
        "urinary_tract_infection": [
            {
                "test_name": "WBC (White Blood Cells)",
                "expected_status": "HIGH",
                "weight": 2.2,
                "significance": "High",
                "explanation": "Systemic leukocytosis reflects an active immune response to ascending bacterial urinary pathogens."
            }
        ],
        "acute_gastroenteritis": [
            {
                "test_name": "Serum Potassium",
                "expected_status": "LOW",
                "weight": 2.0,
                "significance": "High",
                "explanation": "Hypokalemia commonly arises from acute gastrointestinal fluid and electrolyte loss."
            },
            {
                "test_name": "Serum Sodium",
                "expected_status": "LOW",
                "weight": 1.4,
                "significance": "Supporting",
                "explanation": "Hyponatremia reflects dehydrative hypovolemia or hypotonic fluid replacement."
            }
        ],
        "hypothyroidism": [
            {
                "test_name": "TSH (Thyroid Stimulating Hormone)",
                "expected_status": "HIGH",
                "weight": 3.2,
                "significance": "Pathognomonic",
                "explanation": "Marked elevation of pituitary TSH is the sensitive primary screening marker for primary hypothyroidism."
            },
            {
                "test_name": "Total Cholesterol",
                "expected_status": "HIGH",
                "weight": 1.5,
                "significance": "Supporting",
                "explanation": "Impaired hepatic LDL receptor clearance secondary to thyroid deficiency triggers hypercholesterolemia."
            }
        ],
        "gout_arthritis": [
            {
                "test_name": "Uric Acid",
                "expected_status": "HIGH",
                "weight": 3.0,
                "significance": "Pathognomonic",
                "explanation": "Hyperuricemia promotes monosodium urate crystal supersaturation in articular synovial tissues."
            }
        ],
        "kidney_stones": [
            {
                "test_name": "Serum Creatinine",
                "expected_status": "HIGH",
                "weight": 1.8,
                "significance": "Moderate",
                "explanation": "Transient creatinine elevation can indicate post-renal obstructive nephropathy from calculi."
            },
            {
                "test_name": "Uric Acid",
                "expected_status": "HIGH",
                "weight": 2.0,
                "significance": "Supporting",
                "explanation": "Hyperuricosuria and elevated circulating uric acid represent major risks for radiolucent uric acid stones."
            }
        ],
        "hypertension_warning": [
            {
                "test_name": "Serum Sodium",
                "expected_status": "HIGH",
                "weight": 1.2,
                "significance": "Supporting",
                "explanation": "Hypernatremia and expanded intravascular volume contribute to elevated systemic vascular resistance."
            },
            {
                "test_name": "Serum Creatinine",
                "expected_status": "HIGH",
                "weight": 1.5,
                "significance": "Supporting",
                "explanation": "Renal microvascular nephrosclerosis can elevate serum creatinine in uncontrolled hypertension."
            }
        ]
    }

    @classmethod
    def evaluate_lab_evidence(
        cls,
        disease_id: str,
        lab_results_by_name: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates a patient's lab results against the disease's correlation rules.
        Returns:
            - score_boost: float (numeric evidence multiplier)
            - matched_findings: list of corroborating findings with clinical explanations
        """
        rules = cls.CORRELATION_RULES.get(disease_id, [])
        if not rules or not lab_results_by_name:
            return {"score_boost": 0.0, "matched_findings": []}

        score_boost = 0.0
        matched_findings = []

        for rule in rules:
            target_test = rule["test_name"].lower()
            expected_status = rule["expected_status"]

            # Check if patient lab contains this test
            matching_test = None
            for user_test_name, test_obj in lab_results_by_name.items():
                if target_test in user_test_name.lower() or user_test_name.lower() in target_test:
                    matching_test = test_obj
                    break

            if matching_test:
                actual_status = getattr(matching_test, "status", None) or matching_test.get("status")
                actual_val = getattr(matching_test, "value", None) or matching_test.get("value")
                unit = getattr(matching_test, "unit", "") or matching_test.get("unit", "")

                if actual_status == expected_status:
                    score_boost += float(rule["weight"])
                    matched_findings.append({
                        "test_name": rule["test_name"],
                        "actual_value": actual_val,
                        "unit": unit,
                        "status": actual_status,
                        "expected_status": expected_status,
                        "significance": rule["significance"],
                        "explanation": rule["explanation"]
                    })

        return {
            "score_boost": score_boost,
            "matched_findings": matched_findings
        }
