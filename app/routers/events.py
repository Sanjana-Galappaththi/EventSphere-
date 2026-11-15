from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.venue import Venue
from app.models.event import Event, TicketCategory
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse
from app.core.deps import require_role
from app.agents.bus import bus

# Force the VenueAgent to register with the bus
from app.agents.venue_agent import venue_agent

router = APIRouter()

@router.post("/", response_model=EventResponse)
def create_event(
    event_in: EventCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    venue = db.query(Venue).filter(Venue.id == event_in.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    total_tickets = sum(tc.quantity for tc in event_in.ticket_categories)
    if total_tickets > venue.capacity:
        raise HTTPException(status_code=400, detail=f"Total tickets ({total_tickets}) exceed venue capacity ({venue.capacity})")

    conversation_id = str(uuid.uuid4())
    
    # Ask VenueAgent
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

    if agent_response is None:
        raise HTTPException(status_code=500, detail="VenueAgent failed to respond. Check server logs.")

    if agent_response.get("status") != "AGREE":
        raise HTTPException(status_code=400, detail=f"VenueAgent refused: {agent_response.get('reason')}")

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
    
    # Notify NotificationAgent
    bus.send_message(
        db=db, sender="EventRouter", receiver="NotificationAgent", 
        performative="INFORM", content={"message": f"New event created: {new_event.title}"},
        conversation_id=conversation_id
    )

    return new_event

@router.get("/", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).all()