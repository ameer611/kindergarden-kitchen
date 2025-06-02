from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.services.user import user_service

router = APIRouter()

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(
    *, 
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: UserModel = Depends(deps.get_current_active_superuser) # Ensures only admin can create
) -> Any:
    """
    Create new user.
    """
    user = user_service.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = user_service.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = user_service.create(db, obj_in=user_in)
    return user

@router.get("/", response_model=List[UserSchema])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Retrieve users.
    """
    users = db.query(UserModel).offset(skip).limit(limit).all() # Basic pagination, can be improved
    return users

@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: str, # Assuming UUID is passed as string
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Get a specific user by id.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    *, 
    db: Session = Depends(deps.get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: UserModel = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Update a user.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    user = user_service.update(db, db_obj=user, obj_in=user_in)
    return user

@router.delete("/{user_id}", response_model=UserSchema)
def delete_user(
    *, 
    db: Session = Depends(deps.get_db),
    user_id: str,
    current_user: UserModel = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Delete a user.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Add logic here to check if user can be deleted (e.g., not deleting self, or other constraints)
    db.delete(user)
    db.commit()
    return user

