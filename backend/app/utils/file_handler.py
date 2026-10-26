"""
QuickDiagnosis - Secure File Handler (JSON & CSV)
Implements file reading, parsing, validation, sanitization,
serialization, and export for laboratory reports.
"""

import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.rules.lab_rules import LabRules


class FileHandler:
    """
    Secure file handling utility for laboratory report files.
    Supports JSON and CSV formats with strict data sanitization and schema validation.
    """
    MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB limit
    ALLOWED_EXTENSIONS = {".json", ".csv"}

    def __init__(self, lab_rules: Optional[LabRules] = None):
        self.rules = lab_rules or LabRules()

    def sanitize_filename(self, filename: str) -> str:
        """Removes dangerous path traversal characters and non-alphanumeric symbols."""
        base = os.path.basename(filename)
        clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
        return clean[:100]

    def validate_file_metadata(self, filename: str, file_bytes: bytes) -> None:
        """Validates file extension and size constraints."""
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Only .json and .csv files are permitted.")
        
        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File exceeds maximum allowed size of {self.MAX_FILE_SIZE_BYTES // (1024*1024)} MB.")

        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

    # -------------------------------------------------------------------------
    # JSON Parsing & Serialization
    # -------------------------------------------------------------------------
    def parse_json_report(self, json_content: Union[str, bytes]) -> LabReport:
        """
        Parses JSON content string or bytes into a validated LabReport object.
        """
        if isinstance(json_content, bytes):
            try:
                decoded = json_content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = json_content.decode("latin-1")
        else:
            decoded = json_content

        try:
            data = json.loads(decoded)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON syntax: {e.msg} at line {e.lineno}")

        if not isinstance(data, dict):
            # If array of tests was uploaded directly without wrapper
            if isinstance(data, list):
                data = {"tests": data}
            else:
                raise ValueError("JSON file must contain an object or an array of laboratory tests.")

        # Parse tests list
        raw_tests = data.get("tests", [])
        if not raw_tests:
            raise ValueError("JSON report contains no laboratory tests under 'tests'.")

        tests_list: List[LabTest] = []
        for i, item in enumerate(raw_tests):
            if not isinstance(item, dict):
                continue
            
            raw_name = item.get("test_name") or item.get("name") or item.get("test")
            if not raw_name:
                continue

            canonical_name = self.rules.resolve_canonical_name(str(raw_name))
            raw_val = item.get("value")
            if raw_val is None:
                continue

            try:
                val_float = float(raw_val)
            except (ValueError, TypeError):
                continue

            # Prioritize uploaded reference range; fallback to canonical definition if absent
            ref_low = item.get("reference_low")
            ref_high = item.get("reference_high")
            
            low_val = None
            high_val = None
            if ref_low is not None and str(ref_low).strip() != "":
                try:
                    low_val = float(ref_low)
                except (ValueError, TypeError):
                    pass
            
            if ref_high is not None and str(ref_high).strip() != "":
                try:
                    high_val = float(ref_high)
                except (ValueError, TypeError):
                    pass

            # If user report omitted range, query configured rules
            if low_val is None and high_val is None:
                low_val, high_val = self.rules.get_canonical_reference_range(canonical_name)

            unit = str(item.get("unit") or "").strip()
            if not unit:
                unit = self.rules.get_canonical_unit(canonical_name)

            tests_list.append(
                LabTest(
                    test_name=canonical_name,
                    value=val_float,
                    unit=unit,
                    reference_low=low_val,
                    reference_high=high_val
                )
            )

        if not tests_list:
            raise ValueError("No valid laboratory tests could be extracted from JSON data.")

        return LabReport(
            report_id=data.get("report_id"),
            patient_id=data.get("patient_id") or "P_ANONYMOUS",
            report_date=data.get("report_date"),
            tests=tests_list,
            notes=data.get("notes", "")
        )

    def export_json_report(self, report: LabReport) -> str:
        """Serializes a LabReport object to an indented JSON string."""
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)

    # -------------------------------------------------------------------------
    # CSV Parsing & Serialization
    # -------------------------------------------------------------------------
    def parse_csv_report(self, csv_content: Union[str, bytes], patient_id: str = "P_ANONYMOUS", report_date: Optional[str] = None) -> LabReport:
        """
        Parses CSV content into a validated LabReport object.
        Supports standard header formats:
        test_name,value,unit,reference_low,reference_high
        """
        if isinstance(csv_content, bytes):
            try:
                decoded = csv_content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = csv_content.decode("latin-1")
        else:
            decoded = csv_content

        f = io.StringIO(decoded.strip())
        reader = csv.reader(f)
        
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty.")

        # Normalize header indices
        header_map: Dict[str, int] = {}
        for idx, col in enumerate(raw_headers):
            c_clean = col.strip().lower().replace(" ", "_")
            header_map[c_clean] = idx

        # Find mandatory columns: test_name and value
        name_idx = None
        for candidate in ["test_name", "test", "name", "parameter", "analyte"]:
            if candidate in header_map:
                name_idx = header_map[candidate]
                break

        val_idx = None
        for candidate in ["value", "result", "val", "reading", "numeric_value"]:
            if candidate in header_map:
                val_idx = header_map[candidate]
                break

        if name_idx is None or val_idx is None:
            raise ValueError(
                "CSV must contain at least 'test_name' (or 'test') and 'value' columns. "
                f"Found columns: {raw_headers}"
            )

        unit_idx = header_map.get("unit") or header_map.get("units")
        low_idx = header_map.get("reference_low") or header_map.get("low") or header_map.get("min")
        high_idx = header_map.get("reference_high") or header_map.get("high") or header_map.get("max")

        tests_list: List[LabTest] = []
        for line_no, row in enumerate(reader, start=2):
            if not row or not any(row):
                continue
            
            if len(row) <= max(name_idx, val_idx):
                continue

            raw_name = row[name_idx].strip()
            raw_val = row[val_idx].strip()
            
            if not raw_name or not raw_val:
                continue

            try:
                val_float = float(raw_val)
            except ValueError:
                continue

            canonical_name = self.rules.resolve_canonical_name(raw_name)
            
            unit = row[unit_idx].strip() if unit_idx is not None and len(row) > unit_idx else ""
            if not unit:
                unit = self.rules.get_canonical_unit(canonical_name)

            low_val = None
            if low_idx is not None and len(row) > low_idx and row[low_idx].strip():
                try:
                    low_val = float(row[low_idx].strip())
                except ValueError:
                    pass

            high_val = None
            if high_idx is not None and len(row) > high_idx and row[high_idx].strip():
                try:
                    high_val = float(row[high_idx].strip())
                except ValueError:
                    pass

            # Fallback to configured ranges if omitted
            if low_val is None and high_val is None:
                low_val, high_val = self.rules.get_canonical_reference_range(canonical_name)

            tests_list.append(
                LabTest(
                    test_name=canonical_name,
                    value=val_float,
                    unit=unit,
                    reference_low=low_val,
                    reference_high=high_val
                )
            )

        if not tests_list:
            raise ValueError("No valid laboratory records could be extracted from the CSV rows.")

        return LabReport(
            patient_id=patient_id,
            report_date=report_date,
            tests=tests_list
        )

    def export_csv_report(self, report: LabReport) -> str:
        """Exports a LabReport object into standard CSV string."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        
        # Standard header
        writer.writerow(["test_name", "value", "unit", "reference_low", "reference_high", "status"])
        
        for t in report.tests:
            writer.writerow([
                t.test_name,
                t.value,
                t.unit,
                t.reference_low if t.reference_low is not None else "",
                t.reference_high if t.reference_high is not None else "",
                t.status
            ])

        return output.getvalue()
