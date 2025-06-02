from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.utils.validate_uuid import validate_uuid
from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.models.recipe_item import RecipeItem as RecipeItemModel
from app.models.meal import Meal as MealModel
from app.models.ingredient import Ingredient as IngredientModel
from app.schemas.meal import (
    RecipeItem as RecipeItemSchema,
    RecipeItemCreate,
    RecipeItemUpdate
)
from app.services.recipe_item import recipe_item_service

router = APIRouter()


@router.post("/", response_model=RecipeItemSchema, status_code=status.HTTP_201_CREATED)
def create_recipe_item(
        *,
        db: Session = Depends(deps.get_db),
        recipe_item_in: RecipeItemCreate,
        meal_id: str = Query(..., description="The meal ID to add the recipe item to"),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create new recipe item for a specific meal.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        validate_uuid(meal_id)
        validate_uuid(str(recipe_item_in.ingredient_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    # Verify meal exists
    meal = db.query(MealModel).filter(MealModel.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    # Verify ingredient exists
    ingredient = db.query(IngredientModel).filter(IngredientModel.id == recipe_item_in.ingredient_id).first()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )

    # Check if recipe item already exists for this meal and ingredient
    existing_item = db.query(RecipeItemModel).filter(
        RecipeItemModel.meal_id == meal_id,
        RecipeItemModel.ingredient_id == recipe_item_in.ingredient_id
    ).first()

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe item with this ingredient already exists for this meal"
        )

    # Validate amount_grams is positive
    if recipe_item_in.amount_grams <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount in grams must be greater than 0"
        )

    try:
        recipe_item = recipe_item_service.create_for_meal(
            db,
            obj_in=recipe_item_in,
            meal_id=meal_id
        )
        return recipe_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[RecipeItemSchema])
def read_recipe_items(
        db: Session = Depends(deps.get_db),
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        meal_id: Optional[str] = Query(None, description="Filter by meal ID"),
        ingredient_id: Optional[str] = Query(None, description="Filter by ingredient ID"),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve recipe items with optional filtering.
    Accessible by all authenticated users.
    """
    try:
        if meal_id:
            validate_uuid(meal_id)
        if ingredient_id:
            validate_uuid(ingredient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    recipe_items = recipe_item_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        meal_id=meal_id,
        ingredient_id=ingredient_id
    )
    return recipe_items


@router.get("/{recipe_item_id}", response_model=RecipeItemSchema)
def read_recipe_item_by_id(
        recipe_item_id: str,
        db: Session = Depends(deps.get_db),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific recipe item by id.
    Accessible by all authenticated users.
    """
    try:
        validate_uuid(recipe_item_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    recipe_item = recipe_item_service.get(db, id=recipe_item_id)
    if not recipe_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe item not found"
        )
    return recipe_item


@router.get("/meal/{meal_id}", response_model=List[RecipeItemSchema])
def read_recipe_items_by_meal(
        meal_id: str,
        db: Session = Depends(deps.get_db),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get all recipe items for a specific meal.
    Accessible by all authenticated users.
    """
    try:
        validate_uuid(meal_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    # Verify meal exists
    meal = db.query(MealModel).filter(MealModel.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    recipe_items = recipe_item_service.get_by_meal_id(db, meal_id=meal_id)
    return recipe_items


@router.put("/{recipe_item_id}", response_model=RecipeItemSchema)
def update_recipe_item(
        *,
        db: Session = Depends(deps.get_db),
        recipe_item_id: str,
        recipe_item_in: RecipeItemUpdate,
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update a recipe item.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        validate_uuid(recipe_item_id)
        if recipe_item_in.ingredient_id:
            validate_uuid(str(recipe_item_in.ingredient_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    recipe_item = recipe_item_service.get(db, id=recipe_item_id)
    if not recipe_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe item not found"
        )

    # Validate ingredient exists if being updated
    if recipe_item_in.ingredient_id:
        ingredient = db.query(IngredientModel).filter(
            IngredientModel.id == recipe_item_in.ingredient_id
        ).first()
        if not ingredient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingredient not found"
            )

        # Check if changing to an ingredient that already exists in this meal
        existing_item = db.query(RecipeItemModel).filter(
            RecipeItemModel.meal_id == recipe_item.meal_id,
            RecipeItemModel.ingredient_id == recipe_item_in.ingredient_id,
            RecipeItemModel.id != recipe_item_id
        ).first()

        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another recipe item with this ingredient already exists for this meal"
            )

    # Validate amount_grams is positive if being updated
    if recipe_item_in.amount_grams is not None and recipe_item_in.amount_grams <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount in grams must be greater than 0"
        )

    try:
        recipe_item = recipe_item_service.update(db, db_obj=recipe_item, obj_in=recipe_item_in)
        return recipe_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{recipe_item_id}", response_model=RecipeItemSchema)
def delete_recipe_item(
        *,
        db: Session = Depends(deps.get_db),
        recipe_item_id: str,
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete a recipe item.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        validate_uuid(recipe_item_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    recipe_item = recipe_item_service.get(db, id=recipe_item_id)
    if not recipe_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe item not found"
        )

    try:
        deleted_item = recipe_item_service.remove(db, id=recipe_item_id)
        return deleted_item
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting recipe item: {str(e)}"
        )


@router.delete("/meal/{meal_id}", response_model=dict)
def delete_all_recipe_items_for_meal(
        meal_id: str,
        db: Session = Depends(deps.get_db),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete all recipe items for a specific meal.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        validate_uuid(meal_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    # Verify meal exists
    meal = db.query(MealModel).filter(MealModel.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    try:
        deleted_count = recipe_item_service.remove_all_for_meal(db, meal_id=meal_id)
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} recipe items for meal {meal_id}",
            "meal_id": meal_id,
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting recipe items: {str(e)}"
        )


@router.post("/bulk", response_model=List[RecipeItemSchema])
def create_multiple_recipe_items(
        *,
        db: Session = Depends(deps.get_db),
        recipe_items_in: List[RecipeItemCreate],
        meal_id: str = Query(..., description="The meal ID to add the recipe items to"),
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create multiple recipe items for a specific meal in bulk.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        validate_uuid(meal_id)
        for item in recipe_items_in:
            validate_uuid(str(item.ingredient_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        )

    # Verify meal exists
    meal = db.query(MealModel).filter(MealModel.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    # Validate all ingredients exist
    ingredient_ids = [str(item.ingredient_id) for item in recipe_items_in]
    existing_ingredients = db.query(IngredientModel.id).filter(
        IngredientModel.id.in_(ingredient_ids)
    ).all()
    existing_ingredient_ids = [str(ing.id) for ing in existing_ingredients]

    missing_ingredients = set(ingredient_ids) - set(existing_ingredient_ids)
    if missing_ingredients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredients not found: {', '.join(missing_ingredients)}"
        )

    # Check for duplicate ingredients in the request
    seen_ingredients = set()
    for item in recipe_items_in:
        ingredient_id_str = str(item.ingredient_id)
        if ingredient_id_str in seen_ingredients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate ingredient in request: {ingredient_id_str}"
            )
        seen_ingredients.add(ingredient_id_str)

    # Validate amount_grams for all items
    for item in recipe_items_in:
        if item.amount_grams <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All amounts in grams must be greater than 0"
            )

    try:
        created_items = recipe_item_service.create_multiple_for_meal(
            db,
            recipe_items_in=recipe_items_in,
            meal_id=meal_id
        )
        return created_items
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating recipe items: {str(e)}"
        )