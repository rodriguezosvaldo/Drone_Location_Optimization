from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

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
    percentage_mode: Literal["single", "range"] = Field(
        "single",
        description="Use one percentage target or run a range of scenarios",
    )
    percentage_to_cover: float | None = Field(
        None,
        ge=1,
        le=100,
        description="Maximum percentage of incidents that may be covered (single mode)",
    )
    percentage_range_start: float | None = Field(
        None,
        ge=1,
        le=100,
        description="First percentage target in range mode",
    )
    percentage_range_end: float | None = Field(
        None,
        ge=1,
        le=100,
        description="Last percentage target in range mode",
    )
    percentage_range_step: float | None = Field(
        None,
        ge=1,
        le=100,
        description="Increment between percentage targets in range mode",
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

    @model_validator(mode="after")
    def validate_percentage_options(self):
        if self.percentage_mode == "single":
            if self.percentage_to_cover is None:
                self.percentage_to_cover = 100
            if self.iterative and not self.increase_budget and not self.increase_response_time:
                raise ValueError("Enable at least one iterative option (budget or response time).")
            return self

        if self.iterative:
            raise ValueError("Iterative budget/response-time options are not available in range mode.")

        missing = [
            name
            for name, value in (
                ("percentage_range_start", self.percentage_range_start),
                ("percentage_range_end", self.percentage_range_end),
                ("percentage_range_step", self.percentage_range_step),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"Missing required range fields: {', '.join(missing)}.")

        if self.percentage_range_start > self.percentage_range_end:
            raise ValueError("percentage_range_start must be less than or equal to percentage_range_end.")

        values = optimization_service.build_percentage_range_values(
            self.percentage_range_start,
            self.percentage_range_end,
            self.percentage_range_step,
        )
        if len(values) < 2:
            raise ValueError("Percentage range must produce at least two scenarios.")
        return self


def _run_kwargs(payload: OptimizeRequest) -> dict:
    return {
        "area": payload.area,
        "peak_day_only": payload.peak_day_only,
        "budget": payload.budget,
        "open_priority_docks_first": payload.open_priority_docks_first,
        "percentage_mode": payload.percentage_mode,
        "percentage_to_cover": payload.percentage_to_cover or 100,
        "percentage_range_start": payload.percentage_range_start,
        "percentage_range_end": payload.percentage_range_end,
        "percentage_range_step": payload.percentage_range_step,
        "iterative": payload.iterative,
        "increase_budget": payload.increase_budget,
        "increase_response_time": payload.increase_response_time,
    }


@router.post("/run")
def optimize_run(payload: OptimizeRequest):
    try:
        kwargs = _run_kwargs(payload)
        if payload.iterative or payload.percentage_mode == "range":
            job_id = job_manager.create(
                "maximize_incidents_covered",
                lambda: optimization_service.run_optimization(**kwargs),
            )
            message = (
                "Percentage range optimization started."
                if payload.percentage_mode == "range"
                else "Optimization started."
            )
            return {"job_id": job_id, "message": message}

        return optimization_service.run_optimization(**kwargs)
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
