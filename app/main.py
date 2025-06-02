from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, ingredients, meals, serving, estimates, reports, alerts, logs, recipe_items
from app.ws import inventory as ws_inventory
from app.core.config import settings
from app.tasks.worker import celery_app
from app.core.database import engine, Base

app = FastAPI(
    title="Kindergarten Kitchen Management API",
    description="Backend API for Kindergarten Kitchen Management System",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Create the database tables
Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(ingredients.router, prefix=f"{settings.API_V1_STR}/ingredients", tags=["ingredients"])
app.include_router(meals.router, prefix=f"{settings.API_V1_STR}/meals", tags=["meals"])
app.include_router(serving.router, prefix=f"{settings.API_V1_STR}/meals", tags=["serving"]) # Note: serving is under /meals/{meal_id}/serve
app.include_router(estimates.router, prefix=f"{settings.API_V1_STR}/estimates", tags=["estimates"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])
app.include_router(logs.router, prefix=f"{settings.API_V1_STR}/logs", tags=["logs"])
app.include_router(recipe_items.router, prefix=f"{settings.API_V1_STR}/recipe-items", tags=["recipe-items"])


# WebSocket Router
app.include_router(ws_inventory.router) # WebSocket router for /ws/inventory

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Kindergarten Kitchen Management API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# Make Celery app available for import elsewhere if needed
celery_app_instance = celery_app

