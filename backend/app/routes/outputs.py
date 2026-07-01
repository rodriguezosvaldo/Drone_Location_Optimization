from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import OUTPUT_DIR

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


def _resolve_output_path(relative_path: str) -> Path:
    safe_path = Path(relative_path)
    if safe_path.is_absolute() or ".." in safe_path.parts:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    full_path = (OUTPUT_DIR / safe_path).resolve()
    if OUTPUT_DIR.resolve() not in full_path.parents and full_path != OUTPUT_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return full_path


@router.get("")
def list_outputs():
    files = []
    if not OUTPUT_DIR.exists():
        return {"files": files}

    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(OUTPUT_DIR)).replace("\\", "/")
            files.append(
                {
                    "path": rel,
                    "name": path.name,
                    "category": rel.split("/")[0] if "/" in rel else "root",
                }
            )
    files.sort(key=lambda item: item["path"])
    return {"files": files}


@router.get("/file/{file_path:path}")
def get_output_file(file_path: str):
    full_path = _resolve_output_path(file_path)
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(full_path)


@router.delete("/file/{file_path:path}")
def delete_output_file(file_path: str):
    full_path = _resolve_output_path(file_path)
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    full_path.unlink()
    return {"message": f"Deleted {full_path.name}."}


@router.delete("")
def delete_all_outputs():
    if not OUTPUT_DIR.exists():
        return {"message": "No files to delete.", "deleted": 0}

    deleted = 0
    for path in OUTPUT_DIR.rglob("*.html"):
        if path.is_file():
            path.unlink()
            deleted += 1

    return {"message": f"Deleted {deleted} file(s).", "deleted": deleted}
