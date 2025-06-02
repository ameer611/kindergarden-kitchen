from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal_column
from sqlalchemy.sql.expression import select, and_

from app.models.meal import Meal
from app.models.recipe_item import RecipeItem
from app.models.ingredient import Ingredient
from app.schemas.estimate import MealEstimate

class EstimateService:
    def calculate_max_portions_for_all_meals(self, db: Session) -> List[MealEstimate]:
        """
        Calculates the maximum portions possible for each meal based on current inventory.
        Formula: min(ingredient.quantity_grams / recipe_item.amount_grams) for each meal.
        """
        results = []
        meals = db.query(Meal).all()

        for meal in meals:
            if not meal.recipe_items:
                results.append(MealEstimate(meal_id=meal.id, meal_name=meal.name, max_portions_possible=0))
                continue

            min_portions_for_meal = float("inf")
            possible_for_all_ingredients = True

            for item in meal.recipe_items:
                ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
                if not ingredient or item.amount_grams == 0: # Should not happen with proper data
                    possible_for_all_ingredients = False
                    break
                
                # If ingredient quantity is 0, but amount_grams is also 0 (e.g. water, salt - not in spec but general case)
                # this would be infinite. For this spec, amount_grams > 0 is implied.
                if ingredient.quantity_grams == 0 and item.amount_grams > 0:
                    portions_for_this_ingredient = 0
                elif item.amount_grams > 0: # Avoid division by zero
                    portions_for_this_ingredient = ingredient.quantity_grams // item.amount_grams
                else: # amount_grams is 0 or negative, treat as infinite if quantity is also 0, else 0
                    portions_for_this_ingredient = float("inf") if ingredient.quantity_grams == 0 else 0

                min_portions_for_meal = min(min_portions_for_meal, portions_for_this_ingredient)
            
            if not possible_for_all_ingredients:
                max_p = 0
            elif min_portions_for_meal == float("inf"): # Happens if all ingredients have 0 amount_grams and 0 quantity
                max_p = 0 # Or some other indicator of an issue / undefined state
            else:
                max_p = int(min_portions_for_meal)

            results.append(MealEstimate(meal_id=meal.id, meal_name=meal.name, max_portions_possible=max_p))
        
        return results

estimate_service = EstimateService()

