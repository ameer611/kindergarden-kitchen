from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

# --- ServingLog Schemas ---
class ServingLogBase(BaseModel):
    meal_id: UUID4
    user_id: UUID4 # The user who logged the serving (cook)
    portions: int

class ServingLogCreate(ServingLogBase):
    pass # All fields required from base

class ServingLogUpdate(BaseModel):
    # Typically serving logs are immutable, but if updates were allowed:
    portions: Optional[int] = None 

class ServingLogInDBBase(ServingLogBase):
    id: UUID4
    served_at: datetime

    class Config:
        orm_mode = True

class ServingLog(ServingLogInDBBase):
    pass

# --- Request Schema for POST /api/meals/{id}/serve ---
class ServeMealRequest(BaseModel):
    user_id: UUID4 # This is redundant if we take user_id from the authenticated user (cook)
                     # However, the spec explicitly asks for it in the request body.
                     # For now, I will keep it as per spec. It could be the ID of the cook performing the action.
    portions: int

