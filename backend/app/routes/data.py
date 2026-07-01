from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import (
    DEFAULT_DOCKS_PATH,
    DEFAULT_INCIDENTS_PATH,
    UPLOADED_DOCKS_PATH,
    UPLOADED_INCIDENTS_PATH,
    UPLOADED_PRIORITY_DOCKS_PATH,
    UPLOADS_DIR,
)
from app.services import optimization_service
from app.services.session import session

router = APIRouter(prefix="/api/data", tags=["data"])


class LoadDataRequest(BaseModel):
    use_defaults: bool = True


class AnalyzeAreaRequest(BaseModel):
    area: str = Field(..., pattern="^(full|specific)$")


def _resolve_docks_path() -> Path:
    if session.docks_path and session.docks_path.exists():
        return session.docks_path
    if UPLOADED_DOCKS_PATH.exists():
        return UPLOADED_DOCKS_PATH
    return DEFAULT_DOCKS_PATH


def _resolve_incidents_path() -> Path:
    if session.incidents_path and session.incidents_path.exists():
        return session.incidents_path
    if UPLOADED_INCIDENTS_PATH.exists():
        return UPLOADED_INCIDENTS_PATH
    return DEFAULT_INCIDENTS_PATH


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
    incidents: UploadFile | None = File(None),
    docks: UploadFile | None = File(None),
    priority_docks: UploadFile | None = File(None),
):
    if not incidents and not docks and not priority_docks:
        raise HTTPException(status_code=400, detail="Select at least one file to upload.")

    messages: list[str] = []
    result: dict = {}

    try:
        if incidents:
            await _save_upload(incidents, UPLOADED_INCIDENTS_PATH)
            messages.append("incidents")

        if docks:
            await _save_upload(docks, UPLOADED_DOCKS_PATH)
            messages.append("docks")

        if priority_docks:
            await _save_upload(priority_docks, UPLOADED_PRIORITY_DOCKS_PATH)
            priority_result = optimization_service.load_priority_docks(UPLOADED_PRIORITY_DOCKS_PATH)
            result.update(priority_result)
            messages.append("priority docks")

        if incidents or docks:
            docks_path = UPLOADED_DOCKS_PATH if docks else _resolve_docks_path()
            incidents_path = UPLOADED_INCIDENTS_PATH if incidents else _resolve_incidents_path()
            load_result = optimization_service.load_data(docks_path, incidents_path)
            result.update(load_result)

        label = ", ".join(messages)
        return {"message": f"Uploaded and loaded: {label}.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/use/docks")
async def use_docks(file: UploadFile = File(...)):
    try:
        await _save_upload(file, UPLOADED_DOCKS_PATH)
        incidents_path = _resolve_incidents_path()
        result = optimization_service.load_data(UPLOADED_DOCKS_PATH, incidents_path)
        return {"message": "Docks loaded successfully.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/use/incidents")
async def use_incidents(file: UploadFile = File(...)):
    try:
        await _save_upload(file, UPLOADED_INCIDENTS_PATH)
        docks_path = _resolve_docks_path()
        result = optimization_service.load_data(docks_path, UPLOADED_INCIDENTS_PATH)
        return {"message": "Incidents loaded successfully.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
