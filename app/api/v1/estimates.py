from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.schemas.estimate import MealEstimate
from app.services.estimate import estimate_service
from app.tasks.estimates import recalculate_estimates

router = APIRouter()

@router.get("/", response_model=List[MealEstimate])
def get_meal_estimations(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Returns the maximum portions possible for each meal based on current inventory.
    Accessible by all authenticated users.
    """
    try:
        # Direct calculation for immediate results
        estimations = estimate_service.calculate_max_portions_for_all_meals(db)
        return estimations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred during estimation: {str(e)}"
        )

@router.post("/recalculate", response_model=dict)
def trigger_estimate_recalculation(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Manually trigger the recalculation of meal portion estimates.
    This endpoint starts a Celery task to perform the calculation asynchronously.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to trigger estimate recalculation."
        )
    
    try:
        # Start the Celery task asynchronously
        task = recalculate_estimates.delay()
        
        return {
            "status": "success",
            "message": "Estimate recalculation task started",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recalculation task: {str(e)}"
        )

@router.get("/task/{task_id}", response_model=dict)
def get_estimate_task_status(
    task_id: str,
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Check the status of an estimate recalculation task.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to check task status."
        )
    
    try:
        # Get the task result from Celery
        task = recalculate_estimates.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task.status,
        }
        
        # Include result if task is successful
        if task.status == 'SUCCESS':
            response["result"] = task.result
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check task status: {str(e)}"
        )
