from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class IngredientBase(BaseModel):
    name: str
    quantity_grams: int
    delivery_date: datetime
    low_threshold_grams: int

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    quantity_grams: Optional[int] = None
    delivery_date: Optional[datetime] = None
    low_threshold_grams: Optional[int] = None

class IngredientInDBBase(IngredientBase):
    id: UUID4

    class Config:
        orm_mode = True

class Ingredient(IngredientInDBBase):
    pass

