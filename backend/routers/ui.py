from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.db import get_db
from backend import crud
from backend.auth import verify_password

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# -----------------------------
# Session helpers
# -----------------------------
def current_user(request: Request) -> Optional[dict]:
    """Get current user from session"""
    return request.session.get("user")


def require_login(request: Request) -> Optional[RedirectResponse]:
    """Check if user is logged in, redirect to login if not"""
    if not request.session.get("user"):
        return RedirectResponse(url="/ui/login", status_code=303)
    return None


# -----------------------------
# Home / Marketplace
# -----------------------------
@router.get("/", response_class=HTMLResponse)
def ui_home(request: Request, db: Session = Depends(get_db)):
    """Customer marketplace home page"""
    try:
        areas = crud.get_service_areas(db)
        categories = crud.get_service_categories(db)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "areas": areas,
                "categories": categories,
                "user": current_user(request),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "areas": [],
                "categories": [],
                "user": current_user(request),
                "error": f"Error loading page: {str(e)}",
            },
        )


@router.post("/providers/search", response_class=HTMLResponse)
def ui_search_providers(
    request: Request,
    db: Session = Depends(get_db),
    area_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
):
    """Search providers and return table partial"""
    try:
        providers = crud.search_providers(db, area_id=area_id, category_id=category_id)
        return templates.TemplateResponse(
            "partials/providers_table.html",
            {"request": request, "providers": providers, "user": current_user(request)},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/providers_table.html",
            {"request": request, "providers": [], "user": current_user(request), "error": str(e)},
        )


# -----------------------------
# Service Requests (Customer)
# -----------------------------
@router.get("/requests", response_class=HTMLResponse)
def ui_requests(request: Request, db: Session = Depends(get_db)):
    """Customer's service requests page"""
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    if user["role"] != "customer":
        return RedirectResponse(url="/ui/", status_code=303)

    try:
        requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        return templates.TemplateResponse(
            "requests.html",
            {"request": request, "requests": requests_list, "user": user, "is_provider": False},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "requests.html",
            {"request": request, "requests": [], "user": user, "error": str(e), "is_provider": False},
        )


@router.get("/service-requests/form", response_class=HTMLResponse)
def ui_request_form(
    request: Request,
    provider_id: int,
    area_id: Optional[int] = None,
):
    """Return request form partial"""
    return templates.TemplateResponse(
        "partials/request_form.html",
        {
            "request": request,
            "provider_id": provider_id,
            "area_id": area_id,
            "user": current_user(request),
        },
    )


@router.post("/requests", response_class=HTMLResponse)
def ui_create_request(
    request: Request,
    db: Session = Depends(get_db),
    provider_id: int = Form(...),
    category_id: int = Form(1),  # Default category if not provided
    area_id: int = Form(1),  # Default area if not provided
    address: str = Form(...),
    description: str = Form(""),
):
    """Create a new service request"""
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    if user["role"] != "customer":
        return RedirectResponse(url="/ui/", status_code=303)

    try:
        crud.create_service_request(
            db,
            customer_id=user["user_id"],
            provider_id=provider_id,
            category_id=category_id,
            area_id=area_id,
            address=address,
            description=description,
        )
        return RedirectResponse(url="/ui/requests", status_code=303)
    except Exception as e:
        # Return to home with error
        return RedirectResponse(url=f"/ui/?error={str(e)}", status_code=303)


@router.patch("/requests/{request_id}/status", response_class=HTMLResponse)
def ui_update_request_status(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db),
    status: str = Form(...),
):
    """Update request status and return updated table"""
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    
    try:
        crud.update_request_status(db, request_id, status)
        
        # Return updated requests list based on user role
        if user["role"] == "customer":
            requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        else:
            requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        
        return templates.TemplateResponse(
            "partials/requests_table.html",
            {"request": request, "requests": requests_list, "user": user},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/requests_table.html",
            {"request": request, "requests": [], "user": user, "error": str(e)},
        )


# -----------------------------
# Provider Dashboard
# -----------------------------
@router.get("/provider", response_class=HTMLResponse)
def ui_provider_dashboard(request: Request, db: Session = Depends(get_db)):
    """Provider dashboard page"""
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    if user["role"] != "provider":
        return RedirectResponse(url="/ui/", status_code=303)

    try:
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "requests.html",  # Reuse requests template
            {
                "request": request,
                "requests": requests_list,
                "user": user,
                "is_provider": True,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "requests.html",
            {
                "request": request,
                "requests": [],
                "user": user,
                "is_provider": True,
                "error": str(e),
            },
        )


# -----------------------------
# Auth: login / register / logout
# -----------------------------
@router.get("/login", response_class=HTMLResponse)
def ui_login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "user": current_user(request)}
    )


@router.post("/login")
def ui_login(
    request: Request,
    db: Session = Depends(get_db),
    role: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    """Handle login"""
    role = role.strip().lower()
    email = email.strip().lower()

    if role not in {"customer", "provider"}:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid role selected.", "user": None},
        )

    try:
        if role == "customer":
            user_obj = crud.get_customer_by_email(db, email)
            if not user_obj:
                return templates.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Invalid email or password.", "user": None},
                )
            
            if not verify_password(password, user_obj.password_hash):
                return templates.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Invalid email or password.", "user": None},
                )
            
            user_id = user_obj.customer_id
            name = f"{user_obj.first_name} {user_obj.last_name}"
        
        else:  # provider
            user_obj = crud.get_provider_by_email(db, email)
            if not user_obj:
                return templates.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Invalid email or password.", "user": None},
                )
            
            if not verify_password(password, user_obj.password_hash):
                return templates.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Invalid email or password.", "user": None},
                )
            
            user_id = user_obj.provider_id
            name = f"{user_obj.first_name} {user_obj.last_name}"

        request.session["user"] = {
            "user_id": int(user_id),
            "role": role,
            "email": email,
            "name": name,
        }

        # Redirect based on role
        if role == "provider":
            return RedirectResponse(url="/ui/provider", status_code=303)
        else:
            return RedirectResponse(url="/ui/", status_code=303)
    
    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Login error: {str(e)}", "user": None},
        )


@router.get("/register", response_class=HTMLResponse)
def ui_register_page(request: Request, db: Session = Depends(get_db)):
    """Registration page"""
    try:
        areas = crud.get_service_areas(db)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "areas": areas, "user": current_user(request)}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "areas": [], "user": current_user(request), "error": str(e)}
        )


@router.post("/register")
def ui_register(
    request: Request,
    db: Session = Depends(get_db),
    role: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    area_id: Optional[int] = Form(None),
    password: str = Form(...),
    confirm_password: str = Form(...),
    hourly_rate: float = Form(0.0),
):
    """Handle registration"""
    role = role.strip().lower()
    email = email.strip().lower()

    if password != confirm_password:
        areas = crud.get_service_areas(db)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "areas": areas, "error": "Passwords do not match.", "user": None},
        )

    try:
        if role == "customer":
            # Check if email exists
            if crud.get_customer_by_email(db, email):
                areas = crud.get_service_areas(db)
                return templates.TemplateResponse(
                    "register.html",
                    {"request": request, "areas": areas, "error": "Email already registered.", "user": None},
                )
            
            customer = crud.create_customer(
                db, first_name, last_name, email, phone, address, area_id, password
            )
            request.session["user"] = {
                "user_id": customer.customer_id,
                "role": "customer",
                "email": email,
                "name": f"{first_name} {last_name}",
            }
            return RedirectResponse(url="/ui/", status_code=303)

        elif role == "provider":
            # Check if email exists
            if crud.get_provider_by_email(db, email):
                areas = crud.get_service_areas(db)
                return templates.TemplateResponse(
                    "register.html",
                    {"request": request, "areas": areas, "error": "Email already registered.", "user": None},
                )
            
            provider = crud.create_provider(
                db, first_name, last_name, email, phone, address, area_id, hourly_rate, password
            )
            request.session["user"] = {
                "user_id": provider.provider_id,
                "role": "provider",
                "email": email,
                "name": f"{first_name} {last_name}",
            }
            return RedirectResponse(url="/ui/provider", status_code=303)
        
        else:
            areas = crud.get_service_areas(db)
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "areas": areas, "error": "Invalid role.", "user": None},
            )
    
    except Exception as e:
        areas = crud.get_service_areas(db)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "areas": areas, "error": f"Registration error: {str(e)}", "user": None},
        )


@router.post("/logout")
def ui_logout(request: Request):
    """Handle logout"""
    request.session.clear()
    return RedirectResponse(url="/ui/", status_code=303)


# -----------------------------
# Lifecycle Actions (HTMX)
# -----------------------------
@router.post("/provider/requests/{request_id}/accept", response_class=HTMLResponse)
def ui_provider_accept(request_id: int, request: Request, db: Session = Depends(get_db)):
    """Provider accepts a pending request (HTMX)"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    user = current_user(request)
    if user["role"] != "provider":
        return HTMLResponse("<div class='alert alert-error'>Only providers can accept requests</div>", status_code=403)
    
    try:
        crud.provider_accept_request(db, request_id, user["user_id"])
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user}
        )
    except ValueError as e:
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user, "error": str(e)}
        )


@router.post("/provider/requests/{request_id}/complete", response_class=HTMLResponse)
def ui_provider_complete(request_id: int, request: Request, db: Session = Depends(get_db)):
    """Provider marks request as completed (HTMX)"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    user = current_user(request)
    if user["role"] != "provider":
        return HTMLResponse("<div class='alert alert-error'>Only providers can complete requests</div>", status_code=403)
    
    try:
        crud.provider_complete_request(db, request_id, user["user_id"])
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user}
        )
    except ValueError as e:
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user, "error": str(e)}
        )


@router.post("/provider/requests/{request_id}/cancel", response_class=HTMLResponse)
def ui_provider_cancel(request_id: int, request: Request, db: Session = Depends(get_db)):
    """Provider cancels a request (HTMX)"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    user = current_user(request)
    if user["role"] != "provider":
        return HTMLResponse("<div class='alert alert-error'>Only providers can cancel requests</div>", status_code=403)
    
    try:
        crud.update_request_status(db, request_id, "cancelled")
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user}
        )
    except Exception as e:
        requests_list = crud.list_requests_for_provider(db, provider_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/provider_requests.html",
            {"request": request, "requests": requests_list, "user": user, "error": str(e)}
        )


@router.post("/customer/requests/{request_id}/pay", response_class=HTMLResponse)
def ui_customer_pay(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
    payment_method: str = Form(...),
    amount: Optional[float] = Form(None)
):
    """Customer pays for completed request (HTMX)"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    user = current_user(request)
    if user["role"] != "customer":
        return HTMLResponse("<div class='alert alert-error'>Only customers can make payments</div>", status_code=403)
    
    try:
        crud.customer_pay_request(db, request_id, user["user_id"], payment_method, amount)
        requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/customer_requests.html",
            {"request": request, "requests": requests_list, "user": user}
        )
    except ValueError as e:
        requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/customer_requests.html",
            {"request": request, "requests": requests_list, "user": user, "error": str(e)}
        )


@router.post("/customer/requests/{request_id}/review", response_class=HTMLResponse)
def ui_customer_review(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
    rating: int = Form(...),
    comment: Optional[str] = Form(None)
):
    """Customer adds review for completed request (HTMX)"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    user = current_user(request)
    if user["role"] != "customer":
        return HTMLResponse("<div class='alert alert-error'>Only customers can add reviews</div>", status_code=403)
    
    try:
        crud.customer_add_review(db, request_id, user["user_id"], rating, comment)
        requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/customer_requests.html",
            {"request": request, "requests": requests_list, "user": user}
        )
    except ValueError as e:
        requests_list = crud.list_requests_for_customer(db, customer_id=user["user_id"])
        return templates.TemplateResponse(
            "partials/customer_requests.html",
            {"request": request, "requests": requests_list, "user": user, "error": str(e)}
        )
