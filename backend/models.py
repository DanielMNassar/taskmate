from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, ForeignKey, Enum, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

try:
    from .db import Base
except ImportError:
    from db import Base


class AvailabilityStatus(str, enum.Enum):
    available = "available"
    busy = "busy"
    unavailable = "unavailable"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    credit_card = "credit_card"
    debit_card = "debit_card"
    cash = "cash"
    paypal = "paypal"
    bank_transfer = "bank_transfer"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class ServiceArea(Base):
    __tablename__ = "service_area"

    area_id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint('city', 'district', 'postal_code', name='uk_area_location'),
    )

    # Relationships
    customers = relationship("Customer", back_populates="area")
    providers = relationship("ServiceProvider", back_populates="area")
    service_requests = relationship("ServiceRequest", back_populates="area")


class ServiceCategory(Base):
    __tablename__ = "service_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255))

    # Relationships
    providers = relationship("ProviderCategory", back_populates="category", cascade="all, delete-orphan")
    service_requests = relationship("ServiceRequest", back_populates="category")


class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(30), nullable=False)
    address = Column(String(255), nullable=False)
    area_id = Column(Integer, ForeignKey("service_area.area_id", ondelete="SET NULL", onupdate="CASCADE"))
    registration_date = Column(DateTime, server_default=func.now())

    # Relationships
    area = relationship("ServiceArea", back_populates="customers")
    service_requests = relationship("ServiceRequest", back_populates="customer", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="customer", cascade="all, delete-orphan")


class ServiceProvider(Base):
    __tablename__ = "service_provider"

    provider_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(30), nullable=False)
    address = Column(String(255), nullable=False)
    area_id = Column(Integer, ForeignKey("service_area.area_id", ondelete="SET NULL", onupdate="CASCADE"))
    hourly_rate = Column(DECIMAL(10, 2), nullable=False)
    availability_status = Column(Enum(AvailabilityStatus), default=AvailabilityStatus.available)
    date_joined = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint('hourly_rate >= 0', name='check_hourly_rate'),
    )

    # Relationships
    area = relationship("ServiceArea", back_populates="providers")
    categories = relationship("ProviderCategory", back_populates="provider", cascade="all, delete-orphan")
    service_requests = relationship("ServiceRequest", back_populates="provider")
    reviews = relationship("Review", back_populates="provider", cascade="all, delete-orphan")


class ProviderCategory(Base):
    __tablename__ = "provider_category"

    provider_id = Column(Integer, ForeignKey("service_provider.provider_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    category_id = Column(Integer, ForeignKey("service_category.category_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

    # Relationships
    provider = relationship("ServiceProvider", back_populates="categories")
    category = relationship("ServiceCategory", back_populates="providers")


class ServiceRequest(Base):
    __tablename__ = "service_request"

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("service_provider.provider_id", ondelete="SET NULL", onupdate="CASCADE"))
    category_id = Column(Integer, ForeignKey("service_category.category_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    area_id = Column(Integer, ForeignKey("service_area.area_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    address = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    cost = Column(DECIMAL(10, 2))
    request_date = Column(DateTime, server_default=func.now())
    cancellation_date = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint('cost >= 0', name='check_cost'),
    )

    # Relationships
    customer = relationship("Customer", back_populates="service_requests")
    provider = relationship("ServiceProvider", back_populates="service_requests")
    category = relationship("ServiceCategory", back_populates="service_requests")
    area = relationship("ServiceArea", back_populates="service_requests")
    payment = relationship("Payment", back_populates="service_request", uselist=False, cascade="all, delete-orphan")
    review = relationship("Review", back_populates="service_request", uselist=False, cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payment"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("service_request.request_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, unique=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_date = Column(DateTime, server_default=func.now())
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)

    __table_args__ = (
        CheckConstraint('amount >= 0', name='check_amount'),
    )

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="payment")


class Review(Base):
    __tablename__ = "review"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("service_request.request_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("service_provider.provider_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating'),
        UniqueConstraint('request_id', name='uk_review_request'),
    )

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="review")
    customer = relationship("Customer", back_populates="reviews")
    provider = relationship("ServiceProvider", back_populates="reviews")

