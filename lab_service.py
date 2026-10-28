"""
QuickDiagnosis - Laboratory Report Service & File Handler
Exports FileHandler and LabReportService unified with backend services.
"""

from backend.app.utils.file_handler import FileHandler
from backend.app.services.lab_service import LabReportService
from models import LabTest, LabReport
from lab_rules import LabRules

__all__ = ["FileHandler", "LabReportService", "LabTest", "LabReport", "LabRules"]
