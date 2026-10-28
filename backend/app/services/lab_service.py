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
        p = Path(data_dir)
        if not (p / "lab_test_definitions.json").exists():
            alt_candidates = [
                Path(__file__).resolve().parent.parent.parent.parent / "data",
                Path.cwd() / "data",
                Path("/var/task/data")
            ]
            for alt in alt_candidates:
                if (alt / "lab_test_definitions.json").exists():
                    p = alt
                    break
        self.data_dir = p
        self.reports_file = self.data_dir / "lab_reports.json"
        self.reports_dir = self.data_dir / "lab_reports"
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            pass
        
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
            rep = self._memory_reports.get(report_id)
            if rep:
                return rep
            
            # Check individual report file on disk (in case written by another service instance)
            indiv_file = self.reports_dir / f"{report_id}.json"
            if indiv_file.exists():
                try:
                    with open(indiv_file, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        rep = LabReport.from_dict(d)
                        self._memory_reports[report_id] = rep
                        return rep
                except Exception:
                    pass

            # Check master index on disk
            try:
                if self.reports_file.exists():
                    with open(self.reports_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if item.get("report_id") == report_id:
                                    rep = LabReport.from_dict(item)
                                    self._memory_reports[report_id] = rep
                                    return rep
            except Exception:
                pass

            return None

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
    # Import & Export Orchestration
    # -------------------------------------------------------------------------
    def import_report_file(self, filename: str, file_bytes: bytes, patient_id: str = "P_CURRENT") -> LabReport:
        """Parses, validates, and stores an uploaded JSON, CSV, PDF, or image lab report file."""
        self.file_handler.validate_file_metadata(filename, file_bytes)
        ext = Path(filename).suffix.lower()
        
        if ext == ".json":
            report = self.file_handler.parse_json_report(file_bytes)
        elif ext == ".csv":
            report = self.file_handler.parse_csv_report(file_bytes, patient_id=patient_id)
        elif ext == ".pdf":
            report = self.file_handler.parse_pdf_report(file_bytes, patient_id=patient_id)
        elif ext in {".jpg", ".jpeg", ".png"}:
            report = self.file_handler.parse_image_report(file_bytes, filename=filename, patient_id=patient_id)
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
        Calculates deterministic chronological trends across laboratory reports.
        Compares latest test findings against preceding results.
        Returns ALL standard biomarkers with reference ranges:
        - When no reports exist: previous, latest, delta, and direction are None (displayed as '--').
        - When 1 report exists: latest is populated, previous/delta are None (displayed as '--').
        - When 2+ reports exist: calculates exact delta, % change, and trend directions.
        Zero AI or generative prediction used.
        """
        with self.lock:
            reports = list(self._memory_reports.values())

        if patient_id and patient_id != "all":
            reports = [r for r in reports if r.patient_id == patient_id]

        # Sort chronologically ascending (oldest first)
        reports.sort(key=lambda r: (r.report_date, r.created_at))

        # Group test readings by canonical test name: test_name -> list of readings
        test_history: Dict[str, List[Dict[str, Any]]] = {}
        for r in reports:
            for t in r.tests:
                t_canonical = self.rules.resolve_canonical_name(t.test_name)
                if t_canonical not in test_history:
                    test_history[t_canonical] = []
                test_history[t_canonical].append({
                    "date": r.report_date,
                    "value": t.value,
                    "unit": t.unit,
                    "status": t.status,
                    "reference_low": t.reference_low,
                    "reference_high": t.reference_high
                })

        # Load all canonical definitions
        all_defs = self.rules.get_all_definitions()
        seen_tests = set()
        trend_results = []

        for defn in all_defs:
            test_name = defn["test_name"]
            seen_tests.add(test_name.lower())
            unit = defn.get("unit", "")
            ref_low = defn.get("reference_low")
            ref_high = defn.get("reference_high")
            history = test_history.get(test_name, [])

            if len(history) >= 2:
                prev = history[-2]
                curr = history[-1]
                delta = round(curr["value"] - prev["value"], 3)
                pct_change = round((delta / prev["value"]) * 100, 1) if prev["value"] != 0 else 0.0

                if abs(delta) < 0.001 or pct_change == 0:
                    direction = "STABLE"
                    icon = "●"
                elif delta > 0:
                    direction = "INCREASED"
                    icon = "▲"
                else:
                    direction = "DECREASED"
                    icon = "▼"

                trend_results.append({
                    "test_name": test_name,
                    "unit": curr.get("unit") or unit,
                    "previous_date": prev["date"],
                    "previous_value": prev["value"],
                    "previous_status": prev["status"],
                    "latest_date": curr["date"],
                    "latest_value": curr["value"],
                    "latest_status": curr["status"],
                    "reference_low": curr.get("reference_low", ref_low),
                    "reference_high": curr.get("reference_high", ref_high),
                    "delta": delta,
                    "pct_change": pct_change,
                    "direction": direction,
                    "icon": icon,
                    "readings_count": len(history),
                    "has_data": True
                })
            elif len(history) == 1:
                curr = history[-1]
                trend_results.append({
                    "test_name": test_name,
                    "unit": curr.get("unit") or unit,
                    "previous_date": None,
                    "previous_value": None,
                    "previous_status": None,
                    "latest_date": curr["date"],
                    "latest_value": curr["value"],
                    "latest_status": curr["status"],
                    "reference_low": curr.get("reference_low", ref_low),
                    "reference_high": curr.get("reference_high", ref_high),
                    "delta": None,
                    "pct_change": None,
                    "direction": None,
                    "icon": None,
                    "readings_count": 1,
                    "has_data": True
                })
            else:
                # No data yet: keep biomarker name and reference range, values as None (displayed as '--')
                trend_results.append({
                    "test_name": test_name,
                    "unit": unit,
                    "previous_date": None,
                    "previous_value": None,
                    "previous_status": None,
                    "latest_date": None,
                    "latest_value": None,
                    "latest_status": None,
                    "reference_low": ref_low,
                    "reference_high": ref_high,
                    "delta": None,
                    "pct_change": None,
                    "direction": None,
                    "icon": None,
                    "readings_count": 0,
                    "has_data": False
                })

        # Also add any non-standard tests uploaded by the user
        for custom_name, history in test_history.items():
            if custom_name.lower() in seen_tests:
                continue
            curr = history[-1]
            if len(history) >= 2:
                prev = history[-2]
                delta = round(curr["value"] - prev["value"], 3)
                pct_change = round((delta / prev["value"]) * 100, 1) if prev["value"] != 0 else 0.0
                dir_str = "INCREASED" if delta > 0 else ("DECREASED" if delta < 0 else "STABLE")
                icon_str = "▲" if delta > 0 else ("▼" if delta < 0 else "●")
                trend_results.append({
                    "test_name": custom_name,
                    "unit": curr.get("unit", ""),
                    "previous_date": prev["date"],
                    "previous_value": prev["value"],
                    "previous_status": prev["status"],
                    "latest_date": curr["date"],
                    "latest_value": curr["value"],
                    "latest_status": curr["status"],
                    "reference_low": curr.get("reference_low"),
                    "reference_high": curr.get("reference_high"),
                    "delta": delta,
                    "pct_change": pct_change,
                    "direction": dir_str,
                    "icon": icon_str,
                    "readings_count": len(history),
                    "has_data": True
                })
            else:
                trend_results.append({
                    "test_name": custom_name,
                    "unit": curr.get("unit", ""),
                    "previous_date": None,
                    "previous_value": None,
                    "previous_status": None,
                    "latest_date": curr["date"],
                    "latest_value": curr["value"],
                    "latest_status": curr["status"],
                    "reference_low": curr.get("reference_low"),
                    "reference_high": curr.get("reference_high"),
                    "delta": None,
                    "pct_change": None,
                    "direction": None,
                    "icon": None,
                    "readings_count": 1,
                    "has_data": True
                })

        return {
            "has_sufficient_history": len(reports) >= 2,
            "total_reports": len(reports),
            "analyzed_tests_count": sum(1 for t in trend_results if t.get("has_data")),
            "earliest_report_date": reports[0].report_date if reports else None,
            "latest_report_date": reports[-1].report_date if reports else None,
            "trends": trend_results
        }
