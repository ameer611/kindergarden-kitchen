import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class ServingLog(Base):
    __tablename__ = "serving_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    served_at = Column(DateTime, default=datetime.now())
    portions = Column(Integer, nullable=False)

    # Relationships
    meal = relationship("Meal", back_populates="serving_logs")
    user = relationship("User", back_populates="servings_logged")

