from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.report import report_service

@shared_task(name="tasks.generate_monthly_report")
def generate_monthly_report(year=None, month=None):
    """
    Generate monthly summary report for a specific month.
    If year and month are not provided, it will generate for the previous month.
    This task can be triggered manually via API or scheduled.
    
    Args:
        year (int, optional): Year for the report. Defaults to previous month's year.
        month (int, optional): Month for the report (1-12). Defaults to previous month.
    
    Returns:
        dict: Monthly summary report data
    """
    db = SessionLocal()
    try:
        # If year and month not provided, use previous month
        if year is None or month is None:
            today = datetime.today()
            if today.month == 1:  # January
                month = 12
                year = today.year - 1
            else:
                month = today.month - 1
                year = today.year
        
        # Use the existing report service to generate the monthly summary
        summary = report_service.get_monthly_summary(db, year=year, month=month)
        
        # Convert to serializable format for Celery result
        result = {
            "status": "success",
            "report_period": f"{year}-{month:02d}",
            "data": {
                "portions_served": summary.portions_served,
                "portions_possible": summary.portions_possible,
                "discrepancy_rate": summary.discrepancy_rate
            }
        }
        
        # Check if discrepancy is above threshold (10%)
        if summary.discrepancy_rate > 10.0:
            result["alert"] = {
                "type": "discrepancy",
                "message": f"Monthly discrepancy for {year}-{month:02d} is {summary.discrepancy_rate}%, which is above the 10% threshold."
            }
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()
