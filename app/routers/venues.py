from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.venue import Venue
from app.models.user import User
from app.schemas.venue import VenueCreate, VenueResponse
from app.core.deps import require_role

router = APIRouter()

@router.post("/", response_model=VenueResponse)
def create_venue(
    venue: VenueCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    new_venue = Venue(**venue.dict())
    db.add(new_venue)
    db.commit()
    db.refresh(new_venue)
    return new_venue

@router.get("/", response_model=List[VenueResponse])
def list_venues(db: Session = Depends(get_db)):
    return db.query(Venue).all()