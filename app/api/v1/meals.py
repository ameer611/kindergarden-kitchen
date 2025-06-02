from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.validate_uuid import validate_uuid
from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.models.meal import Meal as MealModel
from app.schemas.meal import (
    Meal as MealSchema, 
    MealCreate, 
    MealUpdate, 
    MealWithRecipeSummary,
    MealWithFullRecipe
)
from app.services.meal import meal_service

router = APIRouter()

@router.post("/", response_model=MealSchema, status_code=status.HTTP_201_CREATED)
def create_meal(
    *, 
    db: Session = Depends(deps.get_db),
    meal_in: MealCreate,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can create
) -> Any:
    """
    Create new meal with its recipe.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    existing_meal = meal_service.get_by_name(db, name=meal_in.name)
    if existing_meal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meal with this name already exists."
        )
    try:
        meal = meal_service.create_with_recipe(db, obj_in=meal_in, created_by_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return meal

@router.get("/", response_model=List[MealWithRecipeSummary])
def read_meals(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(deps.get_current_active_user) # All authenticated users can view
) -> Any:
    """
    Retrieve meals with recipe summary (ingredient count, total grams).
    Accessible by all authenticated users.
    """
    meals_data = meal_service.get_multi_with_summary(db, skip=skip, limit=limit)
    results = []
    for meal, item_count, total_grams in meals_data:
        results.append(
            MealWithRecipeSummary(
                id=meal.id,
                name=meal.name,
                created_by_id=meal.created_by_id,
                created_at=meal.created_at,
                recipe_ingredient_count=item_count,
                recipe_total_grams=total_grams
            )
        )
    return results

@router.get("/{meal_id}", response_model=MealWithFullRecipe)
def read_meal_by_id(
    meal_id: str,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific meal by id with full recipe details.
    Accessible by all authenticated users.
    """
    try:
        validate_uuid(meal_id)
        meal = meal_service.get(db, id=meal_id)
        if not meal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
        return meal 
    except Exception as e:
        # Log the exception details for debugging purposes
        logger.error(f"Error retrieving meal {meal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.put("/{meal_id}", response_model=MealSchema)
def update_meal(
    *, 
    db: Session = Depends(deps.get_db),
    meal_id: str,
    meal_in: MealUpdate,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can update
) -> Any:
    """
    Update a meal, including its name or recipe.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    meal = meal_service.get(db, id=meal_id)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found",
        )
    try:
        updated_meal = meal_service.update_with_recipe(db, db_obj=meal, obj_in=meal_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return updated_meal

@router.delete("/{meal_id}", response_model=MealSchema)
def delete_meal(
    *, 
    db: Session = Depends(deps.get_db),
    meal_id: str,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can delete
) -> Any:
    """
    Delete a meal.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    meal = meal_service.get(db, id=meal_id)
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    
    # Add logic here if meal cannot be deleted due to serving logs, etc. (not specified, but good practice)
    
    deleted_meal = meal_service.remove(db, id=meal_id)
    return deleted_meal

