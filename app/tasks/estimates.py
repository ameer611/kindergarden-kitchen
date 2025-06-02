from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.estimate import estimate_service

@shared_task(name="tasks.recalculate_estimates")
def recalculate_estimates():
    """
    Recalculate maximum portions possible for all meals based on current inventory.
    This task can be triggered manually via API or scheduled.
    
    Returns:
        dict: Summary of the recalculation results
    """
    db = SessionLocal()
    try:
        # Use the existing estimate service to calculate max portions
        estimates = estimate_service.calculate_max_portions_for_all_meals(db)
        
        # Convert to serializable format for Celery result
        result = {
            "status": "success",
            "estimates": [
                {
                    "meal_id": str(est.meal_id),
                    "meal_name": est.meal_name,
                    "max_portions_possible": est.max_portions_possible
                }
                for est in estimates
            ],
            "total_meals": len(estimates)
        }
        
        # Here you could also store the results in a cache (Redis, etc.)
        # for faster retrieval by the API endpoint
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()
