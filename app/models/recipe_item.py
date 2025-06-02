import uuid
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.id"), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False)
    amount_grams = Column(Integer, nullable=False)

    # Relationships
    meal = relationship("Meal", back_populates="recipe_items")
    ingredient = relationship("Ingredient") # No back_populates needed if Ingredient doesn't need to know about RecipeItems directly

