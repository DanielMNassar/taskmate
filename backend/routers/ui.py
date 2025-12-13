from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from ..db import get_db
from .. import crud
from ..schemas import ServiceRequestCreate, ServiceRequestUpdateStatus, PaymentCreate

router = APIRouter()

# Templates will be initialized in main.py and passed here
templates = None

def set_templates(templates_instance):
    """Set templates instance from main.py"""
    global templates
    templates = templates_instance


@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request, db: Session = Depends(get_db)):
    """Home page with provider search"""
    areas = crud.get_areas(db, skip=0, limit=100)
    categories = crud.get_categories(db, skip=0, limit=100)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "areas": areas,
        "categories": categories
    })


@router.get("/providers/search", response_class=HTMLResponse)
async def search_providers(
    request: Request,
    area_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Search providers and return partial table"""
    providers = crud.get_providers_by_area_category(db, area_id=area_id, category_id=category_id)
    
    # Load area relationships for display
    for provider in providers:
        if provider.area_id:
            provider.area = crud.get_area(db, provider.area_id)
    
    return templates.TemplateResponse("partials/providers_table.html", {
        "request": request,
        "providers": providers
    })


@router.get("/service-requests/form", response_class=HTMLResponse)
async def get_request_form(
    request: Request,
    provider_id: int,
    area_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get request form partial with provider info"""
    provider = crud.get_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Get first category for this provider (or use a default)
    category_id = None
    if provider.categories:
        category_id = provider.categories[0].category_id
    
    return templates.TemplateResponse("partials/request_form.html", {
        "request": request,
        "provider_id": provider_id,
        "category_id": category_id,
        "area_id": area_id or provider.area_id
    })


@router.post("/service-requests", response_class=HTMLResponse)
async def create_service_request_ui(
    request: Request,
    customer_id: int = Form(...),
    provider_id: Optional[int] = Form(None),
    category_id: int = Form(...),
    area_id: int = Form(...),
    address: str = Form(...),
    description: Optional[str] = Form(None),
    cost: Optional[Decimal] = Form(None),
    db: Session = Depends(get_db)
):
    """Create service request from UI form"""
    try:
        service_request = ServiceRequestCreate(
            customer_id=customer_id,
            provider_id=provider_id if provider_id else None,
            category_id=category_id,
            area_id=area_id,
            address=address,
            description=description,
            cost=cost
        )
        result = crud.create_service_request(db, service_request)
        
        return templates.TemplateResponse("partials/alerts.html", {
            "request": request,
            "alert_type": "success",
            "message": f"Service request #{result.request_id} created successfully!"
        })
    except Exception as e:
        return templates.TemplateResponse("partials/alerts.html", {
            "request": request,
            "alert_type": "error",
            "message": f"Error creating request: {str(e)}"
        })


@router.get("/requests", response_class=HTMLResponse)
async def ui_requests(request: Request, db: Session = Depends(get_db)):
    """My requests page"""
    customer_id = 1  # Demo customer
    requests_list = crud.get_service_requests(db, customer_id=customer_id, skip=0, limit=100)
    
    # Load related data for display
    for req in requests_list:
        if req.category_id:
            req.category = crud.get_category(db, req.category_id)
        if req.provider_id:
            req.provider = crud.get_provider(db, req.provider_id)
        if req.area_id:
            req.area = crud.get_area(db, req.area_id)
    
    return templates.TemplateResponse("requests.html", {
        "request": request,
        "requests": requests_list,
        "customer_id": customer_id
    })


@router.get("/requests/table", response_class=HTMLResponse)
async def get_requests_table(request: Request, db: Session = Depends(get_db)):
    """Get requests table partial for HTMX refresh"""
    customer_id = 1  # Demo customer
    requests_list = crud.get_service_requests(db, customer_id=customer_id, skip=0, limit=100)
    
    # Load related data for display
    for req in requests_list:
        if req.category_id:
            req.category = crud.get_category(db, req.category_id)
        if req.provider_id:
            req.provider = crud.get_provider(db, req.provider_id)
        if req.area_id:
            req.area = crud.get_area(db, req.area_id)
    
    return templates.TemplateResponse("partials/requests_table.html", {
        "request": request,
        "requests": requests_list
    })


@router.patch("/requests/{request_id}/status", response_class=HTMLResponse)
async def update_request_status_ui(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db)
):
    """Update request status from UI"""
    try:
        form_data = await request.form()
        status = form_data.get("status")
        
        if not status:
            raise ValueError("Status is required")
        
        status_update = ServiceRequestUpdateStatus(status=status)
        result = crud.update_service_request_status(db, request_id, status_update)
        
        if not result:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Return updated table
        return await get_requests_table(request, db)
    except Exception as e:
        return templates.TemplateResponse("partials/alerts.html", {
            "request": request,
            "alert_type": "error",
            "message": f"Error updating status: {str(e)}"
        })


@router.get("/payments/form", response_class=HTMLResponse)
async def get_payment_form(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db)
):
    """Get payment form partial"""
    service_request = crud.get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=404, detail="Service request not found")
    
    return templates.TemplateResponse("partials/payment_form.html", {
        "request": request,
        "request_id": request_id
    })


@router.post("/payments", response_class=HTMLResponse)
async def create_payment_ui(
    request: Request,
    request_id: int = Form(...),
    amount: Decimal = Form(...),
    payment_method: str = Form(...),
    payment_status: str = Form("pending"),
    db: Session = Depends(get_db)
):
    """Create payment from UI form"""
    try:
        payment = PaymentCreate(
            request_id=request_id,
            amount=amount,
            payment_method=payment_method,
            payment_status=payment_status
        )
        result = crud.create_payment(db, payment)
        
        return templates.TemplateResponse("partials/alerts.html", {
            "request": request,
            "alert_type": "success",
            "message": f"Payment #{result.payment_id} created successfully!"
        })
    except Exception as e:
        return templates.TemplateResponse("partials/alerts.html", {
            "request": request,
            "alert_type": "error",
            "message": f"Error creating payment: {str(e)}"
        })


@router.get("/seed", response_class=HTMLResponse)
async def seed_demo_data(request: Request, db: Session = Depends(get_db)):
    """Seed demo data if tables are empty"""
    inserted = {}
    
    # Check and insert areas
    areas = crud.get_areas(db, skip=0, limit=1)
    if not areas:
        from ..schemas import ServiceAreaCreate
        area1 = crud.create_area(db, ServiceAreaCreate(
            city="New York",
            district="Manhattan",
            postal_code="10001"
        ))
        area2 = crud.create_area(db, ServiceAreaCreate(
            city="Los Angeles",
            district="Downtown",
            postal_code="90012"
        ))
        inserted["areas"] = 2
    
    # Check and insert categories
    categories = crud.get_categories(db, skip=0, limit=1)
    if not categories:
        from ..schemas import ServiceCategoryCreate
        cat1 = crud.create_category(db, ServiceCategoryCreate(
            name="Plumbing",
            description="Plumbing and pipe repair services"
        ))
        cat2 = crud.create_category(db, ServiceCategoryCreate(
            name="Electrical",
            description="Electrical repair and installation"
        ))
        cat3 = crud.create_category(db, ServiceCategoryCreate(
            name="Cleaning",
            description="House cleaning services"
        ))
        inserted["categories"] = 3
    
    # Check and insert customer
    customers = crud.get_customers(db, skip=0, limit=1)
    if not customers:
        from ..schemas import CustomerCreate
        customer = crud.create_customer(db, CustomerCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="555-0100",
            address="123 Main Street",
            area_id=1
        ))
        inserted["customer"] = customer.customer_id
    
    # Check and insert providers
    providers = crud.get_providers(db, skip=0, limit=1)
    if not providers:
        from ..schemas import ServiceProviderCreate
        from ..models import AvailabilityStatus
        
        provider1 = crud.create_provider(db, ServiceProviderCreate(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="555-0200",
            address="456 Oak Avenue",
            area_id=1,
            hourly_rate=Decimal("50.00"),
            availability_status=AvailabilityStatus.available,
            category_ids=[1, 2]
        ))
        
        provider2 = crud.create_provider(db, ServiceProviderCreate(
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com",
            phone="555-0300",
            address="789 Pine Street",
            area_id=1,
            hourly_rate=Decimal("45.00"),
            availability_status=AvailabilityStatus.available,
            category_ids=[3]
        ))
        
        inserted["providers"] = 2
    
    return templates.TemplateResponse("seed.html", {
        "request": request,
        "inserted": inserted if inserted else None
    })

