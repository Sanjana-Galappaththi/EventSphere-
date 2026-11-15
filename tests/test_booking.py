import app.agents  # <--- Ensure agents are loaded
import uuid
from datetime import datetime, timedelta
from app.agents.bus import bus
from app.models.event import Event, TicketCategory
from app.models.venue import Venue

def test_booking_agent_refuses_over_6_tickets(db_session):
    venue = Venue(name="Test Venue", location="Test", capacity=100, hourly_rate=50.0)
    db_session.add(venue)
    db_session.commit()
    
    event = Event(title="Test Event", category="Test", venue_id=venue.id, start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(hours=2), status="published")
    db_session.add(event)
    db_session.commit()

    category = TicketCategory(event_id=event.id, name="General", price=1000, quantity=100, remaining=100)
    db_session.add(category)
    db_session.commit()

    response = bus.send_message(
        db=db_session, sender="Test", receiver="BookingAgent", performative="REQUEST",
        content={"action": "reserve_tickets", "category_id": category.id, "quantity": 7},
        conversation_id=str(uuid.uuid4())
    )
    assert response is not None
    assert response["status"] == "REFUSE"
    assert "up to 6 tickets" in response["reason"]

def test_booking_agent_prevents_overbooking(db_session):
    venue = Venue(name="Test Venue 2", location="Test", capacity=100, hourly_rate=50.0)
    db_session.add(venue)
    db_session.commit()
    
    event = Event(title="Test Event 2", category="Test", venue_id=venue.id, start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(hours=2), status="published")
    db_session.add(event)
    db_session.commit()

    category = TicketCategory(event_id=event.id, name="General", price=1000, quantity=100, remaining=2)
    db_session.add(category)
    db_session.commit()

    res1 = bus.send_message(
        db=db_session, sender="Test", receiver="BookingAgent", performative="REQUEST",
        content={"action": "reserve_tickets", "category_id": category.id, "quantity": 2},
        conversation_id=str(uuid.uuid4())
    )
    assert res1 is not None
    assert res1["status"] == "AGREE"

    res2 = bus.send_message(
        db=db_session, sender="Test", receiver="BookingAgent", performative="REQUEST",
        content={"action": "reserve_tickets", "category_id": category.id, "quantity": 1},
        conversation_id=str(uuid.uuid4())
    )
    assert res2 is not None
    assert res2["status"] == "REFUSE"
    assert "Only 0 tickets remaining" in res2["reason"]