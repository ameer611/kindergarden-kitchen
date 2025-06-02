from typing import Optional, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.serving_log import ServingLog
from app.models.meal import Meal
from app.models.recipe_item import RecipeItem
from app.models.ingredient import Ingredient
from app.schemas.serving_log import ServingLogCreate, ServeMealRequest
from app.services.ingredient import ingredient_service
from app.services.meal import meal_service # To get meal details

class ServingService:
    def create_serving_log(self, db: Session, *, obj_in: ServingLogCreate) -> ServingLog:
        db_obj = ServingLog(
            meal_id=obj_in.meal_id,
            user_id=obj_in.user_id,
            portions=obj_in.portions
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def serve_meal(
        self, db: Session, *, meal_id: str, serve_request: ServeMealRequest, serving_user_id: str
    ) -> ServingLog:
        meal = meal_service.get(db, id=meal_id)
        if not meal:
            raise ValueError(f"Meal with id {meal_id} not found.")

        if not meal.recipe_items:
            raise ValueError(f"Meal with id {meal_id} has no recipe defined.")

        required_ingredients: Dict[str, int] = {}
        for item in meal.recipe_items:
            ingredient_id_str = str(item.ingredient_id)
            required_amount = item.amount_grams * serve_request.portions
            required_ingredients[ingredient_id_str] = required_ingredients.get(ingredient_id_str, 0) + required_amount

        # Validate inventory and collect ingredients to update
        ingredients_to_update: List[Ingredient] = []
        for ingredient_id, needed_grams in required_ingredients.items():
            ingredient = ingredient_service.get(db, id=ingredient_id)
            if not ingredient:
                # This should ideally not happen if recipe ingredients are validated on meal creation/update
                raise ValueError(f"Ingredient with id {ingredient_id} in recipe not found in inventory.")
            if ingredient.quantity_grams < needed_grams:
                raise ValueError(
                    f"Not enough stock for ingredient 	'{ingredient.name}	'. Required: {needed_grams}g, Available: {ingredient.quantity_grams}g"
                )
            ingredients_to_update.append(ingredient)

        # Deduct stock
        for ingredient in ingredients_to_update:
            needed_grams = required_ingredients[str(ingredient.id)]
            ingredient.quantity_grams -= needed_grams
            db.add(ingredient)
        
        # Log serving
        # The spec says request body has user_id, but it's better to use the authenticated user (cook) if possible.
        # For now, using serve_request.user_id as per spec, but also passing serving_user_id (authenticated user)
        # which could be used for auditing or if the request body user_id is for something else.
        log_entry = ServingLogCreate(
            meal_id=meal_id, 
            user_id=serve_request.user_id, # As per spec request body
            portions=serve_request.portions
        )
        
        # If we decide to use the authenticated user as the one logging the serving:
        # log_entry = ServingLogCreate(meal_id=meal_id, user_id=serving_user_id, portions=serve_request.portions)
        
        db_serving_log = self.create_serving_log(db, obj_in=log_entry)
        
        # Note: The spec mentions real-time updates via WebSockets (inventory.update, serve.attempt).
        # This service should trigger those events. That will be handled in the WebSocket implementation part.

        return db_serving_log
    
    def get_all(self, db: Session) -> List[ServingLog]:
        """
        Retrieve all serving logs ordered by creation time (most recent first).
        """
        return db.query(ServingLog).order_by(ServingLog.created_at.desc()).all()

serving_service = ServingService()

