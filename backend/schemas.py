from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

try:
    from .models import AvailabilityStatus, RequestStatus, PaymentMethod, PaymentStatus
except ImportError:
    from models import AvailabilityStatus, RequestStatus, PaymentMethod, PaymentStatus


# ========== SERVICE AREA SCHEMAS ==========
class ServiceAreaBase(BaseModel):
    city: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)


class ServiceAreaCreate(ServiceAreaBase):
    pass


class ServiceArea(ServiceAreaBase):
    area_id: int
    city: str
    district: str
    postal_code: str

    class Config:
        from_attributes = True


# ========== SERVICE CATEGORY SCHEMAS ==========
class ServiceCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategory(ServiceCategoryBase):
    category_id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ========== CUSTOMER SCHEMAS ==========
class CustomerBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr
    phone: str = Field(..., max_length=30)
    address: str = Field(..., max_length=255)
    area_id: Optional[int] = None


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    customer_id: int
    registration_date: datetime
    area_id: Optional[int]

    class Config:
        from_attributes = True


# ========== SERVICE PROVIDER SCHEMAS ==========
class ServiceProviderBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr
    phone: str = Field(..., max_length=30)
    address: str = Field(..., max_length=255)
    area_id: Optional[int] = None
    hourly_rate: Decimal = Field(..., ge=0)
    availability_status: AvailabilityStatus = AvailabilityStatus.available


class ServiceProviderCreate(ServiceProviderBase):
    category_ids: Optional[List[int]] = []


class ServiceProvider(ServiceProviderBase):
    provider_id: int
    date_joined: datetime
    area_id: Optional[int]

    class Config:
        from_attributes = True


class ServiceProviderWithCategories(ServiceProvider):
    categories: List[ServiceCategory] = []


# ========== SERVICE REQUEST SCHEMAS ==========
class ServiceRequestBase(BaseModel):
    customer_id: int
    provider_id: Optional[int] = None
    category_id: int
    area_id: int
    address: str = Field(..., max_length=255)
    description: Optional[str] = None
    cost: Optional[Decimal] = Field(None, ge=0)


class ServiceRequestCreate(ServiceRequestBase):
    pass


class ServiceRequest(ServiceRequestBase):
    request_id: int
    status: RequestStatus
    request_date: datetime
    cancellation_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServiceRequestUpdateStatus(BaseModel):
    status: RequestStatus
    cancellation_date: Optional[datetime] = None


class ServiceRequestWithRelations(ServiceRequest):
    customer: Optional[Customer] = None
    provider: Optional[ServiceProvider] = None
    category: Optional[ServiceCategory] = None
    area: Optional[ServiceArea] = None


# ========== PAYMENT SCHEMAS ==========
class PaymentBase(BaseModel):
    request_id: int
    amount: Decimal = Field(..., ge=0)
    payment_method: PaymentMethod
    payment_status: PaymentStatus = PaymentStatus.pending


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, ge=0)
    payment_method: Optional[PaymentMethod] = None
    payment_status: Optional[PaymentStatus] = None


class Payment(PaymentBase):
    payment_id: int
    payment_date: datetime

    class Config:
        from_attributes = True


class PaymentWithRequest(Payment):
    service_request: Optional[ServiceRequest] = None


# ========== REVIEW SCHEMAS ==========
class ReviewBase(BaseModel):
    request_id: int
    customer_id: int
    provider_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class Review(ReviewBase):
    review_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewWithRelations(Review):
    customer: Optional[Customer] = None
    provider: Optional[ServiceProvider] = None
    service_request: Optional[ServiceRequest] = None

