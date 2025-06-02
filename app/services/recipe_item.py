from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.recipe_item import RecipeItem
from app.models.meal import Meal
from app.models.ingredient import Ingredient
from app.schemas.meal import RecipeItemCreate, RecipeItemUpdate


class RecipeItemService:
    def get(self, db: Session, id: Any) -> Optional[RecipeItem]:
        """Get a single recipe item by ID."""
        return db.query(RecipeItem).filter(RecipeItem.id == id).first()

    def get_multi(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100,
            meal_id: Optional[str] = None,
            ingredient_id: Optional[str] = None
    ) -> List[RecipeItem]:
        """Get multiple recipe items with optional filtering."""
        query = db.query(RecipeItem)

        if meal_id:
            query = query.filter(RecipeItem.meal_id == meal_id)

        if ingredient_id:
            query = query.filter(RecipeItem.ingredient_id == ingredient_id)

        return query.offset(skip).limit(limit).all()

    def get_by_meal_id(self, db: Session, *, meal_id: str) -> List[RecipeItem]:
        """Get all recipe items for a specific meal."""
        return db.query(RecipeItem).filter(RecipeItem.meal_id == meal_id).all()

    def get_by_ingredient_id(self, db: Session, *, ingredient_id: str) -> List[RecipeItem]:
        """Get all recipe items that use a specific ingredient."""
        return db.query(RecipeItem).filter(RecipeItem.ingredient_id == ingredient_id).all()

    def get_by_meal_and_ingredient(
            self, db: Session, *, meal_id: str, ingredient_id: str
    ) -> Optional[RecipeItem]:
        """Get a recipe item by meal and ingredient IDs."""
        return db.query(RecipeItem).filter(
            and_(
                RecipeItem.meal_id == meal_id,
                RecipeItem.ingredient_id == ingredient_id
            )
        ).first()

    def create(self, db: Session, *, obj_in: RecipeItemCreate, meal_id: str) -> RecipeItem:
        """Create a new recipe item."""
        # Verify meal exists
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            raise ValueError(f"Meal with id {meal_id} not found.")

        # Verify ingredient exists
        ingredient = db.query(Ingredient).filter(Ingredient.id == obj_in.ingredient_id).first()
        if not ingredient:
            raise ValueError(f"Ingredient with id {obj_in.ingredient_id} not found.")

        # Check if recipe item already exists for this meal and ingredient
        existing_item = self.get_by_meal_and_ingredient(
            db, meal_id=meal_id, ingredient_id=str(obj_in.ingredient_id)
        )
        if existing_item:
            raise ValueError(
                f"Recipe item with ingredient {obj_in.ingredient_id} already exists for meal {meal_id}."
            )

        db_obj = RecipeItem(
            meal_id=meal_id,
            ingredient_id=obj_in.ingredient_id,
            amount_grams=obj_in.amount_grams
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_for_meal(self, db: Session, *, obj_in: RecipeItemCreate, meal_id: str) -> RecipeItem:
        """Create a new recipe item for a specific meal (alias for create method)."""
        return self.create(db, obj_in=obj_in, meal_id=meal_id)

    def create_multiple_for_meal(
            self, db: Session, *, recipe_items_in: List[RecipeItemCreate], meal_id: str
    ) -> List[RecipeItem]:
        """Create multiple recipe items for a meal in a single transaction."""
        # Verify meal exists
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            raise ValueError(f"Meal with id {meal_id} not found.")

        # Verify all ingredients exist
        ingredient_ids = [str(item.ingredient_id) for item in recipe_items_in]
        existing_ingredients = db.query(Ingredient).filter(
            Ingredient.id.in_(ingredient_ids)
        ).all()
        existing_ingredient_ids = [str(ing.id) for ing in existing_ingredients]

        missing_ingredients = set(ingredient_ids) - set(existing_ingredient_ids)
        if missing_ingredients:
            raise ValueError(f"Ingredients not found: {', '.join(missing_ingredients)}")

        # Check for existing recipe items
        existing_items = db.query(RecipeItem).filter(
            and_(
                RecipeItem.meal_id == meal_id,
                RecipeItem.ingredient_id.in_(ingredient_ids)
            )
        ).all()

        if existing_items:
            existing_ingredient_ids = [str(item.ingredient_id) for item in existing_items]
            raise ValueError(
                f"Recipe items already exist for ingredients: {', '.join(existing_ingredient_ids)}"
            )

        # Create all recipe items
        created_items = []
        try:
            for item_in in recipe_items_in:
                db_obj = RecipeItem(
                    meal_id=meal_id,
                    ingredient_id=item_in.ingredient_id,
                    amount_grams=item_in.amount_grams
                )
                db.add(db_obj)
                created_items.append(db_obj)

            db.commit()

            # Refresh all objects
            for item in created_items:
                db.refresh(item)

            return created_items

        except Exception as e:
            db.rollback()
            raise ValueError(f"Error creating recipe items: {str(e)}")

    def update(
            self, db: Session, *, db_obj: RecipeItem, obj_in: Union[RecipeItemUpdate, Dict[str, Any]]
    ) -> RecipeItem:
        """Update a recipe item."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        # If ingredient_id is being updated, verify it exists and doesn't conflict
        if "ingredient_id" in update_data and update_data["ingredient_id"] is not None:
            new_ingredient_id = update_data["ingredient_id"]

            # Verify ingredient exists
            ingredient = db.query(Ingredient).filter(Ingredient.id == new_ingredient_id).first()
            if not ingredient:
                raise ValueError(f"Ingredient with id {new_ingredient_id} not found.")

            # Check if another recipe item already uses this ingredient for the same meal
            existing_item = db.query(RecipeItem).filter(
                and_(
                    RecipeItem.meal_id == db_obj.meal_id,
                    RecipeItem.ingredient_id == new_ingredient_id,
                    RecipeItem.id != db_obj.id
                )
            ).first()

            if existing_item:
                raise ValueError(
                    f"Another recipe item with ingredient {new_ingredient_id} already exists for this meal."
                )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: str) -> RecipeItem:
        """Remove a recipe item by ID."""
        obj = db.query(RecipeItem).filter(RecipeItem.id == id).first()
        if not obj:
            raise ValueError(f"Recipe item with id {id} not found.")

        db.delete(obj)
        db.commit()
        return obj

    def remove_all_for_meal(self, db: Session, *, meal_id: str) -> int:
        """Remove all recipe items for a specific meal."""
        # Verify meal exists
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            raise ValueError(f"Meal with id {meal_id} not found.")

        # Count items before deletion
        count = db.query(RecipeItem).filter(RecipeItem.meal_id == meal_id).count()

        # Delete all recipe items for the meal
        db.query(RecipeItem).filter(RecipeItem.meal_id == meal_id).delete()
        db.commit()

        return count

    def remove_by_ingredient(self, db: Session, *, ingredient_id: str) -> int:
        """Remove all recipe items that use a specific ingredient."""
        # Verify ingredient exists
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise ValueError(f"Ingredient with id {ingredient_id} not found.")

        # Count items before deletion
        count = db.query(RecipeItem).filter(RecipeItem.ingredient_id == ingredient_id).count()

        # Delete all recipe items using this ingredient
        db.query(RecipeItem).filter(RecipeItem.ingredient_id == ingredient_id).delete()
        db.commit()

        return count

    def count_by_meal(self, db: Session, *, meal_id: str) -> int:
        """Count recipe items for a specific meal."""
        return db.query(RecipeItem).filter(RecipeItem.meal_id == meal_id).count()

    def count_by_ingredient(self, db: Session, *, ingredient_id: str) -> int:
        """Count recipe items that use a specific ingredient."""
        return db.query(RecipeItem).filter(RecipeItem.ingredient_id == ingredient_id).count()

    def get_total_grams_for_meal(self, db: Session, *, meal_id: str) -> int:
        """Get total grams of all ingredients for a specific meal."""
        from sqlalchemy import func

        result = db.query(func.sum(RecipeItem.amount_grams)).filter(
            RecipeItem.meal_id == meal_id
        ).scalar()

        return result or 0


# Create singleton instance
recipe_item_service = RecipeItemService()