from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from backend import models
from backend.auth import hash_password, verify_password

# -----------------------------
# Helpers
# -----------------------------
def _row_to_dict(row) -> Dict[str, Any]:
    """Convert SQLAlchemy Row to dict"""
    if row is None:
        return None
    return dict(row._mapping)


# -----------------------------
# Lookups for filters
# -----------------------------
def get_service_areas(db: Session) -> List[Dict[str, Any]]:
    """Get all service areas"""
    q = text("""
        SELECT area_id, city, district, postal_code
        FROM service_area
        ORDER BY city, district
    """)
    return [_row_to_dict(r) for r in db.execute(q).fetchall()]


def get_service_categories(db: Session) -> List[Dict[str, Any]]:
    """Get all service categories"""
    q = text("""
        SELECT category_id, name, description
        FROM service_category
        ORDER BY name 
    """)
    return [_row_to_dict(r) for r in db.execute(q).fetchall()]


def search_providers(db: Session, area_id: Optional[int] = None, category_id: Optional[int] = None) -> List[models.ServiceProvider]:
    """Search providers with filters, return ORM objects with relationships"""
    sql = """
        SELECT DISTINCT
            sp.provider_id,
            sp.first_name,
            sp.last_name,
            sp.email,
            sp.phone,
            sp.address,
            sp.area_id,
            sp.hourly_rate,
            sp.availability_status,
            sp.date_joined,
            sp.password_hash,
            sa.area_id AS sa_area_id,
            sa.city,
            sa.district,
            sa.postal_code
        FROM service_provider sp
        LEFT JOIN service_area sa ON sp.area_id = sa.area_id
    """
    
    conditions = []
    params = {}
    
    if area_id:
        conditions.append("sp.area_id = :area_id")
        params["area_id"] = area_id
    
    if category_id:
        sql += """
        INNER JOIN provider_category pc ON sp.provider_id = pc.provider_id
        """
        conditions.append("pc.category_id = :category_id")
        params["category_id"] = category_id
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += """
        ORDER BY 
            sp.availability_status DESC,
            sp.hourly_rate ASC,
            sp.last_name ASC
    """
    
    result = db.execute(text(sql), params)
    providers = []
    seen_ids = set()
    
    for row in result.fetchall():
        provider_id = row.provider_id
        if provider_id in seen_ids:
            continue
        seen_ids.add(provider_id)
        
        # Construct ServiceArea if area_id exists
        area = None
        if row.area_id:
            area = models.ServiceArea(
                area_id=row.sa_area_id,
                city=row.city,
                district=row.district,
                postal_code=row.postal_code
            )
        
        # Construct ServiceProvider
        provider = models.ServiceProvider(
            provider_id=provider_id,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            phone=row.phone,
            address=row.address,
            area_id=row.area_id,
            hourly_rate=float(row.hourly_rate),
            availability_status=models.AvailabilityStatus(row.availability_status),
            date_joined=row.date_joined,
            password_hash=row.password_hash
        )
        provider.area = area
        providers.append(provider)
    
    return providers


# -----------------------------
# Requests
# -----------------------------
def create_service_request(
    db: Session,
    customer_id: int,
    provider_id: int,
    category_id: int,
    area_id: int,
    address: str,
    description: Optional[str] = None,
    cost: Optional[float] = None,
) -> int:
    """Create a new service request"""
    sql = """
        INSERT INTO service_request 
        (customer_id, provider_id, category_id, area_id, address, description, cost, status)
        VALUES (:customer_id, :provider_id, :category_id, :area_id, :address, :description, :cost, 'pending')
    """
    
    params = {
        "customer_id": customer_id,
        "provider_id": provider_id,
        "category_id": category_id,
        "area_id": area_id,
        "address": address,
        "description": description,
        "cost": cost
    }
    
    db.execute(text(sql), params)
    db.commit()
    
    # Get the inserted ID
    result = db.execute(text("SELECT LAST_INSERT_ID() as id"))
    request_id = result.scalar()
    
    return request_id


def list_requests_for_customer(db: Session, customer_id: int) -> List[models.ServiceRequest]:
    """List all service requests for a customer, with relationships loaded"""
    # Fetch main requests
    sql = """
        SELECT request_id, customer_id, provider_id, category_id, area_id,
               address, description, status, cost, request_date, cancellation_date
        FROM service_request
        WHERE customer_id = :customer_id
        ORDER BY request_date DESC
    """
    result = db.execute(text(sql), {"customer_id": customer_id})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    # Collect IDs for batch loading
    request_ids = [row.request_id for row in rows]
    provider_ids = list(set(row.provider_id for row in rows if row.provider_id))
    category_ids = list(set(row.category_id for row in rows))
    area_ids = list(set(row.area_id for row in rows))
    
    # Batch load related entities
    customers = _load_customers_by_ids(db, [customer_id])
    providers = _load_providers_by_ids(db, provider_ids) if provider_ids else {}
    categories = _load_categories_by_ids(db, category_ids) if category_ids else {}
    areas = _load_areas_by_ids(db, area_ids) if area_ids else {}
    payments = _load_payments_by_request_ids(db, request_ids) if request_ids else {}
    reviews = _load_reviews_by_request_ids(db, request_ids) if request_ids else {}
    
    # Build request objects
    requests = []
    for row in rows:
        request = models.ServiceRequest(
            request_id=row.request_id,
            customer_id=row.customer_id,
            provider_id=row.provider_id,
            category_id=row.category_id,
            area_id=row.area_id,
            address=row.address,
            description=row.description,
            status=models.RequestStatus(row.status),
            cost=float(row.cost) if row.cost else None,
            request_date=row.request_date,
            cancellation_date=row.cancellation_date
        )
        
        # Attach relationships
        request.customer = customers.get(row.customer_id)
        request.provider = providers.get(row.provider_id) if row.provider_id else None
        request.category = categories.get(row.category_id)
        request.area = areas.get(row.area_id)
        request.payment = payments.get(row.request_id)
        request.review = reviews.get(row.request_id)
        
        requests.append(request)
    
    return requests


def list_requests_for_provider(db: Session, provider_id: int) -> List[models.ServiceRequest]:
    """List all service requests for a provider, with relationships loaded"""
    # Fetch main requests
    sql = """
        SELECT request_id, customer_id, provider_id, category_id, area_id,
               address, description, status, cost, request_date, cancellation_date
        FROM service_request
        WHERE provider_id = :provider_id
        ORDER BY request_date DESC
    """
    result = db.execute(text(sql), {"provider_id": provider_id})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    # Collect IDs for batch loading
    request_ids = [row.request_id for row in rows]
    customer_ids = list(set(row.customer_id for row in rows))
    category_ids = list(set(row.category_id for row in rows))
    area_ids = list(set(row.area_id for row in rows))
    
    # Batch load related entities
    customers = _load_customers_by_ids(db, customer_ids) if customer_ids else {}
    providers = _load_providers_by_ids(db, [provider_id]) if provider_id else {}
    categories = _load_categories_by_ids(db, category_ids) if category_ids else {}
    areas = _load_areas_by_ids(db, area_ids) if area_ids else {}
    payments = _load_payments_by_request_ids(db, request_ids) if request_ids else {}
    reviews = _load_reviews_by_request_ids(db, request_ids) if request_ids else {}
    
    # Build request objects
    requests = []
    for row in rows:
        request = models.ServiceRequest(
            request_id=row.request_id,
            customer_id=row.customer_id,
            provider_id=row.provider_id,
            category_id=row.category_id,
            area_id=row.area_id,
            address=row.address,
            description=row.description,
            status=models.RequestStatus(row.status),
            cost=float(row.cost) if row.cost else None,
            request_date=row.request_date,
            cancellation_date=row.cancellation_date
        )
        
        # Attach relationships
        request.customer = customers.get(row.customer_id)
        request.provider = providers.get(row.provider_id) if row.provider_id else None
        request.category = categories.get(row.category_id)
        request.area = areas.get(row.area_id)
        request.payment = payments.get(row.request_id)
        request.review = reviews.get(row.request_id)
        
        requests.append(request)
    
    return requests


def update_request_status(db: Session, request_id: int, new_status: str) -> None:
    """Update service request status"""
    if new_status == "cancelled":
        sql = """
            UPDATE service_request 
            SET status = :status, cancellation_date = NOW()
            WHERE request_id = :request_id
        """
    else:
        sql = """
            UPDATE service_request 
            SET status = :status
            WHERE request_id = :request_id
        """
    
    params = {
        "request_id": request_id,
        "status": new_status
    }
    
    db.execute(text(sql), params)
    db.commit()


# -----------------------------
# Auth (customer/provider)
# -----------------------------
def get_customer_by_email(db: Session, email: str) -> Optional[models.Customer]:
    """Get customer by email, return ORM object"""
    sql = """
        SELECT 
            customer_id,
            first_name,
            last_name,
            email,
            phone,
            address,
            area_id,
            registration_date,
            password_hash
        FROM customer
        WHERE email = :email
    """
    
    result = db.execute(text(sql), {"email": email})
    row = result.fetchone()
    
    if not row:
        return None
    
    # Build ServiceArea if area_id exists
    area = None
    if row.area_id:
        area_sql = """
            SELECT area_id, city, district, postal_code
            FROM service_area
            WHERE area_id = :area_id
        """
        area_result = db.execute(text(area_sql), {"area_id": row.area_id})
        area_row = area_result.fetchone()
        if area_row:
            area = models.ServiceArea(
                area_id=area_row.area_id,
                city=area_row.city,
                district=area_row.district,
                postal_code=area_row.postal_code
            )
    
    customer = models.Customer(
        customer_id=row.customer_id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        phone=row.phone,
        address=row.address,
        area_id=row.area_id,
        registration_date=row.registration_date,
        password_hash=row.password_hash
    )
    customer.area = area
    
    return customer


def get_provider_by_email(db: Session, email: str) -> Optional[models.ServiceProvider]:
    """Get provider by email, return ORM object"""
    sql = """
        SELECT 
            provider_id,
            first_name,
            last_name,
            email,
            phone,
            address,
            area_id,
            hourly_rate,
            availability_status,
            date_joined,
            password_hash
        FROM service_provider
        WHERE email = :email
    """
    
    result = db.execute(text(sql), {"email": email})
    row = result.fetchone()
    
    if not row:
        return None
    
    # Build ServiceArea if area_id exists
    area = None
    if row.area_id:
        area_sql = """
            SELECT area_id, city, district, postal_code
            FROM service_area
            WHERE area_id = :area_id
        """
        area_result = db.execute(text(area_sql), {"area_id": row.area_id})
        area_row = area_result.fetchone()
        if area_row:
            area = models.ServiceArea(
                area_id=area_row.area_id,
                city=area_row.city,
                district=area_row.district,
                postal_code=area_row.postal_code
            )
    
    provider = models.ServiceProvider(
        provider_id=row.provider_id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        phone=row.phone,
        address=row.address,
        area_id=row.area_id,
        hourly_rate=float(row.hourly_rate),
        availability_status=models.AvailabilityStatus(row.availability_status),
        date_joined=row.date_joined,
        password_hash=row.password_hash
    )
    provider.area = area
    
    return provider


def create_customer(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    address: str,
    area_id: Optional[int],
    password: str,
) -> models.Customer:
    """Create a new customer with password"""
    sql = """
        INSERT INTO customer 
        (first_name, last_name, email, phone, address, area_id, password_hash)
        VALUES (:first_name, :last_name, :email, :phone, :address, :area_id, :password_hash)
    """
    
    params = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": address,
        "area_id": area_id,
        "password_hash": hash_password(password)
    }
    
    db.execute(text(sql), params)
    db.commit()
    
    # Get the inserted customer
    result = db.execute(text("SELECT LAST_INSERT_ID() as id"))
    customer_id = result.scalar()
    
    # Fetch the created customer
    return get_customer_by_email(db, email)


def create_provider(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    address: str,
    area_id: Optional[int],
    hourly_rate: float,
    password: str,
) -> models.ServiceProvider:
    """Create a new service provider with password"""
    sql = """
        INSERT INTO service_provider 
        (first_name, last_name, email, phone, address, area_id, hourly_rate, availability_status, password_hash)
        VALUES (:first_name, :last_name, :email, :phone, :address, :area_id, :hourly_rate, 'available', :password_hash)
    """
    
    params = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": address,
        "area_id": area_id,
        "hourly_rate": hourly_rate,
        "password_hash": hash_password(password)
    }
    
    db.execute(text(sql), params)
    db.commit()
    
    # Fetch the created provider
    return get_provider_by_email(db, email)


# -----------------------------
# Request Lifecycle - Helper Functions
# -----------------------------
def _load_customer_by_id(db: Session, customer_id: int) -> Optional[models.Customer]:
    """Load a single customer by ID"""
    sql = """
        SELECT customer_id, first_name, last_name, email, phone, address,
               area_id, registration_date, password_hash
        FROM customer
        WHERE customer_id = :customer_id
    """
    result = db.execute(text(sql), {"customer_id": customer_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    area = _load_area_by_id(db, row.area_id) if row.area_id else None
    
    customer = models.Customer(
        customer_id=row.customer_id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        phone=row.phone,
        address=row.address,
        area_id=row.area_id,
        registration_date=row.registration_date,
        password_hash=row.password_hash
    )
    customer.area = area
    return customer


def _load_customers_by_ids(db: Session, customer_ids: List[int]) -> Dict[int, models.Customer]:
    """Batch load customers by IDs"""
    if not customer_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(customer_ids))])
    sql = f"""
        SELECT customer_id, first_name, last_name, email, phone, address,
               area_id, registration_date, password_hash
        FROM customer
        WHERE customer_id IN ({placeholders})
    """
    params = {f"id{i}": customer_ids[i] for i in range(len(customer_ids))}
    result = db.execute(text(sql), params)
    
    customers = {}
    area_ids = []
    for row in result.fetchall():
        customer = models.Customer(
            customer_id=row.customer_id,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            phone=row.phone,
            address=row.address,
            area_id=row.area_id,
            registration_date=row.registration_date,
            password_hash=row.password_hash
        )
        customers[row.customer_id] = customer
        if row.area_id:
            area_ids.append(row.area_id)
    
    # Load areas in batch
    if area_ids:
        areas = _load_areas_by_ids(db, list(set(area_ids)))
        for customer in customers.values():
            if customer.area_id:
                customer.area = areas.get(customer.area_id)
    
    return customers


def _load_provider_by_id(db: Session, provider_id: int) -> Optional[models.ServiceProvider]:
    """Load a single provider by ID"""
    sql = """
        SELECT provider_id, first_name, last_name, email, phone, address,
               area_id, hourly_rate, availability_status, date_joined, password_hash
        FROM service_provider
        WHERE provider_id = :provider_id
    """
    result = db.execute(text(sql), {"provider_id": provider_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    area = _load_area_by_id(db, row.area_id) if row.area_id else None
    
    provider = models.ServiceProvider(
        provider_id=row.provider_id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        phone=row.phone,
        address=row.address,
        area_id=row.area_id,
        hourly_rate=float(row.hourly_rate),
        availability_status=models.AvailabilityStatus(row.availability_status),
        date_joined=row.date_joined,
        password_hash=row.password_hash
    )
    provider.area = area
    return provider


def _load_providers_by_ids(db: Session, provider_ids: List[int]) -> Dict[int, models.ServiceProvider]:
    """Batch load providers by IDs"""
    if not provider_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(provider_ids))])
    sql = f"""
        SELECT provider_id, first_name, last_name, email, phone, address,
               area_id, hourly_rate, availability_status, date_joined, password_hash
        FROM service_provider
        WHERE provider_id IN ({placeholders})
    """
    params = {f"id{i}": provider_ids[i] for i in range(len(provider_ids))}
    result = db.execute(text(sql), params)
    
    providers = {}
    area_ids = []
    for row in result.fetchall():
        provider = models.ServiceProvider(
            provider_id=row.provider_id,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            phone=row.phone,
            address=row.address,
            area_id=row.area_id,
            hourly_rate=float(row.hourly_rate),
            availability_status=models.AvailabilityStatus(row.availability_status),
            date_joined=row.date_joined,
            password_hash=row.password_hash
        )
        providers[row.provider_id] = provider
        if row.area_id:
            area_ids.append(row.area_id)
    
    # Load areas in batch
    if area_ids:
        areas = _load_areas_by_ids(db, list(set(area_ids)))
        for provider in providers.values():
            if provider.area_id:
                provider.area = areas.get(provider.area_id)
    
    return providers


def _load_category_by_id(db: Session, category_id: int) -> Optional[models.ServiceCategory]:
    """Load a single category by ID"""
    sql = """
        SELECT category_id, name, description
        FROM service_category
        WHERE category_id = :category_id
    """
    result = db.execute(text(sql), {"category_id": category_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    return models.ServiceCategory(
        category_id=row.category_id,
        name=row.name,
        description=row.description
    )


def _load_categories_by_ids(db: Session, category_ids: List[int]) -> Dict[int, models.ServiceCategory]:
    """Batch load categories by IDs"""
    if not category_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(category_ids))])
    sql = f"""
        SELECT category_id, name, description
        FROM service_category
        WHERE category_id IN ({placeholders})
    """
    params = {f"id{i}": category_ids[i] for i in range(len(category_ids))}
    result = db.execute(text(sql), params)
    
    categories = {}
    for row in result.fetchall():
        categories[row.category_id] = models.ServiceCategory(
            category_id=row.category_id,
            name=row.name,
            description=row.description
        )
    
    return categories


def _load_area_by_id(db: Session, area_id: int) -> Optional[models.ServiceArea]:
    """Load a single area by ID"""
    sql = """
        SELECT area_id, city, district, postal_code
        FROM service_area
        WHERE area_id = :area_id
    """
    result = db.execute(text(sql), {"area_id": area_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    return models.ServiceArea(
        area_id=row.area_id,
        city=row.city,
        district=row.district,
        postal_code=row.postal_code
    )


def _load_areas_by_ids(db: Session, area_ids: List[int]) -> Dict[int, models.ServiceArea]:
    """Batch load areas by IDs"""
    if not area_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(area_ids))])
    sql = f"""
        SELECT area_id, city, district, postal_code
        FROM service_area
        WHERE area_id IN ({placeholders})
    """
    params = {f"id{i}": area_ids[i] for i in range(len(area_ids))}
    result = db.execute(text(sql), params)
    
    areas = {}
    for row in result.fetchall():
        areas[row.area_id] = models.ServiceArea(
            area_id=row.area_id,
            city=row.city,
            district=row.district,
            postal_code=row.postal_code
        )
    
    return areas


def _load_payment_by_request_id(db: Session, request_id: int) -> Optional[models.Payment]:
    """Load payment by request_id"""
    sql = """
        SELECT payment_id, request_id, amount, payment_method, payment_date, payment_status
        FROM payment
        WHERE request_id = :request_id
    """
    result = db.execute(text(sql), {"request_id": request_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    return models.Payment(
        payment_id=row.payment_id,
        request_id=row.request_id,
        amount=float(row.amount),
        payment_method=models.PaymentMethod(row.payment_method),
        payment_date=row.payment_date,
        payment_status=models.PaymentStatus(row.payment_status)
    )


def _load_payments_by_request_ids(db: Session, request_ids: List[int]) -> Dict[int, models.Payment]:
    """Batch load payments by request_ids"""
    if not request_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(request_ids))])
    sql = f"""
        SELECT payment_id, request_id, amount, payment_method, payment_date, payment_status
        FROM payment
        WHERE request_id IN ({placeholders})
    """
    params = {f"id{i}": request_ids[i] for i in range(len(request_ids))}
    result = db.execute(text(sql), params)
    
    payments = {}
    for row in result.fetchall():
        payments[row.request_id] = models.Payment(
            payment_id=row.payment_id,
            request_id=row.request_id,
            amount=float(row.amount),
            payment_method=models.PaymentMethod(row.payment_method),
            payment_date=row.payment_date,
            payment_status=models.PaymentStatus(row.payment_status)
        )
    
    return payments


def _load_review_by_request_id(db: Session, request_id: int) -> Optional[models.Review]:
    """Load review by request_id"""
    sql = """
        SELECT review_id, request_id, customer_id, provider_id, rating, comment, created_at
        FROM review
        WHERE request_id = :request_id
    """
    result = db.execute(text(sql), {"request_id": request_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    return models.Review(
        review_id=row.review_id,
        request_id=row.request_id,
        customer_id=row.customer_id,
        provider_id=row.provider_id,
        rating=row.rating,
        comment=row.comment,
        created_at=row.created_at
    )


def _load_reviews_by_request_ids(db: Session, request_ids: List[int]) -> Dict[int, models.Review]:
    """Batch load reviews by request_ids"""
    if not request_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ",".join([":id" + str(i) for i in range(len(request_ids))])
    sql = f"""
        SELECT review_id, request_id, customer_id, provider_id, rating, comment, created_at
        FROM review
        WHERE request_id IN ({placeholders})
    """
    params = {f"id{i}": request_ids[i] for i in range(len(request_ids))}
    result = db.execute(text(sql), params)
    
    reviews = {}
    for row in result.fetchall():
        reviews[row.request_id] = models.Review(
            review_id=row.review_id,
            request_id=row.request_id,
            customer_id=row.customer_id,
            provider_id=row.provider_id,
            rating=row.rating,
            comment=row.comment,
            created_at=row.created_at
        )
    
    return reviews


def get_service_request_by_id(db: Session, request_id: int) -> Optional[models.ServiceRequest]:
    """Get a service request by ID with all relationships loaded"""
    # Fetch main request
    sql = """
        SELECT request_id, customer_id, provider_id, category_id, area_id,
               address, description, status, cost, request_date, cancellation_date
        FROM service_request
        WHERE request_id = :request_id
    """
    result = db.execute(text(sql), {"request_id": request_id})
    row = result.fetchone()
    
    if not row:
        return None
    
    # Load related entities
    customer = _load_customer_by_id(db, row.customer_id) if row.customer_id else None
    provider = _load_provider_by_id(db, row.provider_id) if row.provider_id else None
    category = _load_category_by_id(db, row.category_id) if row.category_id else None
    area = _load_area_by_id(db, row.area_id) if row.area_id else None
    payment = _load_payment_by_request_id(db, request_id)
    review = _load_review_by_request_id(db, request_id)
    
    # Build request object
    request = models.ServiceRequest(
        request_id=row.request_id,
        customer_id=row.customer_id,
        provider_id=row.provider_id,
        category_id=row.category_id,
        area_id=row.area_id,
        address=row.address,
        description=row.description,
        status=models.RequestStatus(row.status),
        cost=float(row.cost) if row.cost else None,
        request_date=row.request_date,
        cancellation_date=row.cancellation_date
    )
    
    # Attach relationships
    request.customer = customer
    request.provider = provider
    request.category = category
    request.area = area
    request.payment = payment
    request.review = review
    
    return request


def provider_accept_request(db: Session, request_id: int, provider_id: int) -> models.ServiceRequest:
    """
    Provider accepts a pending request.
    Business rules:
    - Request must be in 'pending' status
    - Provider must be the one assigned to the request
    """
    request = get_service_request_by_id(db, request_id)
    
    if not request:
        raise ValueError(f"Request {request_id} not found")
    
    if request.provider_id != provider_id:
        raise ValueError("You are not authorized to accept this request")
    
    if request.status != models.RequestStatus.pending:
        raise ValueError(f"Cannot accept request with status '{request.status.value}'. Must be 'pending'.")
    
    sql = """
        UPDATE service_request 
        SET status = 'in_progress'
        WHERE request_id = :request_id
    """
    
    db.execute(text(sql), {"request_id": request_id})
    db.commit()
    
    return get_service_request_by_id(db, request_id)


def provider_complete_request(db: Session, request_id: int, provider_id: int) -> models.ServiceRequest:
    """
    Provider marks an in-progress request as completed.
    Business rules:
    - Request must be in 'in_progress' status
    - Provider must be the one assigned to the request
    """
    request = get_service_request_by_id(db, request_id)
    
    if not request:
        raise ValueError(f"Request {request_id} not found")
    
    if request.provider_id != provider_id:
        raise ValueError("You are not authorized to complete this request")
    
    if request.status != models.RequestStatus.in_progress:
        raise ValueError(f"Cannot complete request with status '{request.status.value}'. Must be 'in_progress'.")
    
    sql = """
        UPDATE service_request 
        SET status = 'completed'
        WHERE request_id = :request_id
    """
    
    db.execute(text(sql), {"request_id": request_id})
    db.commit()
    
    return get_service_request_by_id(db, request_id)


def customer_pay_request(
    db: Session,
    request_id: int,
    customer_id: int,
    payment_method: str,
    amount: Optional[float] = None
) -> models.Payment:
    """
    Customer pays for a completed request.
    Business rules:
    - Request must be 'completed'
    - Customer must own the request
    - Request must not already have a paid payment
    - Payment amount must equal request.cost (quoted_price)
    """
    request = get_service_request_by_id(db, request_id)
    
    if not request:
        raise ValueError(f"Request {request_id} not found")
    
    if request.customer_id != customer_id:
        raise ValueError("You are not authorized to pay for this request")
    
    if request.status != models.RequestStatus.completed:
        raise ValueError(f"Cannot pay for request with status '{request.status.value}'. Must be 'completed'.")
    
    # Check if payment already exists and is completed
    if request.payment and request.payment.payment_status == models.PaymentStatus.completed:
        raise ValueError("This request has already been paid")
    
    # Use request.cost as the quoted price
    if request.cost is None:
        raise ValueError("Request does not have a cost/quoted price set")
    
    payment_amount = amount if amount is not None else float(request.cost)
    
    # Validate amount matches quoted price
    if abs(payment_amount - float(request.cost)) > 0.01:  # Allow small float difference
        raise ValueError(f"Payment amount ${payment_amount:.2f} must equal quoted price ${request.cost:.2f}")
    
    # Create or update payment
    if request.payment:
        # Update existing payment
        sql = """
            UPDATE payment 
            SET amount = :amount,
                payment_method = :payment_method,
                payment_status = 'completed',
                payment_date = NOW()
            WHERE request_id = :request_id
        """
        params = {
            "request_id": request_id,
            "amount": payment_amount,
            "payment_method": payment_method
        }
        db.execute(text(sql), params)
    else:
        # Create new payment
        sql = """
            INSERT INTO payment 
            (request_id, amount, payment_method, payment_status, payment_date)
            VALUES (:request_id, :amount, :payment_method, 'completed', NOW())
        """
        params = {
            "request_id": request_id,
            "amount": payment_amount,
            "payment_method": payment_method
        }
        db.execute(text(sql), params)
    
    db.commit()
    
    # Fetch the payment
    sql = """
        SELECT payment_id, request_id, amount, payment_method, payment_date, payment_status
        FROM payment
        WHERE request_id = :request_id
    """
    result = db.execute(text(sql), {"request_id": request_id})
    row = result.fetchone()
    
    payment = models.Payment(
        payment_id=row.payment_id,
        request_id=row.request_id,
        amount=float(row.amount),
        payment_method=models.PaymentMethod(row.payment_method),
        payment_date=row.payment_date,
        payment_status=models.PaymentStatus(row.payment_status)
    )
    
    return payment


def customer_add_review(
    db: Session,
    request_id: int,
    customer_id: int,
    rating: int,
    comment: Optional[str] = None
) -> models.Review:
    """
    Customer adds a review for a completed and paid request.
    Business rules:
    - Request must be 'completed'
    - Request must have a payment with status 'completed'
    - Customer must own the request
    - Rating must be 1-5
    - Cannot review twice (enforced by DB unique constraint)
    """
    request = get_service_request_by_id(db, request_id)
    
    if not request:
        raise ValueError(f"Request {request_id} not found")
    
    if request.customer_id != customer_id:
        raise ValueError("You are not authorized to review this request")
    
    if request.status != models.RequestStatus.completed:
        raise ValueError(f"Cannot review request with status '{request.status.value}'. Must be 'completed'.")
    
    # Check payment exists and is completed
    if not request.payment:
        raise ValueError("Cannot review: request has not been paid")
    
    if request.payment.payment_status != models.PaymentStatus.completed:
        raise ValueError(f"Cannot review: payment status is '{request.payment.payment_status.value}'. Must be 'completed'.")
    
    # Check if review already exists
    if request.review:
        raise ValueError("A review already exists for this request")
    
    # Validate rating
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5")
    
    # Create review
    sql = """
        INSERT INTO review 
        (request_id, customer_id, provider_id, rating, comment)
        VALUES (:request_id, :customer_id, :provider_id, :rating, :comment)
    """
    
    params = {
        "request_id": request_id,
        "customer_id": customer_id,
        "provider_id": request.provider_id,
        "rating": rating,
        "comment": comment
    }
    
    db.execute(text(sql), params)
    db.commit()
    
    # Fetch the created review
    sql = """
        SELECT review_id, request_id, customer_id, provider_id, rating, comment, created_at
        FROM review
        WHERE request_id = :request_id
    """
    result = db.execute(text(sql), {"request_id": request_id})
    row = result.fetchone()
    
    review = models.Review(
        review_id=row.review_id,
        request_id=row.request_id,
        customer_id=row.customer_id,
        provider_id=row.provider_id,
        rating=row.rating,
        comment=row.comment,
        created_at=row.created_at
    )
    
    return review