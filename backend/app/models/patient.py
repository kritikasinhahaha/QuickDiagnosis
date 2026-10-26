"""
QuickDiagnosis - Patient Domain Model (OOP Architecture)
Encapsulates patient biophysics, demographics, and age/weight categorization.
"""

from typing import Dict, Any


class Patient:
    """Encapsulates patient demographic and biophysical parameters."""
    def __init__(self, gender: str, age: int, weight: float, patient_id: str = "P_CURRENT"):
        self.patient_id = (patient_id or "P_CURRENT").strip()
        self.gender = (gender or "other").strip().lower()
        self.age = max(0, int(age))
        self.weight = max(1.0, float(weight))

    @property
    def age_group(self) -> str:
        """Categorizes age into clinical demographic stages."""
        if self.age < 5:
            return "infant_toddler"
        elif self.age < 13:
            return "child"
        elif self.age < 20:
            return "teenager"
        elif self.age < 40:
            return "young_adult"
        elif self.age < 60:
            return "middle_aged"
        else:
            return "senior"

    @property
    def estimated_bmi_category(self) -> str:
        """Estimates general weight category based on standard weight heuristics."""
        if self.weight < 48:
            return "underweight"
        elif self.weight <= 72:
            return "normal"
        elif self.weight <= 88:
            return "overweight"
        else:
            return "obese"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "gender": self.gender,
            "age": self.age,
            "weight": self.weight,
            "age_group": self.age_group,
            "weight_category": self.estimated_bmi_category
        }

    def __repr__(self) -> str:
        return f"<Patient {self.patient_id} ({self.gender}, age {self.age}, {self.weight}kg)>"
