# Home Service Management System

A full-stack web application for managing home service requests, built with FastAPI, MySQL, and a modern HTMX-based UI.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + MySQL
- **Frontend:** Jinja2 templates + HTMX + Bootstrap 5
- **Database:** MySQL 8.0+
- **Python:** 3.8+

## Features

- 🔍 Search providers by area and category
- 📝 Create and track service requests
- 💳 Process payments for completed services
- ⭐ Review providers after service completion
- 📊 Full RESTful API with interactive documentation
- 🎨 Modern, responsive web UI with dynamic updates (no page reloads)

## Quick Start

### 1. Prerequisites

- Python 3.8+
- MySQL 8.0+
- pip

### 2. Database Setup

Create the database and import the schema:

```bash
mysql -u root -p < mysql_schema.sql
```

Or manually:
```sql
CREATE DATABASE home_service_db;
USE home_service_db;
SOURCE mysql_schema.sql;
```

### 3. Environment Variables

Create a `.env` file in the project root (or set environment variables):

```bash
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=home_service_db
```

Alternatively, edit `backend/db.py` directly.

### 4. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 5. Run the Application

From the project root:

```bash
uvicorn backend.main:app --reload
```

The application will be available at:
- **Web UI:** http://localhost:8000/ui
- **API Docs:** http://localhost:8000/docs
- **My Requests:** http://localhost:8000/ui/requests
- **Seed Data:** http://localhost:8000/ui/seed

## Project Structure

```
TM/
├── backend/                 # FastAPI application
│   ├── __init__.py
│   ├── main.py             # Application entry point
│   ├── db.py               # Database connection
│   ├── models.py           # SQLAlchemy ORM models
│   ├── schemas.py          # Pydantic validation schemas
│   ├── crud.py             # CRUD operations
│   ├── requirements.txt    # Python dependencies
│   ├── routers/            # API and UI routes
│   │   ├── customers.py
│   │   ├── areas.py
│   │   ├── categories.py
│   │   ├── providers.py
│   │   ├── service_requests.py
│   │   ├── payments.py
│   │   ├── reviews.py
│   │   └── ui.py           # Web UI routes
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── requests.html
│   │   ├── seed.html
│   │   └── partials/       # HTMX partials
│   └── static/             # Static files (CSS)
│       └── styles.css
├── mysql_schema.sql        # Database schema
├── .env.example            # Environment variables template
├── README.md               # This file
└── docs/                   # Project documentation
    └── PROJECT_NOTES.md    # Architecture, migration, fixes
```

## API Endpoints

### Customers
- `GET /customers` - List all customers
- `GET /customers/{id}` - Get customer by ID
- `POST /customers` - Create new customer

### Service Areas
- `GET /areas` - List all areas
- `POST /areas` - Create new area

### Service Categories
- `GET /categories` - List all categories
- `POST /categories` - Create new category

### Service Providers
- `GET /providers` - List providers (filters: `?area_id=`, `?category_id=`)
- `GET /providers/{id}` - Get provider by ID
- `GET /providers/{id}/reviews` - Get provider reviews
- `POST /providers` - Create new provider

### Service Requests
- `GET /service-requests` - List requests (filters: `?customer_id=`, `?provider_id=`)
- `GET /service-requests/{id}` - Get request by ID
- `POST /service-requests` - Create new request
- `PATCH /service-requests/{id}/status` - Update request status

### Payments
- `GET /payments` - List payments (filter: `?request_id=`)
- `GET /payments/{id}` - Get payment by ID
- `POST /payments` - Create/update payment (upsert)

### Reviews
- `GET /reviews` - List all reviews
- `GET /reviews/{id}` - Get review by ID
- `POST /reviews` - Create new review

## Web UI Routes

- `GET /ui` - Home page (provider search)
- `GET /ui/requests` - My requests page
- `GET /ui/seed` - Seed demo data
- `GET /ui/providers/search` - Search providers (HTMX partial)
- `POST /ui/service-requests` - Create request (HTMX)
- `PATCH /ui/requests/{id}/status` - Update status (HTMX)
- `POST /ui/payments` - Create payment (HTMX)

## Development

### Running Tests

Use the interactive API documentation at http://localhost:8000/docs to test endpoints.

### Database Migrations

The schema is defined in `mysql_schema.sql`. To reset:
```bash
mysql -u root -p home_service_db < mysql_schema.sql
```

### Adding New Features

1. Add SQLAlchemy model in `backend/models.py`
2. Add Pydantic schemas in `backend/schemas.py`
3. Add CRUD functions in `backend/crud.py`
4. Add API routes in `backend/routers/`
5. Add UI routes in `backend/routers/ui.py` (if needed)
6. Add templates in `backend/templates/` (if needed)

## License

This project is part of a Database Systems course assignment.

