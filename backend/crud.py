from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

try:
    from .models import (
        ServiceArea, ServiceCategory, Customer, ServiceProvider,
        ProviderCategory, ServiceRequest, Payment, Review
    )
    from .schemas import (
        ServiceAreaCreate, ServiceCategoryCreate, CustomerCreate,
        ServiceProviderCreate, ServiceRequestCreate, PaymentCreate, PaymentUpdate,
        ReviewCreate, ServiceRequestUpdateStatus
    )
except ImportError:
    from models import (
        ServiceArea, ServiceCategory, Customer, ServiceProvider,
        ProviderCategory, ServiceRequest, Payment, Review
    )
    from schemas import (
        ServiceAreaCreate, ServiceCategoryCreate, CustomerCreate,
        ServiceProviderCreate, ServiceRequestCreate, PaymentCreate, PaymentUpdate,
        ReviewCreate, ServiceRequestUpdateStatus
    )


# ========== SERVICE AREA CRUD ==========
def get_area(db: Session, area_id: int) -> Optional[ServiceArea]:
    return db.query(ServiceArea).filter(ServiceArea.area_id == area_id).first()


def get_areas(db: Session, skip: int = 0, limit: int = 100) -> List[ServiceArea]:
    return db.query(ServiceArea).offset(skip).limit(limit).all()


def create_area(db: Session, area: ServiceAreaCreate) -> ServiceArea:
    db_area = ServiceArea(**area.dict())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area


# ========== SERVICE CATEGORY CRUD ==========
def get_category(db: Session, category_id: int) -> Optional[ServiceCategory]:
    return db.query(ServiceCategory).filter(ServiceCategory.category_id == category_id).first()


def get_categories(db: Session, skip: int = 0, limit: int = 100) -> List[ServiceCategory]:
    return db.query(ServiceCategory).offset(skip).limit(limit).all()


def create_category(db: Session, category: ServiceCategoryCreate) -> ServiceCategory:
    db_category = ServiceCategory(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


# ========== CUSTOMER CRUD ==========
def get_customer(db: Session, customer_id: int) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()


def get_customers(db: Session, skip: int = 0, limit: int = 100) -> List[Customer]:
    return db.query(Customer).offset(skip).limit(limit).all()


def create_customer(db: Session, customer: CustomerCreate) -> Customer:
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    try:
        db.commit()
        db.refresh(db_customer)
        return db_customer
    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation (duplicate email)
        if "UNIQUE constraint" in str(e) or "Duplicate entry" in str(e) or "email" in str(e).lower():
            raise ValueError(f"Email {customer.email} is already registered")
        raise


# ========== SERVICE PROVIDER CRUD ==========
def get_provider(db: Session, provider_id: int) -> Optional[ServiceProvider]:
    return db.query(ServiceProvider).filter(ServiceProvider.provider_id == provider_id).first()


def get_providers(db: Session, skip: int = 0, limit: int = 100) -> List[ServiceProvider]:
    return db.query(ServiceProvider).offset(skip).limit(limit).all()


def create_provider(db: Session, provider: ServiceProviderCreate) -> ServiceProvider:
    provider_data = provider.dict()
    category_ids = provider_data.pop('category_ids', [])
    
    db_provider = ServiceProvider(**provider_data)
    db.add(db_provider)
    db.flush()
    
    # Add categories
    for cat_id in category_ids:
        db_provider_category = ProviderCategory(
            provider_id=db_provider.provider_id,
            category_id=cat_id
        )
        db.add(db_provider_category)
    
    try:
        db.commit()
        db.refresh(db_provider)
        return db_provider
    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation (duplicate email)
        if "UNIQUE constraint" in str(e) or "Duplicate entry" in str(e) or "email" in str(e).lower():
            raise ValueError(f"Email {provider.email} is already registered")
        raise


def get_providers_by_area_category(db: Session, area_id: Optional[int] = None, category_id: Optional[int] = None) -> List[ServiceProvider]:
    query = db.query(ServiceProvider)
    
    if category_id:
        # Only join when filtering by category
        query = query.join(ProviderCategory).filter(ProviderCategory.category_id == category_id)
    
    if area_id:
        query = query.filter(ServiceProvider.area_id == area_id)
    
    return query.distinct().all()


# ========== SERVICE REQUEST CRUD ==========
def get_service_request(db: Session, request_id: int) -> Optional[ServiceRequest]:
    return db.query(ServiceRequest).filter(ServiceRequest.request_id == request_id).first()


def get_service_requests(
    db: Session,
    customer_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ServiceRequest]:
    query = db.query(ServiceRequest)
    
    if customer_id:
        query = query.filter(ServiceRequest.customer_id == customer_id)
    if provider_id:
        query = query.filter(ServiceRequest.provider_id == provider_id)
    
    return query.offset(skip).limit(limit).all()


def create_service_request(db: Session, request: ServiceRequestCreate) -> ServiceRequest:
    db_request = ServiceRequest(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def update_service_request_status(
    db: Session,
    request_id: int,
    status_update: ServiceRequestUpdateStatus
) -> Optional[ServiceRequest]:
    db_request = get_service_request(db, request_id)
    if not db_request:
        return None
    
    db_request.status = status_update.status
    if status_update.cancellation_date:
        db_request.cancellation_date = status_update.cancellation_date
    
    db.commit()
    db.refresh(db_request)
    return db_request


# ========== PAYMENT CRUD ==========
def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    return db.query(Payment).filter(Payment.payment_id == payment_id).first()


def get_payments(db: Session, request_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Payment]:
    query = db.query(Payment)
    
    if request_id:
        query = query.filter(Payment.request_id == request_id)
    
    return query.offset(skip).limit(limit).all()


def create_payment(db: Session, payment: PaymentCreate) -> Payment:
    # Check if payment already exists for this request_id (upsert logic)
    existing_payment = db.query(Payment).filter(Payment.request_id == payment.request_id).first()
    
    if existing_payment:
        # Update existing payment (upsert behavior - matches old Tkinter ON DUPLICATE KEY UPDATE)
        existing_payment.amount = payment.amount
        existing_payment.payment_method = payment.payment_method
        existing_payment.payment_status = payment.payment_status
        # payment_date is not updated on upsert (preserve original, matches old behavior)
        db.commit()
        db.refresh(existing_payment)
        return existing_payment
    else:
        # Create new payment
        db_payment = Payment(**payment.dict())
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment


def update_payment(db: Session, request_id: int, payment_update: PaymentUpdate) -> Optional[Payment]:
    """Update payment by request_id"""
    db_payment = db.query(Payment).filter(Payment.request_id == request_id).first()
    if not db_payment:
        return None
    
    if payment_update.amount is not None:
        db_payment.amount = payment_update.amount
    if payment_update.payment_method is not None:
        db_payment.payment_method = payment_update.payment_method
    if payment_update.payment_status is not None:
        db_payment.payment_status = payment_update.payment_status
    
    db.commit()
    db.refresh(db_payment)
    return db_payment


# ========== REVIEW CRUD ==========
def get_review(db: Session, review_id: int) -> Optional[Review]:
    return db.query(Review).filter(Review.review_id == review_id).first()


def get_reviews(db: Session, skip: int = 0, limit: int = 100) -> List[Review]:
    return db.query(Review).offset(skip).limit(limit).all()


def get_reviews_for_provider(db: Session, provider_id: int, skip: int = 0, limit: int = 100) -> List[Review]:
    return db.query(Review).filter(Review.provider_id == provider_id).offset(skip).limit(limit).all()


def create_review(db: Session, review: ReviewCreate) -> Review:
    # Validate that the service request exists
    service_request = get_service_request(db, review.request_id)
    if not service_request:
        raise ValueError(f"Service request {review.request_id} not found")
    
    # Validate customer_id matches
    if service_request.customer_id != review.customer_id:
        raise ValueError(f"Customer ID {review.customer_id} does not match service request customer {service_request.customer_id}")
    
    # Reject if provider is not assigned to the request
    if not service_request.provider_id:
        raise ValueError(f"Service request {review.request_id} has no provider assigned. Cannot create review.")
    
    # Validate provider_id matches
    if service_request.provider_id != review.provider_id:
        raise ValueError(f"Provider ID {review.provider_id} does not match service request provider {service_request.provider_id}")
    
    db_review = Review(**review.dict())
    db.add(db_review)
    try:
        db.commit()
        db.refresh(db_review)
        return db_review
    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation (request_id already has a review)
        if "UNIQUE constraint" in str(e) or "Duplicate entry" in str(e) or "uk_review_request" in str(e):
            raise ValueError(f"Review already exists for service request {review.request_id}")
        raise

