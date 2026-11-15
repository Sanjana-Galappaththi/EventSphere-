import app.agents  # <--- Ensure agents are loaded
import uuid
from datetime import datetime, timedelta
from app.agents.bus import bus
from app.models.ticket import Ticket
from app.models.booking import Booking
from app.models.event import Event, TicketCategory
from app.models.venue import Venue
from app.models.user import User

def test_ticket_agent_double_checkin(db_session):
    user = User(email="test@test.com", hashed_password="pw", full_name="Test", role="attendee")
    venue = Venue(name="V", location="L", capacity=10, hourly_rate=10.0)
    db_session.add_all([user, venue])
    db_session.commit()
    
    event = Event(title="E", category="C", venue_id=venue.id, start_time=datetime.utcnow(), end_time=datetime.utcnow(), status="published")
    db_session.add(event)
    db_session.commit()
    
    category = TicketCategory(event_id=event.id, name="G", price=10, quantity=10, remaining=10)
    db_session.add(category)
    db_session.commit()
    
    booking = Booking(user_id=user.id, ticket_category_id=category.id, quantity=1, total_price=10, status="confirmed")
    db_session.add(booking)
    db_session.commit()
    
    ticket = Ticket(booking_id=booking.id, qr_code="QR123", is_admitted=False)
    db_session.add(ticket)
    db_session.commit()

    res1 = bus.send_message(
        db=db_session, sender="Scanner", receiver="TicketAgent", performative="REQUEST",
        content={"action": "scan_ticket", "qr_code": "QR123", "event_id": event.id},
        conversation_id=str(uuid.uuid4())
    )
    assert res1 is not None
    assert res1["status"] == "AGREE"

    res2 = bus.send_message(
        db=db_session, sender="Scanner", receiver="TicketAgent", performative="REQUEST",
        content={"action": "scan_ticket", "qr_code": "QR123", "event_id": event.id},
        conversation_id=str(uuid.uuid4())
    )
    assert res2 is not None
    assert res2["status"] == "REFUSE"
    assert "already used" in res2["reason"]