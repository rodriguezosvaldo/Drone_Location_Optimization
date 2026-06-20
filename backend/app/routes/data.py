from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import (
    DEFAULT_DOCKS_PATH,
    DEFAULT_INCIDENTS_PATH,
    UPLOADED_DOCKS_PATH,
    UPLOADED_INCIDENTS_PATH,
    UPLOADS_DIR,
)
from app.services import optimization_service

router = APIRouter(prefix="/api/data", tags=["data"])


class LoadDataRequest(BaseModel):
    use_defaults: bool = True
    docks_filename: str | None = None
    incidents_filename: str | None = None


@router.get("/status")
def get_status():
    return optimization_service.get_status()


@router.post("/upload/docks")
async def upload_docks(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file (.xlsx or .xls).")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    UPLOADED_DOCKS_PATH.write_bytes(content)

    return {
        "message": "Docks file uploaded successfully.",
        "filename": UPLOADED_DOCKS_PATH.name,
        "size_bytes": len(content),
    }


@router.post("/upload/incidents")
async def upload_incidents(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file (.xlsx or .xls).")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    UPLOADED_INCIDENTS_PATH.write_bytes(content)

    return {
        "message": "Incidents file uploaded successfully.",
        "filename": UPLOADED_INCIDENTS_PATH.name,
        "size_bytes": len(content),
    }


@router.post("/load")
def load_data(payload: LoadDataRequest):
    try:
        if payload.use_defaults:
            docks_path = DEFAULT_DOCKS_PATH
            incidents_path = DEFAULT_INCIDENTS_PATH
        else:
            docks_path = UPLOADED_DOCKS_PATH
            incidents_path = UPLOADED_INCIDENTS_PATH

        result = optimization_service.load_data(docks_path, incidents_path)
        return {"message": "Data loaded successfully.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
