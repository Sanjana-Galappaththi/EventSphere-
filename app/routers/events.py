from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import uuid

from app.database import get_db
from app.models.venue import Venue
from app.models.event import Event, TicketCategory
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse
from app.core.deps import require_role
from app.agents.bus import bus

router = APIRouter()

@router.post("/", response_model=EventResponse)
def create_event(
    event_in: EventCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    # 1. Check if venue exists
    venue = db.query(Venue).filter(Venue.id == event_in.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # 2. Check if tickets exceed venue capacity
    total_tickets = sum(tc.quantity for tc in event_in.ticket_categories)
    if total_tickets > venue.capacity:
        raise HTTPException(status_code=400, detail=f"Total tickets ({total_tickets}) exceed venue capacity ({venue.capacity})")

    # 3. Ask the VenueAgent if the time slot is free
    conversation_id = str(uuid.uuid4())
    agent_response = bus.send_message(
        db=db,
        sender="EventRouter",
        receiver="VenueAgent",
        performative="REQUEST",
        content={
            "action": "check_availability",
            "venue_id": venue.id,
            "start_time": event_in.start_time.isoformat(),
            "end_time": event_in.end_time.isoformat()
        },
        conversation_id=conversation_id
    )

    if agent_response.get("status") != "AGREE":
        raise HTTPException(status_code=400, detail=f"VenueAgent refused: {agent_response.get('reason')}")

    # 4. If agent agrees, save the event
    new_event = Event(
        title=event_in.title,
        category=event_in.category,
        venue_id=event_in.venue_id,
        start_time=event_in.start_time,
        end_time=event_in.end_time,
        description=event_in.description,
        status="draft"
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # 5. Add ticket categories
    for tc in event_in.ticket_categories:
        new_tc = TicketCategory(
            event_id=new_event.id,
            name=tc.name,
            price=tc.price,
            quantity=tc.quantity,
            remaining=tc.quantity
        )
        db.add(new_tc)
    
    db.commit()
    db.refresh(new_event)
    
    # 6. Notify NotificationAgent that event was created
    bus.send_message(
        db=db, sender="EventRouter", receiver="NotificationAgent", 
        performative="INFORM", content={"message": f"New event created: {new_event.title}"},
        conversation_id=conversation_id
    )

    return new_event

@router.get("/", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).all()