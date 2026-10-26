"""
QuickDiagnosis - Lab Report Service
Provides CRUD operations, disk persistence, chronological trend analysis,
and import/export orchestration for laboratory reports.
"""

import json
import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.rules.lab_rules import LabRules
from backend.app.utils.file_handler import FileHandler


class LabReportService:
    """
    Manages laboratory report lifecycle, persistence, and deterministic trend calculations.
    Thread-safe disk operations with atomic index writes.
    """
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.reports_file = self.data_dir / "lab_reports.json"
        self.reports_dir = self.data_dir / "lab_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.lock = threading.Lock()
        self.rules = LabRules(str(self.data_dir / "lab_test_definitions.json"))
        self.file_handler = FileHandler(self.rules)
        
        self._memory_reports: Dict[str, LabReport] = {}
        self._load_reports_from_disk()

    def _load_reports_from_disk(self) -> None:
        """Loads reports from master index file."""
        with self.lock:
            if not self.reports_file.exists():
                return
            try:
                with open(self.reports_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            rep = LabReport.from_dict(item)
                            self._memory_reports[rep.report_id] = rep
            except Exception as e:
                print(f"[LabReportService] Warning: Could not read {self.reports_file}: {e}")

    def _save_reports_to_disk(self) -> None:
        """Persists all in-memory reports atomically to disk."""
        reports_list = [r.to_dict() for r in self._memory_reports.values()]
        temp_file = self.data_dir / "lab_reports.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(reports_list, f, indent=2, ensure_ascii=False)
            if temp_file.exists():
                os.replace(temp_file, self.reports_file)
        except Exception as e:
            print(f"[LabReportService] Error saving reports: {e}")

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------
    def get_all_reports(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns sorted list of reports (newest first)."""
        with self.lock:
            all_reps = list(self._memory_reports.values())
        
        if patient_id and patient_id != "all":
            all_reps = [r for r in all_reps if r.patient_id == patient_id]

        # Sort descending by report date
        all_reps.sort(key=lambda r: (r.report_date, r.created_at), reverse=True)
        return [r.to_dict() for r in all_reps]

    def get_report_by_id(self, report_id: str) -> Optional[LabReport]:
        """Retrieves a single LabReport object by ID."""
        with self.lock:
            return self._memory_reports.get(report_id)

    def create_report(self, report: LabReport) -> LabReport:
        """Saves a new laboratory report."""
        with self.lock:
            self._memory_reports[report.report_id] = report
            self._save_reports_to_disk()
            
            # Also save individual report JSON file
            indiv_file = self.reports_dir / f"{report.report_id}.json"
            try:
                with open(indiv_file, "w", encoding="utf-8") as f:
                    json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        return report

    def update_report(self, report_id: str, updated_report: LabReport) -> Optional[LabReport]:
        """Updates an existing report."""
        with self.lock:
            if report_id not in self._memory_reports:
                return None
            
            self._memory_reports[report_id] = updated_report
            self._save_reports_to_disk()
            
            indiv_file = self.reports_dir / f"{report_id}.json"
            try:
                with open(indiv_file, "w", encoding="utf-8") as f:
                    json.dump(updated_report.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        return updated_report

    def delete_report(self, report_id: str) -> bool:
        """Deletes a report by ID."""
        with self.lock:
            if report_id in self._memory_reports:
                del self._memory_reports[report_id]
                self._save_reports_to_disk()
                
                indiv_file = self.reports_dir / f"{report_id}.json"
                if indiv_file.exists():
                    try:
                        indiv_file.unlink()
                    except Exception:
                        pass
                return True
            return False

    # -------------------------------------------------------------------------
    # Import & Export Orchestration
    # -------------------------------------------------------------------------
    def import_report_file(self, filename: str, file_bytes: bytes, patient_id: str = "P_CURRENT") -> LabReport:
        """Parses, validates, and stores an uploaded JSON or CSV lab report file."""
        self.file_handler.validate_file_metadata(filename, file_bytes)
        ext = Path(filename).suffix.lower()
        
        if ext == ".json":
            report = self.file_handler.parse_json_report(file_bytes)
        elif ext == ".csv":
            report = self.file_handler.parse_csv_report(file_bytes, patient_id=patient_id)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Save to database
        self.create_report(report)
        return report

    def export_report_content(self, report_id: str, export_format: str = "json") -> Tuple[str, str, str]:
        """
        Exports a report in JSON or CSV format.
        Returns: (content_string, media_type, filename)
        """
        report = self.get_report_by_id(report_id)
        if not report:
            raise KeyError(f"Report '{report_id}' does not exist.")

        clean_fmt = export_format.strip().lower()
        if clean_fmt == "csv":
            content = self.file_handler.export_csv_report(report)
            media_type = "text/csv"
            filename = f"lab_report_{report.report_date}_{report.report_id}.csv"
        else:
            content = self.file_handler.export_json_report(report)
            media_type = "application/json"
            filename = f"lab_report_{report.report_date}_{report.report_id}.json"

        return content, media_type, filename

    # -------------------------------------------------------------------------
    # Deterministic Trend Analysis
    # -------------------------------------------------------------------------
    def calculate_trends(self, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates deterministic chronological trends across multiple lab reports.
        Compares latest test findings against preceding results.
        Zero AI or generative prediction used.
        """
        with self.lock:
            reports = list(self._memory_reports.values())

        if patient_id and patient_id != "all":
            reports = [r for r in reports if r.patient_id == patient_id]

        if len(reports) < 2:
            return {
                "has_sufficient_history": False,
                "message": "At least 2 chronological reports are required to calculate laboratory trends.",
                "total_reports": len(reports),
                "trends": []
            }

        # Sort chronologically ascending (oldest first)
        reports.sort(key=lambda r: (r.report_date, r.created_at))

        # Group test readings by canonical test name: test_name -> list of (date, value, unit, status)
        test_history: Dict[str, List[Dict[str, Any]]] = {}
        for r in reports:
            for t in r.tests:
                if t.test_name not in test_history:
                    test_history[t.test_name] = []
                test_history[t.test_name].append({
                    "date": r.report_date,
                    "value": t.value,
                    "unit": t.unit,
                    "status": t.status,
                    "reference_low": t.reference_low,
                    "reference_high": t.reference_high
                })

        trend_results = []
        for test_name, history in test_history.items():
            if len(history) < 2:
                continue
            
            prev = history[-2]
            curr = history[-1]
            
            delta = round(curr["value"] - prev["value"], 3)
            if prev["value"] != 0:
                pct_change = round((delta / prev["value"]) * 100, 1)
            else:
                pct_change = 0.0

            if abs(delta) < 0.001 or pct_change == 0:
                direction = "STABLE"
                icon = "➔"
            elif delta > 0:
                direction = "INCREASED"
                icon = "▲"
            else:
                direction = "DECREASED"
                icon = "▼"

            trend_results.append({
                "test_name": test_name,
                "unit": curr["unit"],
                "previous_date": prev["date"],
                "previous_value": prev["value"],
                "previous_status": prev["status"],
                "latest_date": curr["date"],
                "latest_value": curr["value"],
                "latest_status": curr["status"],
                "reference_low": curr["reference_low"],
                "reference_high": curr["reference_high"],
                "delta": delta,
                "pct_change": pct_change,
                "direction": direction,
                "icon": icon,
                "readings_count": len(history)
            })

        # Sort trends: abnormal latest tests first, then alphabetical
        trend_results.sort(
            key=lambda x: (0 if x["latest_status"] in ("LOW", "HIGH") else 1, x["test_name"])
        )

        return {
            "has_sufficient_history": True,
            "total_reports": len(reports),
            "analyzed_tests_count": len(trend_results),
            "earliest_report_date": reports[0].report_date,
            "latest_report_date": reports[-1].report_date,
            "trends": trend_results
        }
