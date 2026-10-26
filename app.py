"""
QuickDiagnosis - Unified Application Entry Point
Exposes FastAPI application compliant with local execution,
uvicorn ASGI server, and Vercel serverless deployment.
"""

import sys
import os

# Ensure root directory is on sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app

# Backwards compatibility exports for testing and external runners
from backend.app.models.patient import Patient
from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.services.diagnosis_service import MedicalKnowledgeBase, DiagnosisEngine
from backend.app.services.medical_source_service import MedicalSourceCoordinator

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" QUICKDIAGNOSIS MEDICAL ASSESSMENT SYSTEM (FastAPI)")
    print(" Serving on http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=5000, reload=True)
