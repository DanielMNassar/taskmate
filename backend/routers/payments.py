from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

try:
    from ..db import get_db
    from ..schemas import Payment, PaymentCreate, PaymentUpdate
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import Payment, PaymentCreate, PaymentUpdate
    import crud

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=List[Payment])
def read_payments(
    request_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all payments, optionally filtered by request_id"""
    payments = crud.get_payments(db, request_id=request_id, skip=skip, limit=limit)
    return payments


@router.get("/{payment_id}", response_model=Payment)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get a specific payment by ID"""
    payment = crud.get_payment(db, payment_id=payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("", response_model=Payment, status_code=201)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """Create a new payment or update existing one (upsert behavior matching old Tkinter app)"""
    return crud.create_payment(db=db, payment=payment)


@router.put("/request/{request_id}", response_model=Payment)
def update_payment_by_request(request_id: int, payment_update: PaymentUpdate, db: Session = Depends(get_db)):
    """Update payment by request_id"""
    payment = crud.update_payment(db, request_id=request_id, payment_update=payment_update)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found for this request")
    return payment

