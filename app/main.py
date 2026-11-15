from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import auth, venues, events, bookings, tickets, hire, dashboard
from app.database import Base, engine
import app.models

# --- EXPLICITLY IMPORT AGENTS TO REGISTER THEM WITH THE MESSAGE BUS ---
from app.agents.venue_agent import venue_agent
from app.agents.booking_agent import booking_agent
from app.agents.ticket_agent import ticket_agent
from app.agents.waitlist_agent import waitlist_agent
from app.agents.notification_agent import notification_agent
# -----------------------------------------------------------------------

# FORCE CREATE TABLES ON STARTUP
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EventSphere API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(venues.router, prefix="/api/venues", tags=["Venues"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(hire.router, prefix="/api/hire", tags=["Hire"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/scanner", response_class=HTMLResponse)
def scanner_page(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")