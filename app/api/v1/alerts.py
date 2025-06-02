from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole # For role checking
from app.schemas.report import Alert as AlertSchema # Using the schema from report.py
from app.services.alert import alert_service

router = APIRouter()

@router.get("/", response_model=List[AlertSchema])
def get_active_alerts_endpoint(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can view alerts
) -> Any:
    """
    Returns active alerts (low stock, discrepancy >10%).
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view alerts."
        )
    try:
        alerts = alert_service.get_active_alerts(db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching alerts: {str(e)}")
    return alerts

