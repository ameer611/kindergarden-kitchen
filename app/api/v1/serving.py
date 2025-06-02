from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.schemas.serving_log import ServeMealRequest, ServingLog as ServingLogSchema
from app.services.serving import serving_service

router = APIRouter()

@router.post("/{meal_id}/serve", response_model=ServingLogSchema)
def serve_meal_endpoint(
    *, 
    db: Session = Depends(deps.get_db),
    meal_id: str, # Assuming UUID is passed as string
    serve_request: ServeMealRequest,
    current_user: UserModel = Depends(deps.get_current_active_user) # Cook, Manager or Admin can serve
) -> Any:
    """
    Serve a meal: calculates ingredient needs, validates inventory, deducts stock, and logs serving.
    Requires Cook, Manager, or Admin role.
    """
    # Authorization: Check if the current user has the required role
    if not (current_user.role == UserRole.COOK or 
            current_user.role == UserRole.MANAGER or 
            current_user.role == UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to serve a meal."
        )
    
    # The spec has user_id in the request body. We should validate if this user_id exists if it's different from current_user.
    # For now, we'll pass current_user.id as the one performing the action to the service layer.
    # The service layer currently uses serve_request.user_id as per spec for logging.
    try:
        serving_log = serving_service.serve_meal(
            db,
            meal_id=meal_id,
            serve_request=serve_request,
            serving_user_id=str(current_user.id) # Pass the authenticated user's ID
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors during the serving process
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

    # WebSocket event for 'serve.attempt' and 'inventory.update' should be triggered here or in the service.
    # This will be handled in the WebSocket implementation part.

    return serving_log



@router.get("/serve", response_model=List[ServingLogSchema])
def read_all_serving_logs(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve all serving logs.
    Accessible to authorized users.
    """
    # Optionally, you could enforce role-based restrictions here if needed.
    return serving_service.get_all(db)
