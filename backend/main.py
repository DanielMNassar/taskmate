from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

try:
    from .db import engine, Base
    from .routers import (
        customers, areas, categories, providers,
        service_requests, payments, reviews, ui
    )
except ImportError:
    from db import engine, Base
    from routers import (
        customers, areas, categories, providers,
        service_requests, payments, reviews, ui
    )

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Home Service Management System API",
    description="RESTful API for managing home service requests, providers, customers, and payments",
    version="1.0.0"
)

# Setup templates and static files
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

templates = Jinja2Templates(directory=templates_dir)
ui.set_templates(templates)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customers.router)
app.include_router(areas.router)
app.include_router(categories.router)
app.include_router(providers.router)
app.include_router(service_requests.router)
app.include_router(payments.router)
app.include_router(reviews.router)

# Include UI router
app.include_router(ui.router, prefix="/ui", tags=["ui"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Home Service Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

