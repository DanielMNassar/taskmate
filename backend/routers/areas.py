from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    from ..db import get_db
    from ..schemas import ServiceArea, ServiceAreaCreate
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import ServiceArea, ServiceAreaCreate
    import crud

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=List[ServiceArea])
def read_areas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all service areas"""
    areas = crud.get_areas(db, skip=skip, limit=limit)
    return areas


@router.get("/{area_id}", response_model=ServiceArea)
def read_area(area_id: int, db: Session = Depends(get_db)):
    """Get a specific service area by ID"""
    area = crud.get_area(db, area_id=area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Service area not found")
    return area


@router.post("", response_model=ServiceArea, status_code=201)
def create_area(area: ServiceAreaCreate, db: Session = Depends(get_db)):
    """Create a new service area"""
    return crud.create_area(db=db, area=area)

