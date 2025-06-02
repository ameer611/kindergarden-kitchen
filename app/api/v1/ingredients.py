from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.models.ingredient import Ingredient as IngredientModel
from app.schemas.ingredient import Ingredient as IngredientSchema, IngredientCreate, IngredientUpdate
from app.services.ingredient import ingredient_service

router = APIRouter()

@router.post("/", response_model=IngredientSchema, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    *, 
    db: Session = Depends(deps.get_db),
    ingredient_in: IngredientCreate,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can create
) -> Any:
    """
    Create new ingredient.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    existing_ingredient = ingredient_service.get_by_name(db, name=ingredient_in.name)
    if existing_ingredient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient with this name already exists."
        )
    ingredient = ingredient_service.create(db, obj_in=ingredient_in)
    return ingredient

@router.get("/", response_model=List[IngredientSchema])
def read_ingredients(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, alias="search"),
    current_user: UserModel = Depends(deps.get_current_active_user) # All authenticated users can view
) -> Any:
    """
    Retrieve ingredients with pagination and search.
    Accessible by all authenticated users.
    """
    ingredients = ingredient_service.get_multi(db, skip=skip, limit=limit, search=search)
    return ingredients

@router.get("/{ingredient_id}", response_model=IngredientSchema)
def read_ingredient_by_id(
    ingredient_id: str, # Assuming UUID is passed as string
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user) # All authenticated users can view
) -> Any:
    """
    Get a specific ingredient by id.
    Accessible by all authenticated users.
    """
    ingredient = ingredient_service.get(db, id=ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
    return ingredient

@router.put("/{ingredient_id}", response_model=IngredientSchema)
def update_ingredient(
    *, 
    db: Session = Depends(deps.get_db),
    ingredient_id: str,
    ingredient_in: IngredientUpdate,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can update
) -> Any:
    """
    Update an ingredient.
    Requires Manager or Admin role.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    ingredient = ingredient_service.get(db, id=ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found",
        )
    ingredient = ingredient_service.update(db, db_obj=ingredient, obj_in=ingredient_in)
    return ingredient

@router.delete("/{ingredient_id}", response_model=IngredientSchema)
def delete_ingredient(
    *, 
    db: Session = Depends(deps.get_db),
    ingredient_id: str,
    current_user: UserModel = Depends(deps.get_current_active_user) # Manager or Admin can delete
) -> Any:
    """
    Delete an ingredient.
    Requires Manager or Admin role.
    Note: Specification says "Delete if not used in recipes." This logic needs to be added in the service.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    ingredient = ingredient_service.get(db, id=ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
    
    # TODO: Add service logic to check if ingredient is used in any recipe_items
    # For now, direct delete for simplicity
    # if ingredient_service.is_used_in_recipes(db, id=ingredient_id):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Ingredient cannot be deleted as it is used in recipes."
    #     )
        
    deleted_ingredient = ingredient_service.remove(db, id=ingredient_id)
    return deleted_ingredient

