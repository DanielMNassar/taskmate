from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

try:
    from ..db import get_db
    from ..schemas import Customer, CustomerCreate
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import Customer, CustomerCreate
    import crud

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=List[Customer])
def read_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all customers"""
    customers = crud.get_customers(db, skip=skip, limit=limit)
    return customers


@router.get("/{customer_id}", response_model=Customer)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a specific customer by ID"""
    customer = crud.get_customer(db, customer_id=customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("", response_model=Customer, status_code=201)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    try:
        return crud.create_customer(db=db, customer=customer)
    except ValueError as e:
        # Check if it's a duplicate email error (409 Conflict)
        if "already registered" in str(e).lower() or "email" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError as e:
        # Fallback for direct IntegrityError
        if "email" in str(e).lower() or "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail=f"Email {customer.email} is already registered")
        raise HTTPException(status_code=400, detail="Database constraint violation")

