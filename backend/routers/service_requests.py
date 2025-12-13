from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

try:
    from ..db import get_db
    from ..schemas import ServiceRequest, ServiceRequestCreate, ServiceRequestUpdateStatus
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import ServiceRequest, ServiceRequestCreate, ServiceRequestUpdateStatus
    import crud

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("", response_model=List[ServiceRequest])
def read_service_requests(
    customer_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all service requests, optionally filtered by customer_id and/or provider_id"""
    requests = crud.get_service_requests(
        db, customer_id=customer_id, provider_id=provider_id, skip=skip, limit=limit
    )
    return requests


@router.get("/{request_id}", response_model=ServiceRequest)
def read_service_request(request_id: int, db: Session = Depends(get_db)):
    """Get a specific service request by ID"""
    request = crud.get_service_request(db, request_id=request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Service request not found")
    return request


@router.post("", response_model=ServiceRequest, status_code=201)
def create_service_request(request: ServiceRequestCreate, db: Session = Depends(get_db)):
    """Create a new service request"""
    return crud.create_service_request(db=db, request=request)


@router.patch("/{request_id}/status", response_model=ServiceRequest)
def update_service_request_status(
    request_id: int,
    status_update: ServiceRequestUpdateStatus,
    db: Session = Depends(get_db)
):
    """Update the status of a service request"""
    request = crud.update_service_request_status(db, request_id=request_id, status_update=status_update)
    if request is None:
        raise HTTPException(status_code=404, detail="Service request not found")
    return request

