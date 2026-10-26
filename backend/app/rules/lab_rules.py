"""
QuickDiagnosis - Lab Rules & Normalization Engine
Configurable laboratory test definitions, alias normalization,
and deterministic reference range resolution.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List


class LabRules:
    """
    Central repository of laboratory test rules and definitions.
    Allows dynamic addition of tests without code changes.
    """
    def __init__(self, definitions_file: Optional[str] = None):
        self._definitions: Dict[str, Dict[str, Any]] = {}
        self._alias_map: Dict[str, str] = {}
        
        # Load from file if provided, else use defaults
        if definitions_file and os.path.exists(definitions_file):
            self.load_definitions(definitions_file)
        else:
            self._init_default_rules()

    def load_definitions(self, filepath: str) -> None:
        """Loads configurable test definitions from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    name = item.get("test_name", "")
                    if name:
                        self._definitions[name.lower()] = item
                        self._alias_map[name.lower()] = name
                        # Also register common abbreviations or IDs
                        test_id = item.get("id", "")
                        if test_id:
                            self._alias_map[test_id.lower()] = name
        except Exception as e:
            print(f"[LabRules] Warning: Failed to load definitions from {filepath}: {e}")
            self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Fallback hardcoded rules if external JSON definition file is absent."""
        defaults = [
            {"test_name": "Hemoglobin", "unit": "g/dL", "reference_low": 12.0, "reference_high": 17.5},
            {"test_name": "Fasting Glucose", "unit": "mg/dL", "reference_low": 70.0, "reference_high": 99.0},
            {"test_name": "HbA1c", "unit": "%", "reference_low": 4.0, "reference_high": 5.6},
            {"test_name": "WBC (White Blood Cells)", "unit": "x10^3/uL", "reference_low": 4.5, "reference_high": 11.0},
            {"test_name": "RBC (Red Blood Cells)", "unit": "x10^6/uL", "reference_low": 4.2, "reference_high": 5.9},
            {"test_name": "Platelets", "unit": "x10^3/uL", "reference_low": 150.0, "reference_high": 450.0},
            {"test_name": "Vitamin D (25-OH)", "unit": "ng/mL", "reference_low": 30.0, "reference_high": 100.0},
            {"test_name": "Vitamin B12", "unit": "pg/mL", "reference_low": 200.0, "reference_high": 900.0},
            {"test_name": "Ferritin", "unit": "ng/mL", "reference_low": 20.0, "reference_high": 250.0},
            {"test_name": "Total Cholesterol", "unit": "mg/dL", "reference_low": 125.0, "reference_high": 200.0},
            {"test_name": "Serum Creatinine", "unit": "mg/dL", "reference_low": 0.6, "reference_high": 1.3},
            {"test_name": "Blood Urea Nitrogen (BUN)", "unit": "mg/dL", "reference_low": 7.0, "reference_high": 20.0},
            {"test_name": "Uric Acid", "unit": "mg/dL", "reference_low": 3.5, "reference_high": 7.2},
            {"test_name": "TSH (Thyroid Stimulating Hormone)", "unit": "uIU/mL", "reference_low": 0.4, "reference_high": 4.0},
            {"test_name": "Serum Sodium", "unit": "mEq/L", "reference_low": 135.0, "reference_high": 145.0},
            {"test_name": "Serum Potassium", "unit": "mEq/L", "reference_low": 3.5, "reference_high": 5.0}
        ]
        for item in defaults:
            name = item["test_name"]
            self._definitions[name.lower()] = item
            self._alias_map[name.lower()] = name

    def resolve_canonical_name(self, raw_name: str) -> str:
        """Resolves user or lab input variations to standardized canonical test names."""
        clean = (raw_name or "").strip().lower()
        if clean in self._alias_map:
            return self._alias_map[clean]

        # Common clinical alias aliases mapping
        common_aliases = {
            "hba1c": "HbA1c",
            "a1c": "HbA1c",
            "glycated hemoglobin": "HbA1c",
            "glucose": "Fasting Glucose",
            "blood sugar": "Fasting Glucose",
            "fasting blood sugar": "Fasting Glucose",
            "hb": "Hemoglobin",
            "hgb": "Hemoglobin",
            "wbc": "WBC (White Blood Cells)",
            "white blood cell": "WBC (White Blood Cells)",
            "white blood count": "WBC (White Blood Cells)",
            "rbc": "RBC (Red Blood Cells)",
            "red blood cell": "RBC (Red Blood Cells)",
            "platelet": "Platelets",
            "plt": "Platelets",
            "vit d": "Vitamin D (25-OH)",
            "vitamin d": "Vitamin D (25-OH)",
            "25-oh vitamin d": "Vitamin D (25-OH)",
            "vit b12": "Vitamin B12",
            "b12": "Vitamin B12",
            "cholesterol": "Total Cholesterol",
            "total cholesterol": "Total Cholesterol",
            "creatinine": "Serum Creatinine",
            "bun": "Blood Urea Nitrogen (BUN)",
            "urea": "Blood Urea Nitrogen (BUN)",
            "uric acid": "Uric Acid",
            "tsh": "TSH (Thyroid Stimulating Hormone)",
            "sodium": "Serum Sodium",
            "na": "Serum Sodium",
            "potassium": "Serum Potassium",
            "k": "Serum Potassium"
        }

        if clean in common_aliases:
            return common_aliases[clean]

        # Fuzzy word containment check against known definitions
        for key, canonical in self._alias_map.items():
            if clean in key or key in clean:
                return canonical

        # Return original title-cased string if no alias matches
        return raw_name.strip().title()

    def get_canonical_reference_range(self, canonical_name: str) -> Tuple[Optional[float], Optional[float]]:
        """Returns the canonical (low, high) reference range tuple for a test."""
        clean = canonical_name.lower()
        defn = self._definitions.get(clean)
        if defn:
            return (defn.get("reference_low"), defn.get("reference_high"))
        return (None, None)

    def get_canonical_unit(self, canonical_name: str) -> str:
        """Returns standard unit for a test."""
        clean = canonical_name.lower()
        defn = self._definitions.get(clean)
        return defn.get("unit", "") if defn else ""

    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Returns list of all available test definitions."""
        return list(self._definitions.values())
