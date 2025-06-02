from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.models.meal import Meal
from app.models.recipe_item import RecipeItem
from app.models.ingredient import Ingredient # Needed for validation
from app.schemas.meal import MealCreate, MealUpdate, RecipeItemCreate
from app.services.ingredient import ingredient_service # To check ingredient existence

class MealService:
    def get(self, db: Session, id: str) -> Optional[Meal]:
        return db.query(Meal).filter(Meal.id == id).first()

    def get_by_name(self, db: Session, *, name: str) -> Optional[Meal]:
        return db.query(Meal).filter(Meal.name == name).first()

    def get_multi_with_summary(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Meal, int, int]]:
        """Fetches meals along with recipe ingredient count and total grams."""
        # Subquery to count recipe items per meal
        recipe_item_count_sq = (
            select(RecipeItem.meal_id, func.count(RecipeItem.id).label("item_count"))
            .group_by(RecipeItem.meal_id)
            .subquery()
        )
        # Subquery to sum amount_grams per meal
        recipe_total_grams_sq = (
            select(RecipeItem.meal_id, func.sum(RecipeItem.amount_grams).label("total_grams"))
            .group_by(RecipeItem.meal_id)
            .subquery()
        )

        query = (
            db.query(
                Meal,
                func.coalesce(recipe_item_count_sq.c.item_count, 0).label("recipe_ingredient_count"),
                func.coalesce(recipe_total_grams_sq.c.total_grams, 0).label("recipe_total_grams")
            )
            .outerjoin(recipe_item_count_sq, Meal.id == recipe_item_count_sq.c.meal_id)
            .outerjoin(recipe_total_grams_sq, Meal.id == recipe_total_grams_sq.c.meal_id)
            .order_by(Meal.name)
            .offset(skip)
            .limit(limit)
        )
        return query.all()

    def create_with_recipe(self, db: Session, *, obj_in: MealCreate, created_by_id: str) -> Meal:
        # Validate all ingredients in the recipe exist
        for item_in in obj_in.recipe:
            ingredient = ingredient_service.get(db, id=str(item_in.ingredient_id))
            if not ingredient:
                raise ValueError(f"Ingredient with id {item_in.ingredient_id} not found.")

        db_meal = Meal(name=obj_in.name, created_by_id=created_by_id)
        db.add(db_meal)
        db.flush() # Flush to get meal_id for recipe items

        for item_in in obj_in.recipe:
            db_recipe_item = RecipeItem(
                meal_id=db_meal.id,
                ingredient_id=item_in.ingredient_id,
                amount_grams=item_in.amount_grams
            )
            db.add(db_recipe_item)
        
        db.commit()
        db.refresh(db_meal)
        return db_meal

    def update_with_recipe(self, db: Session, *, db_obj: Meal, obj_in: MealUpdate) -> Meal:
        if obj_in.name is not None:
            db_obj.name = obj_in.name

        if obj_in.recipe is not None:
            # Clear existing recipe items for this meal
            db.query(RecipeItem).filter(RecipeItem.meal_id == db_obj.id).delete()

            # Validate and add new recipe items
            for item_in in obj_in.recipe:
                ingredient = ingredient_service.get(db, id=str(item_in.ingredient_id))
                if not ingredient:
                    raise ValueError(f"Ingredient with id {item_in.ingredient_id} not found during update.")
                db_recipe_item = RecipeItem(
                    meal_id=db_obj.id,
                    ingredient_id=item_in.ingredient_id,
                    amount_grams=item_in.amount_grams
                )
                db.add(db_recipe_item)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: str) -> Optional[Meal]:
        obj = db.query(Meal).get(id)
        if obj:
            # RecipeItems are cascade deleted due to relationship setting in Meal model
            db.delete(obj)
            db.commit()
        return obj

meal_service = MealService()

