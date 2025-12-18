"""
Request Lifecycle API Endpoints
Handles provider accept/complete and customer pay/review actions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from backend.db import get_db
from backend import crud, models

router = APIRouter(prefix="/api", tags=["lifecycle"])


# -----------------------------
# Pydantic Models
# -----------------------------
class AcceptRequestResponse(BaseModel):
    request_id: int
    status: str
    message: str

    class Config:
        from_attributes = True


class CompleteRequestResponse(BaseModel):
    request_id: int
    status: str
    message: str

    class Config:
        from_attributes = True


class PaymentRequest(BaseModel):
    payment_method: str = Field(..., description="Payment method: credit_card, debit_card, cash, paypal, bank_transfer")
    amount: Optional[float] = Field(None, description="Payment amount (must match quoted price)")

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    payment_id: int
    request_id: int
    amount: float
    payment_method: str
    payment_status: str
    message: str

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, description="Optional review comment")

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    review_id: int
    request_id: int
    rating: int
    comment: Optional[str]
    message: str

    class Config:
        from_attributes = True


# -----------------------------
# Session Helper
# -----------------------------
def get_current_user(request: Request) -> dict:
    """Get current user from session or raise 401"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated. Please login.")
    return user


# -----------------------------
# Provider Endpoints
# -----------------------------
@router.post("/provider/requests/{request_id}/accept", response_model=AcceptRequestResponse)
def provider_accept_request_endpoint(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Provider accepts a pending service request.
    
    Authorization: Must be logged in as provider and assigned to this request.
    Status transition: pending → in_progress
    """
    user = get_current_user(request)
    
    # Verify user is a provider
    if user.get("role") != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can accept requests"
        )
    
    provider_id = user.get("user_id")
    
    try:
        service_request = crud.provider_accept_request(db, request_id, provider_id)
        return AcceptRequestResponse(
            request_id=service_request.request_id,
            status=service_request.status.value,
            message=f"Request #{request_id} accepted successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/provider/requests/{request_id}/complete", response_model=CompleteRequestResponse)
def provider_complete_request_endpoint(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Provider marks an in-progress request as completed.
    
    Authorization: Must be logged in as provider and assigned to this request.
    Status transition: in_progress → completed
    """
    user = get_current_user(request)
    
    # Verify user is a provider
    if user.get("role") != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can complete requests"
        )
    
    provider_id = user.get("user_id")
    
    try:
        service_request = crud.provider_complete_request(db, request_id, provider_id)
        return CompleteRequestResponse(
            request_id=service_request.request_id,
            status=service_request.status.value,
            message=f"Request #{request_id} marked as completed"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# -----------------------------
# Customer Endpoints
# -----------------------------
@router.post("/customer/requests/{request_id}/pay", response_model=PaymentResponse)
def customer_pay_request_endpoint(
    request_id: int,
    payment_data: PaymentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Customer pays for a completed service request.
    
    Authorization: Must be logged in as customer and own this request.
    Requirements:
    - Request must be completed
    - Payment amount must match quoted price (request.cost)
    - Request must not already be paid
    """
    user = get_current_user(request)
    
    # Verify user is a customer
    if user.get("role") != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can pay for requests"
        )
    
    customer_id = user.get("user_id")
    
    try:
        payment = crud.customer_pay_request(
            db,
            request_id=request_id,
            customer_id=customer_id,
            payment_method=payment_data.payment_method,
            amount=payment_data.amount
        )
        return PaymentResponse(
            payment_id=payment.payment_id,
            request_id=payment.request_id,
            amount=float(payment.amount),
            payment_method=payment.payment_method.value,
            payment_status=payment.payment_status.value,
            message=f"Payment of ${payment.amount:.2f} completed successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/customer/requests/{request_id}/review", response_model=ReviewResponse)
def customer_add_review_endpoint(
    request_id: int,
    review_data: ReviewRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Customer adds a review for a completed and paid request.
    
    Authorization: Must be logged in as customer and own this request.
    Requirements:
    - Request must be completed
    - Request must be paid (payment status = completed)
    - Rating must be 1-5
    - Cannot review twice
    """
    user = get_current_user(request)
    
    # Verify user is a customer
    if user.get("role") != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can add reviews"
        )
    
    customer_id = user.get("user_id")
    
    try:
        review = crud.customer_add_review(
            db,
            request_id=request_id,
            customer_id=customer_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        return ReviewResponse(
            review_id=review.review_id,
            request_id=review.request_id,
            rating=review.rating,
            comment=review.comment,
            message=f"Review added successfully with {review.rating} stars"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

