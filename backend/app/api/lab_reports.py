"""
QuickDiagnosis - Lab Reports API Router (FastAPI)
Exposes endpoints for lab report CRUD, file uploads (JSON/CSV),
data export, definition templates, and trend calculations.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.app.models.lab_test import LabTest
from backend.app.models.lab_report import LabReport
from backend.app.services.lab_service import LabReportService

router = APIRouter(prefix="/api/lab-reports", tags=["Lab Reports"])
from pathlib import Path

def _resolve_data_dir() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "data",
        Path.cwd() / "data",
        Path("/var/task/data"),
        Path("data").resolve()
    ]
    for c in candidates:
        if (c / "lab_test_definitions.json").exists():
            return str(c)
    return str(Path(__file__).resolve().parent.parent.parent.parent / "data")

DATA_DIR = _resolve_data_dir()

def get_lab_service(data_dir: Optional[str] = None) -> LabReportService:
    """Dependency provider for LabReportService singleton."""
    return LabReportService(data_dir=data_dir or DATA_DIR)



@router.get("", summary="List all saved laboratory reports")
def list_reports(patient_id: Optional[str] = Query(None, description="Optional patient ID filter")):
    service = get_lab_service()
    reports = service.get_all_reports(patient_id=patient_id)
    return {"success": True, "count": len(reports), "reports": reports}


@router.get("/definitions", summary="Get standard laboratory test definitions and canonical ranges")
def get_definitions():
    service = get_lab_service()
    definitions = service.rules.get_all_definitions()
    return {"success": True, "count": len(definitions), "definitions": definitions}


@router.get("/trends", summary="Calculate chronological deterministic trends across reports")
def get_trends(patient_id: Optional[str] = Query(None, description="Optional patient ID filter")):
    service = get_lab_service()
    trends_data = service.calculate_trends(patient_id=patient_id)
    return {"success": True, "data": trends_data}


@router.get("/{report_id}", summary="Get full details for a single laboratory report")
def get_report(report_id: str):
    service = get_lab_service()
    report = service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Laboratory report '{report_id}' not found.")
    return {"success": True, "report": report.to_dict()}


@router.post("", summary="Create or save a laboratory report")
def create_report(payload: Dict[str, Any]):
    service = get_lab_service()
    try:
        report = LabReport.from_dict(payload)
        saved = service.create_report(report)
        return {"success": True, "message": "Laboratory report saved successfully.", "report": saved.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{report_id}", summary="Update an existing laboratory report")
def update_report(report_id: str, payload: Dict[str, Any]):
    service = get_lab_service()
    try:
        payload["report_id"] = report_id
        report = LabReport.from_dict(payload)
        updated = service.update_report(report_id, report)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Laboratory report '{report_id}' not found.")
        return {"success": True, "message": "Report updated successfully.", "report": updated.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{report_id}", summary="Delete a laboratory report")
def delete_report(report_id: str):
    service = get_lab_service()
    deleted = service.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Laboratory report '{report_id}' not found.")
    return {"success": True, "message": f"Laboratory report '{report_id}' deleted successfully."}


@router.post("/upload", summary="Upload a JSON or CSV laboratory report file")
async def upload_report_file(
    file: UploadFile = File(...),
    patient_id: str = Form("P_CURRENT")
):
    service = get_lab_service()
    try:
        content_bytes = await file.read()
        report = service.import_report_file(
            filename=file.filename or "uploaded_report.json",
            file_bytes=content_bytes,
            patient_id=patient_id
        )
        return {
            "success": True,
            "message": f"Successfully parsed and saved {len(report.tests)} tests from '{file.filename}'.",
            "report": report.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File upload error: {str(e)}")


@router.get("/{report_id}/export", summary="Export laboratory report as JSON or CSV")
def export_report(
    report_id: str,
    format: str = Query("json", pattern="^(json|csv)$", description="Format: 'json' or 'csv'")
):
    service = get_lab_service()
    try:
        content, media_type, filename = service.export_report_content(report_id, export_format=format)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
