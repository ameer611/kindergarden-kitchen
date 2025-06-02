from pydantic import BaseModel, UUID4
from typing import List

class MealEstimate(BaseModel):
    meal_id: UUID4
    meal_name: str
    max_portions_possible: int

class EstimateResponse(BaseModel):
    estimates: List[MealEstimate]

