from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import (
    UPLOADED_DOCKS_PATH,
    UPLOADED_INCIDENTS_PATH,
    UPLOADED_PRIORITY_DOCKS_PATH,
    UPLOADS_DIR,
)
from app.services import optimization_service

router = APIRouter(prefix="/api/data", tags=["data"])


class AnalyzeAreaRequest(BaseModel):
    area: str = Field(..., pattern="^(full|specific)$")


def _missing_upload_labels() -> list[str]:
    missing: list[str] = []
    if not UPLOADED_INCIDENTS_PATH.exists():
        missing.append("incidents")
    if not UPLOADED_DOCKS_PATH.exists():
        missing.append("docks")
    if not UPLOADED_PRIORITY_DOCKS_PATH.exists():
        missing.append("priority docks")
    return missing


def _require_all_uploaded_files() -> None:
    missing = _missing_upload_labels()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Upload all three files before continuing. Missing: {', '.join(missing)}.",
        )


async def _save_upload(file: UploadFile, destination: Path) -> int:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file (.xlsx or .xls).")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    destination.write_bytes(content)
    return len(content)


@router.get("/status")
def get_status():
    return optimization_service.get_status()


@router.post("/upload/docks")
async def upload_docks(file: UploadFile = File(...)):
    size_bytes = await _save_upload(file, UPLOADED_DOCKS_PATH)

    return {
        "message": "Docks file uploaded successfully.",
        "filename": UPLOADED_DOCKS_PATH.name,
        "size_bytes": size_bytes,
    }


@router.post("/upload/incidents")
async def upload_incidents(file: UploadFile = File(...)):
    size_bytes = await _save_upload(file, UPLOADED_INCIDENTS_PATH)

    return {
        "message": "Incidents file uploaded successfully.",
        "filename": UPLOADED_INCIDENTS_PATH.name,
        "size_bytes": size_bytes,
    }


@router.post("/upload/priority-docks")
async def upload_priority_docks(file: UploadFile = File(...)):
    size_bytes = await _save_upload(file, UPLOADED_PRIORITY_DOCKS_PATH)
    result = optimization_service.load_priority_docks(UPLOADED_PRIORITY_DOCKS_PATH)

    return {
        "message": "Priority docks file uploaded successfully.",
        "filename": UPLOADED_PRIORITY_DOCKS_PATH.name,
        "size_bytes": size_bytes,
        **result,
    }


@router.post("/upload")
async def upload_all(
    incidents: UploadFile = File(...),
    docks: UploadFile = File(...),
    priority_docks: UploadFile = File(...),
):
    try:
        await _save_upload(incidents, UPLOADED_INCIDENTS_PATH)
        await _save_upload(docks, UPLOADED_DOCKS_PATH)
        await _save_upload(priority_docks, UPLOADED_PRIORITY_DOCKS_PATH)

        result = optimization_service.load_data(
            UPLOADED_DOCKS_PATH,
            UPLOADED_INCIDENTS_PATH,
            UPLOADED_PRIORITY_DOCKS_PATH,
        )
        return {
            "message": "Uploaded and loaded incidents, docks, and priority docks.",
            **result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/load")
def reload_uploaded_data():
    try:
        _require_all_uploaded_files()
        result = optimization_service.load_data(
            UPLOADED_DOCKS_PATH,
            UPLOADED_INCIDENTS_PATH,
            UPLOADED_PRIORITY_DOCKS_PATH,
        )
        return {"message": "Uploaded data reloaded successfully.", **result}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze")
def analyze_area(payload: AnalyzeAreaRequest):
    try:
        result = optimization_service.analyze_area(payload.area)
        label = "entire area" if payload.area == "full" else "priority area"
        return {"message": f"Map generated for the {label}.", **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
