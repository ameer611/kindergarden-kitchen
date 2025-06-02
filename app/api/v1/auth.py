from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User as UserModel
from app.schemas.user import User as UserSchema, Token, UserCreate
from app.services.user import user_service

router = APIRouter()

# @router.post("/register", response_model=UserSchema)
# def register_user(
#     user_in: UserCreate,
#     db: Session = Depends(deps.get_db)
# ) -> Any:
#     """
#     Register a new user without requiring authentication.
#     """
#     # Check if username or email already exists
#     if user_service.get_by_username(db, username=user_in.username):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="The username is already taken."
#         )
#     if user_service.get_by_email(db, email=user_in.email):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="The email is already registered."
#         )

#     # Create the user
#     user = user_service.create(db, obj_in=user_in)
#     return user


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = user_service.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "username": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserSchema)
def read_users_me(
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
