from pydantic import BaseModel
from typing import List, Optional

# --- Report Schemas ---

# For GET /api/reports/ingredient-usage?from=&to=
class IngredientUsageReportItem(BaseModel):
    ingredient_name: str # Changed from "ingredient" to be more specific
    delivered_grams: int # Changed from "delivered" for clarity on units
    used_grams: int      # Changed from "used" for clarity on units

# For GET /api/reports/monthly-summary?month=YYYY-MM
class MonthlySummaryReport(BaseModel):
    portions_served: int
    portions_possible: int # This would likely come from summing MealEstimate.max_portions_possible for the month or similar logic
    discrepancy_rate: float # (portions_possible - portions_served) / portions_possible if portions_possible > 0

# --- Alert Schemas ---

class AlertBase(BaseModel):
    type: str # e.g., "low_stock", "discrepancy"
    message: str
    details: Optional[dict] = None # For additional context, e.g., ingredient_id for low_stock

class Alert(AlertBase):
    id: str # Could be a hash of the alert content or a UUID if stored
    created_at: str # ISO datetime string

# Response for GET /api/alerts
class ActiveAlertsResponse(BaseModel):
    alerts: List[Alert]

