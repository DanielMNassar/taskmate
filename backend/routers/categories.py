from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    from ..db import get_db
    from ..schemas import ServiceCategory, ServiceCategoryCreate
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import ServiceCategory, ServiceCategoryCreate
    import crud

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[ServiceCategory])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all service categories"""
    categories = crud.get_categories(db, skip=skip, limit=limit)
    return categories


@router.get("/{category_id}", response_model=ServiceCategory)
def read_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific service category by ID"""
    category = crud.get_category(db, category_id=category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Service category not found")
    return category


@router.post("", response_model=ServiceCategory, status_code=201)
def create_category(category: ServiceCategoryCreate, db: Session = Depends(get_db)):
    """Create a new service category"""
    return crud.create_category(db=db, category=category)

