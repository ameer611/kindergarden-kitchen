from typing import Any, List
from datetime import date as DateObject # Alias to avoid confusion with datetime.date

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.schemas.report import IngredientUsageReportItem, MonthlySummaryReport
from app.services.report import report_service
from app.tasks.reports import generate_monthly_report

router = APIRouter()

@router.get("/ingredient-usage", response_model=List[IngredientUsageReportItem])
def get_ingredient_usage_report(
    db: Session = Depends(deps.get_db),
    start_date: DateObject = Query(..., alias="from", description="Start date in YYYY-MM-DD format"),
    end_date: DateObject = Query(..., alias="to", description="End date in YYYY-MM-DD format"),
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get ingredient usage report (delivered vs used) for a specified date range.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view this report."
        )
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date."
        )
    try:
        report_data = report_service.get_ingredient_usage(db, start_date=start_date, end_date=end_date)
    except Exception as e:
        # Log the error (you may want to add more details or use a logger)
        print(f"Error generating ingredient usage report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )
    return report_data

@router.get("/monthly-summary", response_model=MonthlySummaryReport)
def get_monthly_summary_report(
    db: Session = Depends(deps.get_db),
    month_str: str = Query(..., alias="month", description="Month in YYYY-MM format"),
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can view
) -> Any:
    """
    Get monthly summary report (portions served, possible, discrepancy rate).
    Requires Manager or Admin role.
    Note: 'Portions possible' is a snapshot based on current estimates.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view this report."
        )
    try:
        year, month = map(int, month_str.split("-"))
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 01 and 12.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid month format. Expected YYYY-MM. Error: {e}"
        )
    
    try:
        summary_data = report_service.get_monthly_summary(db, year=year, month=month)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating summary: {str(e)}")
    return summary_data

@router.post("/monthly-summary/generate", response_model=dict)
def trigger_monthly_report_generation(
    background_tasks: BackgroundTasks,
    month_str: str = Query(..., alias="month", description="Month in YYYY-MM format"),
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can trigger
) -> Any:
    """
    Manually trigger the generation of a monthly summary report.
    This endpoint starts a Celery task to perform the calculation asynchronously.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to trigger report generation."
        )
    
    try:
        year, month = map(int, month_str.split("-"))
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 01 and 12.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid month format. Expected YYYY-MM. Error: {e}"
        )
    
    try:
        # Start the Celery task asynchronously
        task = generate_monthly_report.delay(year=year, month=month)
        
        return {
            "status": "success",
            "message": f"Monthly report generation for {month_str} started",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start report generation task: {str(e)}"
        )

@router.get("/task/{task_id}", response_model=dict)
def get_report_task_status(
    task_id: str,
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Check the status of a report generation task.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to check task status."
        )
    
    try:
        # Get the task result from Celery
        task = generate_monthly_report.AsyncResult(task_id)
        
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
