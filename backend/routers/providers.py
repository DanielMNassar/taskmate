from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

try:
    from ..db import get_db
    from ..schemas import ServiceProvider, ServiceProviderCreate, ServiceProviderWithCategories, Review
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import ServiceProvider, ServiceProviderCreate, ServiceProviderWithCategories, Review
    import crud

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=List[ServiceProvider])
def read_providers(
    area_id: Optional[int] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all providers, optionally filtered by area_id and/or category_id"""
    if area_id or category_id:
        providers = crud.get_providers_by_area_category(
            db, area_id=area_id, category_id=category_id
        )
    else:
        providers = crud.get_providers(db, skip=skip, limit=limit)
    return providers


@router.get("/{provider_id}", response_model=ServiceProvider)
def read_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get a specific provider by ID"""
    provider = crud.get_provider(db, provider_id=provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Service provider not found")
    return provider


@router.post("", response_model=ServiceProvider, status_code=201)
def create_provider(provider: ServiceProviderCreate, db: Session = Depends(get_db)):
    """Create a new service provider"""
    try:
        return crud.create_provider(db=db, provider=provider)
    except ValueError as e:
        # Check if it's a duplicate email error (409 Conflict)
        if "already registered" in str(e).lower() or "email" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError as e:
        # Fallback for direct IntegrityError
        if "email" in str(e).lower() or "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail=f"Email {provider.email} is already registered")
        raise HTTPException(status_code=400, detail="Database constraint violation")


@router.get("/{provider_id}/reviews", response_model=List[Review])
def get_provider_reviews(
    provider_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all reviews for a specific provider"""
    from schemas import Review
    reviews = crud.get_reviews_for_provider(db, provider_id=provider_id, skip=skip, limit=limit)
    return reviews

