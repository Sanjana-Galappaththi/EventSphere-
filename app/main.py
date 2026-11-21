import os
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.templates_config import templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal, get_db
from app import models
from app.security import get_current_user, get_password_hash
from app.agents.message_bus import MessageBus, make_msg
from app.agents.venue_agent import VenueAgent
from app.agents.booking_agent import BookingAgent
from app.agents.ticket_agent import TicketAgent
from app.agents.waitlist_agent import WaitlistAgent
from app.agents.notification_agent import NotificationAgent

from app.routers import auth, venues, events, bookings, hire, scanner, dashboard

# 1. Register Agents with MessageBus
VenueAgent.register()
BookingAgent.register()
TicketAgent.register()
WaitlistAgent.register()
NotificationAgent.register()

# 2. Autonomous Background Scheduler for Proactive Agent Behaviour
# (Learning outcome 3 & Requirement 4.2.4: WaitlistAgent expiry sweep on a timer)
scheduler = AsyncIOScheduler()

async def scheduled_waitlist_sweep():
    db = SessionLocal()
    try:
        conv_id = str(uuid.uuid4())
        await MessageBus.publish(make_msg(
            "Scheduler", "WaitlistAgent", "REQUEST",
            {"action": "expire_sweep"},
            conv_id
        ), db)
    except Exception as e:
        print(f"[Waitlist Sweep Error]: {e}")
    finally:
        db.close()

# 3. Seed Demo Data Function
def seed_initial_data(db: Session):
    # Check if admin already exists
    admin = db.query(models.User).filter(models.User.email == "admin@eventsphere.edu").first()
    if not admin:
        # Create Demo Accounts required by ICA specification:
        admin = models.User(
            name="Alice Admin",
            email="admin@eventsphere.edu",
            hashed_password=get_password_hash("password123"),
            role=models.UserRole.admin
        )
        staff = models.User(
            name="Sam Staff",
            email="staff@eventsphere.edu",
            hashed_password=get_password_hash("password123"),
            role=models.UserRole.staff
        )
        attendee = models.User(
            name="Charlie Attendee",
            email="attendee@eventsphere.edu",
            hashed_password=get_password_hash("password123"),
            role=models.UserRole.attendee
        )
        db.add_all([admin, staff, attendee])
        db.commit()

        # Seed Sample Campus Venues
        v1 = models.Venue(
            name="Great Hall Auditorium",
            location="Central Campus, Building 101",
            capacity=300,
            description="Flagship university auditorium equipped with concert-grade acoustics, stage lighting, and projection systems.",
            image_url="https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop",
            hourly_hire_rate=120.0,
            is_hireable=True
        )
        v2 = models.Venue(
            name="Science & Innovation Amphitheatre",
            location="West Campus, STEM Quad",
            capacity=150,
            description="Modern tiered lecture hall with dual presentation screens and interactive audience polling mics.",
            image_url="https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=800&auto=format&fit=crop",
            hourly_hire_rate=75.0,
            is_hireable=True
        )
        v3 = models.Venue(
            name="Student Guild Pavilion",
            location="East Gardens",
            capacity=80,
            description="Flexible open-plan space for receptions, club meetings, networking nights, and private banquets.",
            image_url="https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=800&auto=format&fit=crop",
            hourly_hire_rate=45.0,
            is_hireable=True
        )
        db.add_all([v1, v2, v3])
        db.commit()

        # Seed Sample Events
        now = datetime.utcnow()
        e1 = models.Event(
            title="Spring University Symphony Concert",
            category="Concert",
            venue_id=v1.id,
            start_time=now + timedelta(days=5, hours=18),
            end_time=now + timedelta(days=5, hours=21),
            description="An evening of classical and contemporary orchestral performances by the University Philharmonic.",
            status=models.EventStatus.published
        )
        e2 = models.Event(
            title="AI & Agent-Based Computing Symposium 2026",
            category="Conference",
            venue_id=v2.id,
            start_time=now + timedelta(days=12, hours=9),
            end_time=now + timedelta(days=12, hours=17),
            description="Leading researchers and industry engineers discuss multi-agent systems, autonomous negotiation, and LLMs.",
            status=models.EventStatus.published
        )
        db.add_all([e1, e2])
        db.commit()

        # Seed Ticket Categories for events
        tc1_std = models.TicketCategory(event_id=e1.id, name="General Admission", price=20.0, quantity=250, sold=0)
        tc1_vip = models.TicketCategory(event_id=e1.id, name="VIP Balcony", price=45.0, quantity=50, sold=0)
        tc2_std = models.TicketCategory(event_id=e2.id, name="Student Delegate", price=10.0, quantity=100, sold=0)
        tc2_pro = models.TicketCategory(event_id=e2.id, name="Full Access Pass", price=35.0, quantity=50, sold=0)
        db.add_all([tc1_std, tc1_vip, tc2_std, tc2_pro])
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    # Start proactive background timer (Waitlist sweep runs every 60 seconds)
    scheduler.add_job(scheduled_waitlist_sweep, 'interval', seconds=60, id='waitlist_sweep_job')
    scheduler.start()
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(
    title="EventSphere - Multi-Agent Ticketing & Venue Platform",
    description="IT4123 Agent Based Computing Practical (ICA 02)",
    version="1.0.0",
    lifespan=lifespan
)

# Static & Templates configuration
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(venues.router)
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(hire.router)
app.include_router(scanner.router)
app.include_router(dashboard.router)

# Home Route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user
    })

# Notifications View Route
@app.get("/notifications", response_class=HTMLResponse)
async def notifications_view(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": user
    })

# Part C Advanced Feature: Agents reachable over HTTP (documented JSON inbox endpoints)
@app.post("/api/agents/{agent_name}/inbox", tags=["agents"])
async def agent_http_inbox(agent_name: str, payload: dict, db: Session = Depends(get_db)):
    """
    Direct HTTP Inbox for Agents (Part C Advanced Feature).
    Accepts JSON messages with structured performatives: REQUEST, AGREE, REFUSE, PROPOSE, INFORM, FAILURE.
    """
    msg = {
        "sender": payload.get("sender", "HTTP_CLIENT"),
        "receiver": agent_name,
        "performative": payload.get("performative", "REQUEST"),
        "content": payload.get("content", {}),
        "conversation_id": payload.get("conversation_id", str(uuid.uuid4()))
    }
    result = await MessageBus.publish(msg, db)
    return result
