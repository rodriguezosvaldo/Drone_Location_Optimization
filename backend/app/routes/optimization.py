from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import optimization_service
from app.services.jobs import job_manager

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


class OptimizeRequest(BaseModel):
    area: str = Field(..., pattern="^(full|specific)$")
    peak_day_only: bool = Field(
        True,
        description="Use only incidents from the busiest day in the selected area",
    )
    budget: int = Field(..., ge=1, description="Maximum number of dock locations to open")
    open_priority_docks_first: bool = Field(
        False,
        description="Prioritize opening docks from the priority docks file",
    )
    percentage_to_cover: float = Field(
        100,
        ge=1,
        le=100,
        description="Maximum percentage of incidents that may be covered",
    )
    iterative: bool = Field(
        False,
        description="Run repeated optimizations increasing budget and/or response time",
    )
    increase_budget: bool = Field(
        False,
        description="Increase budget by 1 on each iterative step",
    )
    increase_response_time: bool = Field(
        False,
        description="Increase drone response time on each iterative step",
    )


@router.post("/run")
def optimize_run(payload: OptimizeRequest):
    try:
        if payload.iterative:
            job_id = job_manager.create(
                "maximize_incidents_covered",
                lambda: optimization_service.run_optimization(
                    area=payload.area,
                    peak_day_only=payload.peak_day_only,
                    budget=payload.budget,
                    open_priority_docks_first=payload.open_priority_docks_first,
                    percentage_to_cover=payload.percentage_to_cover,
                    iterative=True,
                    increase_budget=payload.increase_budget,
                    increase_response_time=payload.increase_response_time,
                ),
            )
            return {"job_id": job_id, "message": "Optimization started."}

        return optimization_service.run_optimization(
            area=payload.area,
            peak_day_only=payload.peak_day_only,
            budget=payload.budget,
            open_priority_docks_first=payload.open_priority_docks_first,
            percentage_to_cover=payload.percentage_to_cover,
            iterative=False,
            increase_budget=False,
            increase_response_time=False,
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
