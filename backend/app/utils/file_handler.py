"""
QuickDiagnosis - Secure File Handler (PDF, Images, JSON & CSV)
Implements file reading, parsing, validation, sanitization,
serialization, and export for laboratory reports.
Supports real-world clinical document formats: PDF (.pdf),
images (.jpg, .jpeg, .png), standard CSV (.csv), and JSON (.json).
"""

import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.rules.lab_rules import LabRules

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from PIL import Image
except ImportError:
    Image = None


class FileHandler:
    """
    Secure file handling utility for laboratory report files.
    Supports PDF documents, medical image uploads, JSON and CSV formats
    with strict data sanitization and schema validation.
    """
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit for scanned documents & photos
    ALLOWED_EXTENSIONS = {".json", ".csv", ".pdf", ".jpg", ".jpeg", ".png"}

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
            raise ValueError(
                f"Unsupported file format '{ext}'. Accepted formats are PDF (.pdf), "
                "Images (.jpg, .jpeg, .png), CSV (.csv), and JSON (.json)."
            )
        
        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            max_mb = self.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"File exceeds maximum allowed size of {max_mb} MB.")

        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

    # -------------------------------------------------------------------------
    # PDF Parsing
    # -------------------------------------------------------------------------
    def parse_pdf_report(
        self,
        pdf_bytes: bytes,
        patient_id: str = "P_CURRENT",
        report_date: Optional[str] = None
    ) -> LabReport:
        """
        Extracts textual content from a PDF lab report using pypdf,
        then parses clinical biomarkers deterministically with regex.
        """
        extracted_text = ""
        if pypdf:
            try:
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                pages_text = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        pages_text.append(txt)
                extracted_text = "\n".join(pages_text)
            except Exception as e:
                print(f"[FileHandler] Warning: pypdf extraction error: {e}")

        # Fallback stream text extraction if standard extractor found nothing
        if not extracted_text.strip():
            extracted_text = self._fallback_pdf_text_scanner(pdf_bytes)

        if not extracted_text.strip():
            # Scanned document without text layer
            return self._create_fallback_scanned_report(
                patient_id=patient_id,
                report_date=report_date,
                notes="Scanned PDF Lab Document (Please verify values in manual entry)"
            )

        return self.extract_tests_from_text(
            text=extracted_text,
            patient_id=patient_id,
            report_date=report_date,
            default_notes="Clinical PDF Laboratory Report"
        )

    def _fallback_pdf_text_scanner(self, data: bytes) -> str:
        """Fallback regex scanner to recover plain ASCII and Latin strings from raw PDF streams."""
        try:
            raw = data.decode("latin-1", errors="ignore")
            # Extract text blocks inside parentheses (standard PDF text operator: (text) Tj)
            matches = re.findall(r"\(([^)]+)\)\s*(?:Tj|TJ|'|\")", raw)
            if matches:
                return " ".join(matches)
        except Exception:
            pass
        return ""

    # -------------------------------------------------------------------------
    # Image Parsing (.jpg, .jpeg, .png)
    # -------------------------------------------------------------------------
    def parse_image_report(
        self,
        image_bytes: bytes,
        filename: str,
        patient_id: str = "P_CURRENT",
        report_date: Optional[str] = None
    ) -> LabReport:
        """
        Validates medical image files (JPG/PNG). Attempts OCR text extraction
        if pytesseract is available, otherwise returns a structured intake record
        ready for quick confirmation in the manual editor.
        """
        # Validate that the file is indeed a valid image
        if Image:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
            except Exception as e:
                raise ValueError(f"Corrupted or invalid image file: {e}")

        # Attempt OCR if pytesseract is available
        ocr_text = ""
        try:
            import pytesseract
            if Image:
                img = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(img)
        except Exception:
            pass

        if ocr_text.strip():
            return self.extract_tests_from_text(
                text=ocr_text,
                patient_id=patient_id,
                report_date=report_date,
                default_notes=f"Scanned Lab Photo ({filename})"
            )

        # Scanned photo without local OCR installed:
        return self._create_fallback_scanned_report(
            patient_id=patient_id,
            report_date=report_date,
            notes=f"Uploaded Lab Image: {filename} (Review and save in manual table)"
        )

    def _create_fallback_scanned_report(
        self,
        patient_id: str,
        report_date: Optional[str],
        notes: str
    ) -> LabReport:
        """Creates a baseline intake report when a physical scan lacks embedded text."""
        date_str = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Provide standard baseline markers so user has pre-set reference ranges
        standard_markers = [
            ("Hemoglobin", 12.0, 17.5, "g/dL"),
            ("Fasting Glucose", 70.0, 99.0, "mg/dL"),
            ("HbA1c", 4.0, 5.6, "%"),
            ("Vitamin D (25-OH)", 30.0, 100.0, "ng/mL")
        ]
        tests = []
        for name, low, high, unit in standard_markers:
            tests.append(
                LabTest(
                    test_name=name,
                    value=0.0,
                    unit=unit,
                    reference_low=low,
                    reference_high=high
                )
            )

        return LabReport(
            patient_id=patient_id or "P_CURRENT",
            report_date=date_str,
            tests=tests,
            notes=notes
        )

    # -------------------------------------------------------------------------
    # Deterministic Text Parsing for Medical Biomarkers
    # -------------------------------------------------------------------------
    def extract_tests_from_text(
        self,
        text: str,
        patient_id: str = "P_CURRENT",
        report_date: Optional[str] = None,
        default_notes: str = "Uploaded Laboratory Panel"
    ) -> LabReport:
        """
        Parses multi-line clinical text deterministically.
        Extracts report date, biomarker names, numeric results, and units.
        Zero AI / LLMs used: strictly deterministic regex matching.
        """
        # 1. Search for report date in text if not explicitly provided
        final_date = report_date
        if not final_date:
            date_match = re.search(
                r"\b(20\d\d[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/](?:20)?\d{2,4})\b",
                text
            )
            if date_match:
                raw_d = date_match.group(1).replace("/", "-")
                parts = raw_d.split("-")
                if len(parts) == 3:
                    if len(parts[0]) == 4:
                        final_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif len(parts[2]) == 4:
                        final_date = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"

        if not final_date:
            final_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 2. Known clinical search patterns: canonical name -> list of regex name patterns
        test_patterns: Dict[str, List[str]] = {
            "Hemoglobin": [r"\bhemoglobin\b", r"\bhgb\b", r"\bhb\b"],
            "Fasting Glucose": [r"\bfasting\s+glucose\b", r"\bfbs\b", r"\bblood\s+glucose\b", r"\bglucose\b", r"\bblood\s+sugar\b"],
            "HbA1c": [r"\bhba1c\b", r"\ba1c\b", r"\bglycated\s+hemoglobin\b"],
            "WBC (White Blood Cells)": [r"\bwhite\s+blood\s+cells?\b", r"\bwbc\b", r"\btotal\s+leukocyte\s+count\b", r"\btlc\b"],
            "RBC (Red Blood Cells)": [r"\bred\s+blood\s+cells?\b", r"\brbc\b", r"\berythrocytes?\b"],
            "Platelets": [r"\bplatelets?\b", r"\bplatelet\s+count\b", r"\bplt\b", r"\bthrombocytes?\b"],
            "Vitamin D (25-OH)": [r"\bvitamin\s+d\b", r"\b25[- ]oh\s+vit(?:amin)?\s+d\b", r"\bvit\s*d\b"],
            "Vitamin B12": [r"\bvitamin\s+b12\b", r"\bvit\s*b12\b", r"\bcobalamin\b"],
            "Ferritin": [r"\bferritin\b", r"\bserum\s+ferritin\b"],
            "Total Cholesterol": [r"\btotal\s+cholesterol\b", r"\bcholesterol\s+total\b", r"\bserum\s+cholesterol\b", r"\bcholesterol\b"],
            "HDL Cholesterol": [r"\bhdl\s+cholesterol\b", r"\bhdl\b", r"\bhigh\s+density\s+lipoprotein\b"],
            "LDL Cholesterol": [r"\bldl\s+cholesterol\b", r"\bldl\b", r"\blow\s+density\s+lipoprotein\b"],
            "Triglycerides": [r"\btriglycerides?\b", r"\bserum\s+triglycerides?\b", r"\btg\b"],
            "Serum Creatinine": [r"\bserum\s+creatinine\b", r"\bcreatinine\b"],
            "Blood Urea Nitrogen (BUN)": [r"\bblood\s+urea\s+nitrogen\b", r"\bbun\b", r"\burea\b"],
            "Uric Acid": [r"\buric\s+acid\b", r"\bserum\s+uric\s+acid\b"],
            "Total Bilirubin": [r"\btotal\s+bilirubin\b", r"\bbilirubin\s+total\b", r"\bserum\s+bilirubin\b"],
            "ALT (Alanine Aminotransferase)": [r"\balt\b", r"\bsgpt\b", r"\balanine\s+aminotransferase\b"],
            "AST (Aspartate Aminotransferase)": [r"\bast\b", r"\bsgot\b", r"\baspartate\s+aminotransferase\b"],
            "TSH (Thyroid Stimulating Hormone)": [r"\btsh\b", r"\bthyroid\s+stimulating\s+hormone\b", r"\bthyrotropin\b"],
            "Serum Sodium": [r"\bserum\s+sodium\b", r"\bsodium\b", r"\bna\+?\b"],
            "Serum Potassium": [r"\bserum\s+potassium\b", r"\bpotassium\b", r"\bk\+?\b"],
            "Calcium": [r"\bserum\s+calcium\b", r"\bcalcium\b"]
        }

        found_tests: Dict[str, LabTest] = {}
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        for line in lines:
            line_lower = line.lower()
            for canonical_name, patterns in test_patterns.items():
                if canonical_name in found_tests:
                    continue  # already parsed earlier line

                matched_end = 0
                for p in patterns:
                    m = re.search(p, line_lower)
                    if m:
                        matched_end = m.end()
                        break

                if matched_end == 0:
                    continue

                # Test name found on this line! Extract numeric value
                # Search after the biomarker name first to avoid matching digits inside the name (e.g. HbA1c, Vit B12)
                text_after_name = line[matched_end:]
                num_matches = re.findall(r"(?<![0-9\.\-])([0-9]+(?:\.[0-9]+)?)(?![0-9\.\-])", text_after_name)
                if not num_matches:
                    num_matches = re.findall(r"(?<![0-9\.\-])([0-9]+(?:\.[0-9]+)?)(?![0-9\.\-])", line)
                if not num_matches:
                    continue

                val_float = None
                # Check for reference range pattern like "12.0 - 17.5"
                range_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*[-–—to]+\s*([0-9]+(?:\.[0-9]+)?)", text_after_name)
                if not range_match:
                    range_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*[-–—to]+\s*([0-9]+(?:\.[0-9]+)?)", line)
                low_val = None
                high_val = None
                if range_match:
                    try:
                        low_val = float(range_match.group(1))
                        high_val = float(range_match.group(2))
                    except ValueError:
                        pass

                # Pick the reading value:
                for candidate in num_matches:
                    try:
                        cf = float(candidate)
                        # Exclude numbers that are part of the reference range if known
                        if low_val is not None and high_val is not None:
                            if cf == low_val or cf == high_val:
                                continue
                        val_float = cf
                        break
                    except ValueError:
                        continue

                if val_float is None and num_matches:
                    val_float = float(num_matches[0])

                if val_float is None:
                    continue

                # Standard canonical range fallback if not explicitly found in line
                if low_val is None and high_val is None:
                    low_val, high_val = self.rules.get_canonical_reference_range(canonical_name)

                unit = self.rules.get_canonical_unit(canonical_name)

                found_tests[canonical_name] = LabTest(
                    test_name=canonical_name,
                    value=val_float,
                    unit=unit,
                    reference_low=low_val,
                    reference_high=high_val
                )

        tests_list = list(found_tests.values())
        if not tests_list:
            # Fallback if no matching tests found
            return self._create_fallback_scanned_report(
                patient_id=patient_id,
                report_date=final_date,
                notes=default_notes
            )

        return LabReport(
            patient_id=patient_id or "P_CURRENT",
            report_date=final_date,
            tests=tests_list,
            notes=f"{default_notes} ({len(tests_list)} biomarkers parsed)"
        )

    # -------------------------------------------------------------------------
    # JSON Parsing & Serialization
    # -------------------------------------------------------------------------
    def parse_json_report(self, json_content: Union[str, bytes]) -> LabReport:
        """Parses JSON content string or bytes into a validated LabReport object."""
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
            if isinstance(data, list):
                data = {"tests": data}
            else:
                raise ValueError("JSON file must contain an object or an array of laboratory tests.")

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
            patient_id=data.get("patient_id") or "P_CURRENT",
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
    def parse_csv_report(
        self,
        csv_content: Union[str, bytes],
        patient_id: str = "P_CURRENT",
        report_date: Optional[str] = None
    ) -> LabReport:
        """Parses CSV content into a validated LabReport object."""
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

        header_map: Dict[str, int] = {}
        for idx, col in enumerate(raw_headers):
            c_clean = col.strip().lower().replace(" ", "_")
            header_map[c_clean] = idx

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


__all__ = ["FileHandler"]
