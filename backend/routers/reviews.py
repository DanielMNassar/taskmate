from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    from ..db import get_db
    from ..schemas import Review, ReviewCreate
    from ..models import Review as ReviewModel
    from .. import crud
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db
    from schemas import Review, ReviewCreate
    from models import Review as ReviewModel
    import crud

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=List[Review])
def read_reviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all reviews"""
    reviews = crud.get_reviews(db, skip=skip, limit=limit)
    return reviews


@router.get("/{review_id}", response_model=Review)
def read_review(review_id: int, db: Session = Depends(get_db)):
    """Get a specific review by ID"""
    review = crud.get_review(db, review_id=review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("", response_model=Review, status_code=201)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    """Create a new review"""
    try:
        return crud.create_review(db=db, review=review)
    except ValueError as e:
        # Check if it's a duplicate review error (409 Conflict)
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

