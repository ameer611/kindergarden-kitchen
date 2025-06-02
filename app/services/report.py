from datetime import datetime, date
from typing import List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.ingredient import Ingredient
from app.models.serving_log import ServingLog
from app.models.recipe_item import RecipeItem
from app.models.meal import Meal
from app.schemas.report import IngredientUsageReportItem, MonthlySummaryReport
from app.schemas.estimate import MealEstimate  # For portions_possible in monthly summary
from app.services.estimate import estimate_service  # For portions_possible in monthly summary

class ReportService:
    def get_ingredient_usage(
        self, db: Session, *, start_date: date, end_date: date
    ) -> List[IngredientUsageReportItem]:
        """
        Calculates ingredient usage (delivered vs used) within a specified date range.
        'Delivered' is simplified: This service cannot accurately calculate 'delivered' amounts in a period
        without a dedicated delivery log. It will return 0 for delivered_grams.
        'Used' is calculated from ServingLog and RecipeItem within the date range.
        """
        report_items: List[IngredientUsageReportItem] = []
        ingredients = db.query(Ingredient).all()

        # Calculate total used for each ingredient in the period
        ingredient_usage_map: Dict[str, int] = {}
        servings_in_period = (
            db.query(ServingLog)
            .filter(ServingLog.served_at >= datetime.combine(start_date, datetime.min.time()))
            .filter(ServingLog.served_at <= datetime.combine(end_date, datetime.max.time()))
            .all()
        )

        for serving in servings_in_period:
            meal = (
                db.query(Meal)
                .options(joinedload(Meal.recipe_items))
                .filter(Meal.id == serving.meal_id)
                .first()
            )
            if meal and meal.recipe_items:
                for recipe_item in meal.recipe_items:
                    ingredient_id_str = str(recipe_item.ingredient_id)
                    amount_used = recipe_item.amount_grams * serving.portions
                    ingredient_usage_map[ingredient_id_str] = (
                        ingredient_usage_map.get(ingredient_id_str, 0) + amount_used
                    )

        for ing in ingredients:
            used_grams = ingredient_usage_map.get(str(ing.id), 0)
            report_items.append(
                IngredientUsageReportItem(
                    ingredient_name=ing.name,
                    delivered_grams=0,  # Limitation: Model doesn't support tracking deliveries over time.
                    used_grams=used_grams,
                )
            )
        return report_items

    def get_monthly_summary(
        self, db: Session, *, year: int, month: int
    ) -> MonthlySummaryReport:
        """
        Calculates monthly summary: portions served, portions possible, discrepancy rate.
        'Portions possible' is a snapshot based on current inventory estimates, not a true monthly aggregate.
        """
        # Portions Served
        start_datetime = datetime(year, month, 1)
        if month == 12:
            end_datetime = datetime(year + 1, 1, 1)
        else:
            end_datetime = datetime(year, month + 1, 1)

        total_portions_served = (
            db.query(func.sum(ServingLog.portions))
            .filter(ServingLog.served_at >= start_datetime)
            .filter(ServingLog.served_at < end_datetime)
            .scalar()
        ) or 0

        # Portions Possible - Sum of current max_portions_possible for all meals
        current_meal_estimates = estimate_service.calculate_max_portions_for_all_meals(db)
        total_portions_possible = sum(est.max_portions_possible for est in current_meal_estimates)

        discrepancy_rate = 0.0
        if total_portions_possible > 0:
            discrepancy_rate = round(
                (total_portions_possible - total_portions_served) / total_portions_possible * 100,
                1  # One decimal place
            )
        else:
            discrepancy_rate = 0.0 if total_portions_served == 0 else 100.0

        return MonthlySummaryReport(
            portions_served=total_portions_served,
            portions_possible=total_portions_possible,
            discrepancy_rate=discrepancy_rate,
        )

report_service = ReportService()