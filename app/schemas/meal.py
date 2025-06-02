from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional
from app.schemas.ingredient import Ingredient  # For recipe item ingredient details if needed

# --- RecipeItem Schemas ---

class RecipeItemBase(BaseModel):
    ingredient_id: UUID4
    amount_grams: int

class RecipeItemCreate(RecipeItemBase):
    pass

class RecipeItemUpdate(BaseModel):
    ingredient_id: Optional[UUID4] = None
    amount_grams: Optional[int] = None

class RecipeItemInDBBase(RecipeItemBase):
    id: UUID4
    meal_id: UUID4
    # To show ingredient details when fetching a recipe
    # ingredient: Optional[Ingredient] = None  # This would require a join or separate query in service

    class Config:
        from_attributes = True

class RecipeItem(RecipeItemInDBBase):
    pass

# --- Meal Schemas ---

class MealBase(BaseModel):
    name: str

class MealCreate(MealBase):
    recipe: List[RecipeItemCreate]

class MealUpdate(BaseModel):
    name: Optional[str] = None
    recipe: Optional[List[RecipeItemCreate]] = None  # Allow updating recipe items

class MealInDBBase(MealBase):
    id: UUID4
    created_by_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class Meal(MealInDBBase):
    recipe_items: List[RecipeItem] = []  # To hold RecipeItem objects when fetched

# For GET /api/meals/ - list meals with recipe summary
class MealWithRecipeSummary(MealInDBBase):
    recipe_ingredient_count: int
    recipe_total_grams: int

# For GET /api/meals/{id} - fetch meal with full recipe details
class MealWithFullRecipe(Meal):
    pass  # Inherits recipe_items from Meal schema