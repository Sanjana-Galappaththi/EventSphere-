from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from app.security import require_admin, get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db),
                     user: models.User = Depends(require_admin)):
    events = db.query(models.Event).all()
    event_stats = []
    for event in events:
        total_sold = sum(tc.sold for tc in event.ticket_categories)
        total_capacity = sum(tc.quantity for tc in event.ticket_categories)
        revenue = sum(
            b.total_amount for b in event.bookings
            if b.status == models.BookingStatus.confirmed
        )
        checkins = db.query(models.Ticket).join(models.Booking).filter(
            models.Booking.event_id == event.id,
            models.Ticket.status == models.TicketStatus.used
        ).count()
        event_stats.append({
            "event": event, "sold": total_sold,
            "capacity": total_capacity, "revenue": revenue, "checkins": checkins
        })

    messages = db.query(models.AgentMessage).order_by(
        models.AgentMessage.created_at.desc()
    ).limit(50).all()

    hire_requests = db.query(models.HireRequest).filter(
        models.HireRequest.status == models.HireStatus.escalated
    ).all()

    total_revenue = sum(
        b.total_amount for b in db.query(models.Booking).filter(
            models.Booking.status == models.BookingStatus.confirmed
        ).all()
    )

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request, "user": user, "event_stats": event_stats,
        "messages": messages, "hire_requests": hire_requests,
        "total_revenue": total_revenue
    })
