import os
import pytest
from datetime import datetime, timedelta
import secrets

# Set testing database before importing models
os.environ["DATABASE_URL"] = "sqlite:///./test_eventsphere.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models
from app.security import get_password_hash, create_access_token
from app.agents.message_bus import MessageBus, make_msg
from app.agents.venue_agent import VenueAgent
from app.agents.booking_agent import BookingAgent
from app.agents.ticket_agent import TicketAgent
from app.agents.waitlist_agent import WaitlistAgent
from app.agents.notification_agent import NotificationAgent

TEST_DB_URL = "sqlite:///./test_eventsphere.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_eventsphere.db"):
        try:
            os.remove("./test_eventsphere.db")
        except:
            pass

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

# -------------------------------------------------------------
# Test 1: User Registration & Hashed Password Verification (Part A.1)
# -------------------------------------------------------------
def test_user_registration_and_password_hashing(db_session):
    email = f"test_reg_{secrets.token_hex(4)}@test.com"
    plain_password = "SecurePassword123"
    
    user = models.User(
        name="Test Attendee",
        email=email,
        hashed_password=get_password_hash(plain_password),
        role=models.UserRole.attendee
    )
    db_session.add(user)
    db_session.commit()

    saved_user = db_session.query(models.User).filter(models.User.email == email).first()
    assert saved_user is not None
    assert saved_user.hashed_password != plain_password
    assert saved_user.hashed_password.startswith("$2b$") or saved_user.hashed_password.startswith("$2a$")
    assert saved_user.role == models.UserRole.attendee

# -------------------------------------------------------------
# Test 2: Role Access Enforcement (Part A.1.b)
# -------------------------------------------------------------
def test_role_access_enforcement(client, db_session):
    # Attendee user token trying to access admin dashboard
    token = create_access_token({"sub": "attendee_user@test.com"})
    client.cookies.set("access_token", token)
    
    # Try admin dashboard route
    res = client.get("/dashboard")
    # Redirects or returns 403 / redirect to login because not admin
    assert res.status_code in [302, 403, 401]

# -------------------------------------------------------------
# Test 3: VenueAgent - Turnaround Buffer & Clash Prevention (Part B: VenueAgent)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_venue_agent_turnaround_buffer_refusal(db_session):
    # Create test venue
    venue = models.Venue(
        name="Acoustic Hall",
        location="East Campus",
        capacity=200,
        hourly_hire_rate=80.0,
        is_hireable=True
    )
    db_session.add(venue)
    db_session.commit()

    # Create event from 14:00 to 16:00
    base_time = datetime.utcnow() + timedelta(days=20)
    event1 = models.Event(
        title="Jazz Session",
        category="Concert",
        venue_id=venue.id,
        start_time=base_time.replace(hour=14, minute=0, second=0),
        end_time=base_time.replace(hour=16, minute=0, second=0),
        status=models.EventStatus.published
    )
    db_session.add(event1)
    db_session.commit()

    # Attempt to request slot at 16:15 (within the 30-min turnaround buffer)
    clash_request = {
        "action": "check_slot",
        "venue_id": venue.id,
        "start_time": base_time.replace(hour=16, minute=15).isoformat(),
        "end_time": base_time.replace(hour=18, minute=0).isoformat()
    }
    
    result = await VenueAgent.check_slot(clash_request, "conv-turnaround-1", db_session)
    assert result["performative"] == "REFUSE"
    assert "turnaround buffer" in result["content"]["reason"].lower()

# -------------------------------------------------------------
# Test 4: VenueAgent - Weekend Peak Pricing & Automatic Confirmation (Part B & C)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_venue_agent_weekend_pricing_and_decision(db_session):
    venue = models.Venue(
        name="Garden Pavilion",
        location="North Lawn",
        capacity=100,
        hourly_hire_rate=100.0,
        is_hireable=True
    )
    user = models.User(
        name="Club President",
        email=f"club_{secrets.token_hex(4)}@test.com",
        hashed_password="hash",
        role=models.UserRole.attendee
    )
    db_session.add_all([venue, user])
    db_session.commit()

    # Next Saturday
    sat = datetime.utcnow() + timedelta(days=(5 - datetime.utcnow().weekday() + 7) % 7 + 1)
    hire_req = models.HireRequest(
        user_id=user.id,
        venue_id=venue.id,
        start_time=sat.replace(hour=10, minute=0),
        end_time=sat.replace(hour=12, minute=0), # 2 hours
        purpose="Society Brunch",
        guest_count=50 # 50% capacity <= 90% auto-confirm threshold
    )
    db_session.add(hire_req)
    db_session.commit()

    payload = {
        "action": "hire_request",
        "venue_id": venue.id,
        "start_time": hire_req.start_time.isoformat(),
        "end_time": hire_req.end_time.isoformat(),
        "guest_count": 50,
        "hire_request_id": hire_req.id
    }

    decision = await VenueAgent.handle_hire(payload, "conv-hire-weekend", db_session)
    assert decision["performative"] == "AGREE"
    assert decision["content"]["is_weekend"] is True
    # 2 hours * $100 * 1.5x weekend rate = $300.00
    assert decision["content"]["total_price"] == 300.0

# -------------------------------------------------------------
# Test 5: BookingAgent - Max Ticket Quantity Enforcement (Part B: BookingAgent)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_booking_agent_refuses_excessive_quantity(db_session):
    payload = {
        "action": "book_tickets",
        "user_id": 1,
        "ticket_category_id": 1,
        "quantity": 10 # Limit is 6
    }
    result = await BookingAgent.book_tickets(payload, "conv-book-max", db_session)
    assert result["performative"] == "REFUSE"
    assert "maximum 6 tickets" in result["content"]["reason"].lower()

# -------------------------------------------------------------
# Test 6: BookingAgent - Strict Anti-Overbooking Protection (Part A.4.c & Technical Concurrency)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_booking_agent_prevents_overselling(db_session):
    venue = models.Venue(name="Studio 4", location="Art Block", capacity=10, hourly_hire_rate=20.0)
    user = models.User(name="Buyer", email=f"buyer_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    db_session.add_all([venue, user])
    db_session.commit()

    event = models.Event(
        title="Micro Workshop",
        category="Workshop",
        venue_id=venue.id,
        start_time=datetime.utcnow() + timedelta(days=10),
        end_time=datetime.utcnow() + timedelta(days=10, hours=2),
        status=models.EventStatus.published
    )
    db_session.add(event)
    db_session.commit()

    # Category with only 2 seats remaining
    cat = models.TicketCategory(event_id=event.id, name="Limited Seats", price=50.0, quantity=2, sold=0)
    db_session.add(cat)
    db_session.commit()

    # First booking takes both seats
    res1 = await BookingAgent.book_tickets({
        "user_id": user.id, "ticket_category_id": cat.id, "quantity": 2
    }, "conv-overbook-1", db_session)
    assert res1["performative"] == "INFORM"
    assert res1["content"]["action"] == "booking_confirmed"

    # Second booking attempts to take 1 more seat (must be strictly refused)
    res2 = await BookingAgent.book_tickets({
        "user_id": user.id, "ticket_category_id": cat.id, "quantity": 1
    }, "conv-overbook-2", db_session)
    assert res2["performative"] == "REFUSE"
    assert "available" in res2["content"]["reason"].lower()

# -------------------------------------------------------------
# Test 7: TicketAgent - Admit Exactly Once & Double Check-In Rejection (Part A.5.c & Part B)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_ticket_agent_admits_once_and_rejects_double_scan(db_session):
    venue = models.Venue(name="Main Stage", location="Hall", capacity=50, hourly_hire_rate=50.0)
    user = models.User(name="Attendee X", email=f"user_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    db_session.add_all([venue, user])
    db_session.commit()

    # Event starts in 30 minutes (within active check-in window)
    event = models.Event(
        title="Live Keynote",
        category="Seminar",
        venue_id=venue.id,
        start_time=datetime.utcnow() + timedelta(minutes=30),
        end_time=datetime.utcnow() + timedelta(hours=2),
        status=models.EventStatus.published
    )
    db_session.add(event)
    db_session.commit()

    cat = models.TicketCategory(event_id=event.id, name="Standard", price=10.0, quantity=10, sold=1)
    db_session.add(cat)
    db_session.commit()

    booking = models.Booking(
        user_id=user.id, event_id=event.id, ticket_category_id=cat.id,
        quantity=1, total_amount=10.0, payment_reference="PAY-TEST-99"
    )
    db_session.add(booking)
    db_session.flush()

    ticket = models.Ticket(booking_id=booking.id, qr_code=secrets.token_urlsafe(32))
    db_session.add(ticket)
    db_session.commit()

    # First Scan: Admitted
    scan1 = await TicketAgent.scan_ticket({"qr_code": ticket.qr_code, "event_id": event.id}, "conv-scan-1", db_session)
    assert scan1["performative"] == "AGREE"
    assert scan1["content"]["result"] == "admitted"

    # Second Scan: Rejected with clear reason (Already Used)
    scan2 = await TicketAgent.scan_ticket({"qr_code": ticket.qr_code, "event_id": event.id}, "conv-scan-2", db_session)
    assert scan2["performative"] == "REFUSE"
    assert scan2["content"]["result"] == "already_used"
    assert "already checked in" in scan2["content"]["reason"].lower()

# -------------------------------------------------------------
# Test 8: TicketAgent - Reject Ticket for Wrong Event (Part A.5.c)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_ticket_agent_rejects_wrong_event(db_session):
    venue = models.Venue(name="Room 1", location="L1", capacity=30, hourly_hire_rate=10.0)
    user = models.User(name="User Y", email=f"user_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    db_session.add_all([venue, user])
    db_session.commit()

    event = models.Event(
        title="Event Alpha", category="Seminar", venue_id=venue.id,
        start_time=datetime.utcnow() + timedelta(minutes=15),
        end_time=datetime.utcnow() + timedelta(hours=1),
        status=models.EventStatus.published
    )
    db_session.add(event)
    db_session.commit()

    cat = models.TicketCategory(event_id=event.id, name="Pass", price=5.0, quantity=5, sold=1)
    db_session.add(cat)
    db_session.commit()

    booking = models.Booking(user_id=user.id, event_id=event.id, ticket_category_id=cat.id, quantity=1, total_amount=5.0, payment_reference="P1")
    db_session.add(booking)
    db_session.flush()

    ticket = models.Ticket(booking_id=booking.id, qr_code=secrets.token_urlsafe(32))
    db_session.add(ticket)
    db_session.commit()

    # Scan with different gate event ID (e.g. 9999)
    scan = await TicketAgent.scan_ticket({"qr_code": ticket.qr_code, "event_id": 9999}, "conv-wrong-ev", db_session)
    assert scan["performative"] == "REFUSE"
    assert scan["content"]["result"] == "wrong_event"

# -------------------------------------------------------------
# Test 9: WaitlistAgent - Proactive Expiry Sweep & FIFO Re-offer (Part B & Part C)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_waitlist_agent_proactive_sweep_and_reoffer(db_session):
    user1 = models.User(name="Wait User 1", email=f"w1_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    user2 = models.User(name="Wait User 2", email=f"w2_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    db_session.add_all([user1, user2])
    db_session.commit()

    # Create waitlist entry 1 with expired hold time in the past
    w1 = models.WaitlistEntry(
        user_id=user1.id,
        ticket_category_id=1,
        quantity=1,
        status=models.WaitlistStatus.offered,
        offer_expires_at=datetime.utcnow() - timedelta(minutes=5) # Expired
    )
    # Create waitlist entry 2 in waiting state
    w2 = models.WaitlistEntry(
        user_id=user2.id,
        ticket_category_id=1,
        quantity=1,
        status=models.WaitlistStatus.waiting
    )
    db_session.add_all([w1, w2])
    db_session.commit()

    # Trigger proactive timer sweep
    sweep_res = await WaitlistAgent.expire_sweep("conv-sweep-test", db_session)
    assert sweep_res["performative"] == "INFORM"
    assert sweep_res["content"]["expired"] >= 1

    db_session.refresh(w1)
    db_session.refresh(w2)

    # w1 transitioned to expired
    assert w1.status == models.WaitlistStatus.expired
    # w2 received the cascaded re-offer
    assert w2.status == models.WaitlistStatus.offered
    assert w2.offer_expires_at > datetime.utcnow()

# -------------------------------------------------------------
# Test 10: NotificationAgent - Reactive to Broadcast Events (Part B: NotificationAgent)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_notification_agent_reacts_and_creates_alert(db_session):
    user = models.User(name="Target User", email=f"target_{secrets.token_hex(4)}@test.com", hashed_password="h", role=models.UserRole.attendee)
    db_session.add(user)
    db_session.commit()

    broadcast_msg = {
        "sender": "BookingAgent",
        "receiver": "NotificationAgent",
        "performative": "INFORM",
        "content": {
            "action": "booking_confirmed",
            "user_id": user.id,
            "event_title": "Gala Dinner",
            "quantity": 2,
            "total": 60.0,
            "payment_ref": "PAY-GALA-101"
        },
        "conversation_id": "conv-notif-1"
    }

    res = await NotificationAgent.handle(broadcast_msg, db_session)
    assert res["performative"] == "INFORM"

    # Verify notification record was persisted in database
    notif = db_session.query(models.Notification).filter(models.Notification.user_id == user.id).first()
    assert notif is not None
    assert "PAY-GALA-101" in notif.message
    assert "Gala Dinner" in notif.message

# -------------------------------------------------------------
# Test 11: Multi-Agent Message Bus Audit Log Traceability (Part B.4.2.5)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_message_bus_logs_traceable_conversation_id(db_session):
    test_conv_id = f"trace-{secrets.token_hex(6)}"
    msg = make_msg("TestSender", "VenueAgent", "REQUEST", {"action": "check_slot", "venue_id": 9999, "start_time": datetime.utcnow().isoformat(), "end_time": (datetime.utcnow()+timedelta(hours=1)).isoformat()}, test_conv_id)
    
    await MessageBus.publish(msg, db_session)

    # Verify message was logged with conversation id
    audit = db_session.query(models.AgentMessage).filter(models.AgentMessage.conversation_id == test_conv_id).first()
    assert audit is not None
    assert audit.sender == "TestSender"
    assert audit.receiver == "VenueAgent"
    assert audit.performative == "REQUEST"
