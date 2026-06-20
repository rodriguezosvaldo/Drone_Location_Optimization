from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import optimization_service
from app.services.jobs import job_manager

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


class SingleOptimizationRequest(BaseModel):
    dock_locations_quantity: int = Field(..., ge=1, description="Maximum number of dock locations (k)")
    max_dock_coverage_capacity: int = Field(..., ge=1, description="Max incidents per dock")
    generate_map: bool = True


class ScenarioRangeRequest(BaseModel):
    k_min: int = Field(..., ge=1)
    k_max: int = Field(..., ge=1)
    max_dock_coverage_capacity: int = Field(..., ge=1)


class FixedScenarioRequest(BaseModel):
    k_max: int = Field(..., ge=1)
    max_dock_coverage_capacity: int = Field(..., ge=1)


class MonthlyComparisonRequest(BaseModel):
    dock_locations_quantity: int = Field(..., ge=1)
    max_dock_coverage_capacity: int = Field(..., ge=1)


def _validate_k_range(k_min: int, k_max: int) -> None:
    if k_min > k_max:
        raise HTTPException(status_code=400, detail="k_min must be less than or equal to k_max.")


@router.post("/single")
def optimize_single(payload: SingleOptimizationRequest):
    try:
        return optimization_service.run_single_optimization(
            payload.dock_locations_quantity,
            payload.max_dock_coverage_capacity,
            payload.generate_map,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/minimize-docks")
def optimize_minimize_docks(payload: SingleOptimizationRequest):
    try:
        return optimization_service.run_minimize_docks(
            payload.dock_locations_quantity,
            payload.max_dock_coverage_capacity,
            payload.generate_map,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/no-fixed")
def optimize_no_fixed(payload: ScenarioRangeRequest):
    _validate_k_range(payload.k_min, payload.k_max)
    job_id = job_manager.create(
        "no_fixed_scenario",
        lambda: optimization_service.run_no_fixed_scenario(
            payload.k_min,
            payload.k_max,
            payload.max_dock_coverage_capacity,
        ),
    )
    return {"job_id": job_id, "message": "Optimization started."}


@router.post("/fixed")
def optimize_fixed(payload: FixedScenarioRequest):
    job_id = job_manager.create(
        "fixed_metrosafe_scenario",
        lambda: optimization_service.run_fixed_scenario(
            payload.k_max,
            payload.max_dock_coverage_capacity,
        ),
    )
    return {"job_id": job_id, "message": "Optimization started."}


@router.post("/compare-both")
def optimize_compare_both(payload: ScenarioRangeRequest):
    _validate_k_range(payload.k_min, payload.k_max)
    job_id = job_manager.create(
        "compare_both_scenarios",
        lambda: optimization_service.run_compare_both_scenarios(
            payload.k_min,
            payload.k_max,
            payload.max_dock_coverage_capacity,
        ),
    )
    return {"job_id": job_id, "message": "Optimization started."}


@router.post("/by-month")
def optimize_by_month(payload: MonthlyComparisonRequest):
    job_id = job_manager.create(
        "monthly_peak_day_comparison",
        lambda: optimization_service.run_monthly_comparison(
            payload.dock_locations_quantity,
            payload.max_dock_coverage_capacity,
        ),
    )
    return {"job_id": job_id, "message": "Optimization started."}


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
