"""
QuickDiagnosis - Core Diagnostic Engine & Knowledgebase
Re-exports DiagnosisEngine and MedicalKnowledgeBase for root-level modules and backwards compatibility.
"""

from backend.app.services.diagnosis_service import (
    MedicalKnowledgeBase,
    DiagnosisEngine
)

# Alias for backwards compatibility
DiagnosticEngine = DiagnosisEngine

__all__ = [
    "MedicalKnowledgeBase",
    "DiagnosisEngine",
    "DiagnosticEngine"
]
