import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

# Routers
from backend.routers.ui import router as ui_router
from backend.routers.admin import router as admin_router
from backend.routers.lifecycle import router as lifecycle_router

app = FastAPI(title="TaskMate")

# --- CORS (keep permissive for course demo) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Sessions ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False,   # set True only if you host with HTTPS
)

# --- Static files ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- UI routes ---
app.include_router(ui_router, prefix="/ui", tags=["ui"])

# --- Admin routes (NOT exposed in UI) ---
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# --- API routes: Request Lifecycle ---
app.include_router(lifecycle_router, tags=["lifecycle"])

# (Optional) If you have other API routers, include them here as well:
# from backend.routers.customers import router as customers_router
# app.include_router(customers_router, prefix="/api")
