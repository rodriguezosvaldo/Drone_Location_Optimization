from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import optimization_service
from app.services.jobs import job_manager

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


class MaximizeRequest(BaseModel):
    dock_locations_quantity: int = Field(..., ge=1, description="Maximum number of dock locations (budget)")
    use_specific_docks: bool = Field(
        False,
        description="Prioritize docks from the uploaded priority docks file",
    )
    increase_budget: bool = Field(
        False,
        description="Increment k until 100% of incidents are covered",
    )


@router.post("/maximize")
def optimize_maximize(payload: MaximizeRequest):
    try:
        if payload.increase_budget:
            job_id = job_manager.create(
                "maximize_incidents_covered",
                lambda: optimization_service.run_maximize_optimization(
                    payload.dock_locations_quantity,
                    payload.use_specific_docks,
                    payload.increase_budget,
                ),
            )
            return {"job_id": job_id, "message": "Optimization started."}

        return optimization_service.run_maximize_optimization(
            payload.dock_locations_quantity,
            payload.use_specific_docks,
            payload.increase_budget,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/jobs")
def list_jobs():
    return {"jobs": job_manager.list_jobs()}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
        "result": job.result,
        "error": job.error,
    }
