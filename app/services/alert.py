from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.ingredient import Ingredient
from app.models.serving_log import ServingLog
from app.models.meal import Meal # For discrepancy calculation
from app.schemas.report import Alert # Using the Alert schema from report.py
from app.services.report import report_service # For monthly summary to get discrepancy

class AlertService:
    def get_active_alerts(self, db: Session) -> List[Alert]:
        alerts: List[Alert] = []

        # 1. Low Stock Alerts
        low_stock_ingredients = (
            db.query(Ingredient)
            .filter(Ingredient.quantity_grams <= Ingredient.low_threshold_grams)
            .all()
        )
        for ing in low_stock_ingredients:
            alerts.append(
                Alert(
                    id=f"low_stock_{ing.id}",
                    type="low_stock",
                    message=f"Ingredient 	'{ing.name}	' is low in stock ({ing.quantity_grams}g remaining, threshold is {ing.low_threshold_grams}g).",
                    details={"ingredient_id": str(ing.id), "ingredient_name": ing.name, "current_quantity": ing.quantity_grams, "threshold": ing.low_threshold_grams},
                    created_at=datetime.utcnow().isoformat()
                )
            )

        # 2. Discrepancy Alert (>10%)
        # This requires calculating the monthly summary for the *current* month up to today, or the *last completed* month.
        # The spec says "Monthly Report: On 1st of each month, calculate discrepancy and push alert if >10%."
        # This implies the alert is based on the *previous* month's full summary.
        # Let's assume the alert endpoint shows if the *last calculated* monthly discrepancy (e.g., from a background task) was >10%.
        # For now, let's calculate for the *previous* full month.
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        prev_month_year = last_day_previous_month.year
        prev_month_month = last_day_previous_month.month

        # Check if we are past the 1st of the month to have a previous month's report
        # Or, if it's the first day, the report for the month before that might be relevant.
        # For simplicity, we always check the previous full month's summary.
        try:
            previous_month_summary = report_service.get_monthly_summary(db, year=prev_month_year, month=prev_month_month)
            if previous_month_summary.discrepancy_rate > 10.0:
                alerts.append(
                    Alert(
                        id=f"discrepancy_{prev_month_year}_{prev_month_month}",
                        type="discrepancy",
                        message=f"Monthly discrepancy for {prev_month_year}-{prev_month_month:02d} is {previous_month_summary.discrepancy_rate}%, which is above the 10% threshold.",
                        details={
                            "month": f"{prev_month_year}-{prev_month_month:02d}", 
                            "discrepancy_rate": previous_month_summary.discrepancy_rate,
                            "portions_served": previous_month_summary.portions_served,
                            "portions_possible": previous_month_summary.portions_possible
                        },
                        created_at=datetime.now().isoformat() # Ideally, this would be when the alert was generated
                    )
                )
        except Exception as e:
            # Could log this error, e.g., if previous month data is not available yet
            print(f"Could not calculate discrepancy for alert: {e}")
            pass # Don't let this crash the alert fetching
            
        return alerts

alert_service = AlertService()

