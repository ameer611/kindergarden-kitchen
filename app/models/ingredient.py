import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    quantity_grams = Column(Integer, nullable=False, default=0)
    delivery_date = Column(DateTime, nullable=False, default=datetime.now())
    low_threshold_grams = Column(Integer, nullable=False, default=0)

