"""
QuickDiagnosis - LabReport Domain Model (OOP Architecture)
Encapsulates complete laboratory reports, ordered test lists,
abnormal filter queries, and dictionary/JSON conversion.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.models.lab_test import LabTest


class LabReport:
    """
    Represents an entire clinical laboratory report for a patient.
    Maintains a list of LabTest objects and provides query methods.
    """
    def __init__(
        self,
        report_id: Optional[str] = None,
        patient_id: str = "P_ANONYMOUS",
        report_date: Optional[str] = None,
        tests: Optional[List[LabTest]] = None,
        notes: str = "",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        now_utc = datetime.now(timezone.utc)
        self._report_id: str = report_id or f"rep_{uuid.uuid4().hex[:10]}"
        self._patient_id: str = (patient_id or "P_ANONYMOUS").strip()
        self._report_date: str = report_date or now_utc.strftime("%Y-%m-%d")
        self._notes: str = (notes or "").strip()
        self._created_at: str = created_at or now_utc.isoformat()
        self._updated_at: str = updated_at or now_utc.isoformat()
        
        # Internal ordered list of LabTest objects
        self._tests: List[LabTest] = []
        if tests:
            for t in tests:
                self.add_test(t)

    @property
    def report_id(self) -> str:
        return self._report_id

    @property
    def patient_id(self) -> str:
        return self._patient_id

    @property
    def report_date(self) -> str:
        return self._report_date

    @property
    def notes(self) -> str:
        return self._notes

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def tests(self) -> List[LabTest]:
        """Returns shallow copy of tests list to preserve internal encapsulation."""
        return list(self._tests)

    @property
    def total_tests_count(self) -> int:
        return len(self._tests)

    def add_test(self, test: LabTest) -> None:
        """
        Adds or replaces a test in the report.
        If a test with the same name exists, it is replaced with the newer entry.
        """
        if not isinstance(test, LabTest):
            raise TypeError(f"Expected LabTest instance, got {type(test).__name__}")
        
        # Remove existing if present to avoid duplicates
        self._tests = [t for t in self._tests if t.test_name.lower() != test.test_name.lower()]
        self._tests.append(test)
        self._updated_at = datetime.now(timezone.utc).isoformat()

    def remove_test(self, test_name: str) -> bool:
        """Removes a test by name. Returns True if removed, False if not found."""
        target = (test_name or "").strip().lower()
        initial_len = len(self._tests)
        self._tests = [t for t in self._tests if t.test_name.lower() != target]
        if len(self._tests) < initial_len:
            self._updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def get_test(self, test_name: str) -> Optional[LabTest]:
        """Case-insensitive test lookup."""
        target = (test_name or "").strip().lower()
        for t in self._tests:
            if t.test_name.lower() == target:
                return t
        return None

    def get_abnormal_tests(self) -> List[LabTest]:
        """Returns list of tests where status is LOW or HIGH."""
        return [t for t in self._tests if t.is_abnormal]

    def get_normal_tests(self) -> List[LabTest]:
        """Returns list of tests where status is NORMAL."""
        return [t for t in self._tests if t.status == LabTest.STATUS_NORMAL]

    def to_dict_by_name(self) -> Dict[str, float]:
        """Returns dictionary of test names to numeric values: {'HbA1c': 7.2, ...}."""
        return {t.test_name: t.value for t in self._tests}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes complete report to structured dictionary."""
        abnormal = self.get_abnormal_tests()
        return {
            "report_id": self._report_id,
            "patient_id": self._patient_id,
            "report_date": self._report_date,
            "notes": self._notes,
            "total_tests": len(self._tests),
            "abnormal_tests_count": len(abnormal),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "tests": [t.to_dict() for t in self._tests]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabReport":
        """Reconstructs LabReport from dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Invalid lab report data: expected dict, got {type(data).__name__}")
        
        rep_id = data.get("report_id") or data.get("id")
        patient_id = data.get("patient_id") or data.get("user_id") or "P_ANONYMOUS"
        report_date = data.get("report_date") or data.get("date")
        notes = data.get("notes") or ""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        tests_raw = data.get("tests", [])
        tests_list: List[LabTest] = []
        for t_dict in tests_raw:
            try:
                tests_list.append(LabTest.from_dict(t_dict))
            except Exception as e:
                # Skip invalid test item with logging
                print(f"[LabReport.from_dict] Skipping invalid test item: {e}")

        return cls(
            report_id=rep_id,
            patient_id=patient_id,
            report_date=report_date,
            tests=tests_list,
            notes=notes,
            created_at=created_at,
            updated_at=updated_at
        )

    def __repr__(self) -> str:
        return f"<LabReport {self._report_id} ({self._report_date}) tests={len(self._tests)}>"
