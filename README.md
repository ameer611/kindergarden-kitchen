# Kindergarten Kitchen Management – Backend

## 🔧 Project Overview

This project is the backend for a full-stack application designed to streamline kindergarten kitchen operations. It focuses on inventory control, meal preparation tracking, portion estimation, and reporting. Key features include role-based access control, real-time updates via WebSockets, and background task processing with Celery.

## 🧰 Technology Stack

-   **Backend**: FastAPI, Python 3.11
-   **Database**: PostgreSQL
-   **ORM**: SQLAlchemy 2.0 (with Alembic for migrations)
-   **Background Tasks**: Celery, Redis
-   **Real-Time**: FastAPI WebSockets
-   **Authentication**: JWT (python-jose, passlib)
-   **Containerization**: Docker, Docker Compose

## 🚀 Quick Start with Docker

The easiest way to run the application is using Docker Compose:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ameer611/kindergarden-kitchen.git
   cd kindergarten_kitchen
   ```

2. **Configure environment variables**:
   Create a `.env` file in the project root directory with the following content (modify as needed):
   ```
   DATABASE_URL=postgresql://kindergarten_user:your_strong_password@postgres:5432/kindergarten_kitchen_db
   SECRET_KEY=your_very_strong_and_secret_key_for_jwt_please_change_this
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

5. **Access the API**:
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## ⚙️ Manual Setup (Without Docker)

If you prefer to run the application without Docker:

1. **Prerequisites**:
   - Python 3.11+
   - PostgreSQL
   - Redis

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root directory with the following content (modify as needed):
   ```
   DATABASE_URL=postgresql://kindergarten_user:your_strong_password@localhost:5432/kindergarten_kitchen_db
   SECRET_KEY=your_very_strong_and_secret_key_for_jwt_please_change_this
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

5. **Set up the database**:
   ```bash
   # Create a PostgreSQL user and database
   createuser --pwprompt kindergarten_user
   createdb --owner=kindergarten_user kindergarten_kitchen_db
   
   # Run migrations
   alembic upgrade head
   ```

6. **Start the FastAPI application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Start the Celery worker** (in a separate terminal):
   ```bash
   celery -A app.tasks.worker.celery_app worker --loglevel=info
   ```

## 📝 API Endpoints

All API endpoints are prefixed with `/api/v1`.

### Authentication
- **POST /auth/login**: OAuth2 compatible token login
- **GET /users/me**: Get current user profile

### Users
- **POST /users/**: Create a new user (Admin only)
- **GET /users/**: List all users (Admin only)
- **GET /users/{user_id}**: Get a specific user (Admin only)
- **PUT /users/{user_id}**: Update a user (Admin only)
- **DELETE /users/{user_id}**: Delete a user (Admin only)

### Ingredients
- **GET /ingredients/**: List ingredients (supports pagination and search)
- **POST /ingredients/**: Create a new ingredient (Manager/Admin)
- **GET /ingredients/{ingredient_id}**: Get a specific ingredient
- **PUT /ingredients/{ingredient_id}**: Update an ingredient (Manager/Admin)
- **DELETE /ingredients/{ingredient_id}**: Delete an ingredient if not used in recipes (Manager/Admin)

### Meals & Recipes
- **GET /meals/**: List meals with recipe summary
- **POST /meals/**: Create a meal with recipe (Manager/Admin)
- **GET /meals/{meal_id}**: Get a meal with full recipe details
- **PUT /meals/{meal_id}**: Update a meal (Manager/Admin)
- **DELETE /meals/{meal_id}**: Delete a meal (Manager/Admin)

### Serving Logic
- **POST /meals/{meal_id}/serve**: Serve a meal (Cook/Manager/Admin)

### Estimations
- **GET /estimates/**: Get maximum portions possible for each meal
- **POST /estimates/recalculate**: Trigger asynchronous recalculation of estimates (Manager/Admin)
- **GET /estimates/task/{task_id}**: Check status of an estimate recalculation task (Manager/Admin)

### Reports
- **GET /reports/ingredient-usage**: Get ingredient usage report for a date range (Manager/Admin)
- **GET /reports/monthly-summary**: Get monthly summary report (Manager/Admin)
- **POST /reports/monthly-summary/generate**: Trigger asynchronous generation of a monthly report (Manager/Admin)
- **GET /reports/task/{task_id}**: Check status of a report generation task (Manager/Admin)

### Alerts
- **GET /alerts/**: Get active alerts (low stock, discrepancy >10%)

## 🔌 WebSocket Real-Time Updates

The application uses WebSockets for real-time updates on the `/ws/inventory` namespace.

- **Events Broadcasted**:
  - `inventory.update`: Sent when ingredient stock changes
  - `alerts.low_stock`: Sent when an ingredient's quantity falls below its low threshold
  - `serve.attempt`: Provides feedback during the meal serving process

Clients can connect to `ws://localhost:8000/ws/inventory` to receive these updates.

## 🧪 Background Tasks with Celery

The application uses Celery for asynchronous background tasks:

1. **Estimate Recalculation**:
   - Triggered via API endpoint: `POST /api/v1/estimates/recalculate`
   - Calculates maximum portions possible for all meals based on current inventory

2. **Monthly Report Generation**:
   - Triggered via API endpoint: `POST /api/v1/reports/monthly-summary/generate?month=YYYY-MM`
   - Generates monthly summary report and checks for discrepancy alerts

## 🔐 Role-Based Access Control

The system implements three user roles:

- **Admin**: Full access to all endpoints
- **Manager**: All except user management
- **Cook**: Limited to viewing data and serving meals

## 📂 Project Structure

```
kindergarten_kitchen/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API endpoints
│   │   ├── deps.py           # Dependencies (auth, DB session)
│   │   └── v1/               # API version 1 routers
│   ├── core/                 # Core functionality
│   │   ├── config.py         # Settings using pydantic-settings
│   │   ├── database.py       # Database connection
│   │   └── security.py       # JWT handling
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   ├── tasks/                # Celery tasks
│   │   ├── estimates.py      # Estimate recalculation task
│   │   ├── reports.py        # Report generation task
│   │   └── worker.py         # Celery worker configuration
│   ├── ws/                   # WebSocket handlers
│   │   └── inventory.py      # Real-time inventory updates
│   └── main.py               # FastAPI application
├── tests/                    # Test directory
├── .env                      # Environment variables (create this file)
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🐳 Docker Configuration

The project includes Docker configuration for easy deployment:

- **Dockerfile**: Builds the FastAPI application image
- **docker-compose.yml**: Orchestrates the following services:
  - **app**: FastAPI application
  - **celery_worker**: Celery worker for background tasks
  - **postgres**: PostgreSQL database
  - **redis**: Redis for Celery broker and result backend

## 🧪 Testing

To run tests (once implemented):

```bash
# With Docker
docker-compose exec app pytest

# Without Docker
pytest
```

## 📚 Additional Information

- **API Documentation**: Available at `/docs` when the application is running
- **Database Migrations**: Managed with Alembic
- **Environment Variables**: See `.env` file for configuration options
