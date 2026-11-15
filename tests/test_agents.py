import app.agents  # <--- Ensure agents are loaded
import uuid
from datetime import datetime, timedelta
from app.agents.bus import bus
from app.models.event import Event
from app.models.venue import Venue

def test_venue_agent_clash(db_session):
    venue = Venue(name="V", location="L", capacity=10, hourly_rate=10.0)
    db_session.add(venue)
    db_session.commit()
    
    start = datetime(2026, 1, 1, 10, 0)
    end = datetime(2026, 1, 1, 12, 0)
    
    event = Event(title="E", category="C", venue_id=venue.id, start_time=start, end_time=end, status="published")
    db_session.add(event)
    db_session.commit()

    res = bus.send_message(
        db=db_session, sender="Test", receiver="VenueAgent", performative="REQUEST",
        content={"action": "check_availability", "venue_id": venue.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
        conversation_id=str(uuid.uuid4())
    )
    assert res is not None
    assert res["status"] == "REFUSE"
    assert "Clashes with event" in res["reason"]

def test_venue_agent_hire_counter_proposal(db_session):
    venue = Venue(name="V2", location="L", capacity=10, hourly_rate=10.0)
    db_session.add(venue)
    db_session.commit()
    
    start = datetime(2026, 1, 1, 10, 0)
    end = datetime(2026, 1, 1, 12, 0)
    event = Event(title="E", category="C", venue_id=venue.id, start_time=start, end_time=end, status="published")
    db_session.add(event)
    db_session.commit()

    res = bus.send_message(
        db=db_session, sender="Test", receiver="VenueAgent", performative="REQUEST",
        content={"action": "request_hire", "venue_id": venue.id, "start_time": start.isoformat(), "end_time": end.isoformat(), "guest_count": 5},
        conversation_id=str(uuid.uuid4())
    )
    assert res is not None
    assert res["status"] == "PROPOSE"
    assert "alternatives" in res

def test_notification_agent(db_session):
    res = bus.send_message(
        db=db_session, sender="Test", receiver="NotificationAgent", performative="INFORM",
        content={"message": "Hello"},
        conversation_id=str(uuid.uuid4())
    )
    assert res is not None
    assert res["status"] == "AGREE"